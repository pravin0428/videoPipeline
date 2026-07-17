import asyncio
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import numpy as np

from core.config import settings
from core.logging import get_logger
from services.vision.clip_scorer import (
    expand_keywords_multilingual,
    score_assets_async,
    compute_embedding_async,
    select_diverse,
)
from services.vision.asset_library import get_asset_library
from services.vision.map_provider import MapProvider
from services.quality.video_gate import VideoQualityGate

logger = get_logger()

WIDTH = 1080
HEIGHT = 1920
FPS = 24
RENDER_FPS = 24
PER_ASSET_MIN = 1.0
PER_ASSET_MAX = 3.0
MIN_SCENES = 6
MAX_SCENES = 14
TOTAL_TARGET_DURATION = 58.0
FONT = "DevanagariMT"

COMMONS_CATEGORIES = {"cave", "temple", "monument", "historical", "ancient", "artifact", "ruins", "archaeology", "statue", "sculpture", "museum", "fort", "palace", "heritage"}

PEXELS_API = "https://api.pexels.com/v1/search"
PEXELS_API_KEY = settings.pexels_api_key
PIXABAY_API = "https://pixabay.com/api/"
PIXABAY_API_KEY = settings.pixabay_api_key
UNSPLASH_API = "https://api.unsplash.com/search/photos"
UNSPLASH_API_KEY = settings.unsplash_api_key

SD_MODEL = "runwayml/stable-diffusion-v1-5"
SD_STEPS = 25

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"
V3_DIR = OUTPUT_ROOT / "v3"

SHOT_TYPES = ["drone", "wide", "close_up", "macro", "aerial", "underground", "cinematic", "wildlife", "overhead", "tracking"]
CAMERA_MOVEMENTS = ["pan_left", "pan_right", "tilt_up", "tilt_down", "push_in", "pull_out", "track_left", "track_right", "static"]
TRANSITION_TYPES = ["crossfade", "dissolve", "fade", "fadeblack", "slideleft", "slideright"]


@dataclass
class V3Scene:
    scene_number: int
    start_time: float
    duration: float
    narration: str
    purpose: str = ""
    emotion: str = ""
    visual_goal: str = ""
    camera_style: str = "cinematic"
    shot_type: str = "cinematic"
    camera_movement: str = "static"
    motion_intensity: str = "medium"
    transition: str = "crossfade"
    visual_queries: list[str] = field(default_factory=list)
    overlay_text: str = ""


@dataclass
class V3Asset:
    url: str
    local_path: str = ""
    width: int = 0
    height: int = 0
    quality_score: float = 50.0
    source: str = "unknown"
    mime: str = "image/jpeg"
    title: str = ""
    description: str = ""
    shot_type: str = "cinematic"
    motion_type: str = "ken_burns_in"


@dataclass
class V3SceneRender:
    video_path: str
    duration: float
    scene_number: int


class ScenePlannerV3:
    def __init__(self, ollama_url: str = settings.ollama_base_url, model: str = settings.ollama_model):
        self.ollama_url = ollama_url
        self.model = model

    async def plan(self, script: str) -> list[V3Scene]:
        scenes = await self._llm_plan(script)
        if scenes and len(scenes) >= 4:
            logger.info("scene_planner_llm", count=len(scenes))
            return scenes
        logger.info("scene_planner_deterministic", reason="llm_failed" if not scenes else "too_few")
        return self._deterministic_plan(script)

    async def _llm_plan(self, script: str) -> list[V3Scene]:
        prompt = f"""You are a documentary scene planner. Split this Hindi script into cinematic scenes.

Rules:
- Each scene = one complete thought (1 narrated sentence).
- 8-12 scenes for a 60-second script.
- Assign duration (4-10 seconds) proportional to importance.
- Assign a purpose: Hook, Context, Explanation, Revelation, Contrast, Example, Question, Conclusion
- Assign an emotion: Mystery, Wonder, Amazement, Curiosity, Reflection, Hope, Surprise, Calm
- Write visual_goal (15 words) describing what the viewer should SEE.
- Assign camera_style: Drone, Wide, Close-up, Macro, Aerial, Cinematic, Underground, Tracking
- List 5-8 English visual_queries for image search (photography terms like "forest drone aerial", "tree canopy sunlight").

Script: {script}

Return ONLY valid JSON array, no other text:
[
  {{
    "scene_number": 1,
    "duration": 6.5,
    "narration": "Hindi text for this scene",
    "purpose": "Hook",
    "emotion": "Mystery",
    "visual_goal": "Aerial drone shot of dense forest canopy with mist",
    "camera_style": "Drone",
    "visual_queries": ["forest drone aerial", "tree canopy mist", "aerial jungle view", "forest top down", "green canopy sunlight"]
  }}
]"""
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                    )
                    if resp.status_code != 200:
                        continue
                    raw_data = json.loads(resp.json().get("response", "[]"))
                    if isinstance(raw_data, dict):
                        raw_data = raw_data.get("scenes") or raw_data.get("response") or raw_data
                    if isinstance(raw_data, str):
                        raw_data = json.loads(raw_data)
                    if isinstance(raw_data, dict) and "scene_number" in raw_data:
                        raw_data = [raw_data]
                    if not isinstance(raw_data, list):
                        raw_data = []
                    scenes = []
                    for s in raw_data:
                        if not isinstance(s, dict):
                            continue
                        scenes.append(V3Scene(
                            scene_number=int(s.get("scene_number", len(scenes) + 1)),
                            start_time=0,
                            duration=max(3.0, min(12.0, float(s.get("duration", 5)))),
                            narration=s.get("narration", ""),
                            purpose=s.get("purpose", "Explanation"),
                            emotion=s.get("emotion", "Wonder"),
                            visual_goal=s.get("visual_goal", s.get("visual_description", "")),
                            camera_style=s.get("camera_style", "Cinematic"),
                            visual_queries=s.get("visual_queries", []),
                        ))
                    if scenes:
                        return self._normalize_timing(scenes)
            except Exception as e:
                logger.debug("llm_plan_failed", attempt=attempt, error=str(e)[:80])
                await asyncio.sleep(1.0)
        return []

    def _deterministic_plan(self, script: str) -> list[V3Scene]:
        sentences = self._split_sentences(script)
        n = min(max(len(sentences), MIN_SCENES), MAX_SCENES)
        grouped = self._group_sentences(sentences, n)
        scenes = []
        purposes = ["Hook", "Context", "Explanation", "Revelation", "Example", "Contrast", "Question", "Conclusion"]
        emotions = ["Mystery", "Wonder", "Amazement", "Curiosity", "Reflection", "Surprise", "Hope", "Calm"]
        cameras = ["Cinematic", "Wide", "Close-up", "Aerial", "Drone", "Macro", "Underground", "Tracking", "Wide", "Cinematic"]
        for i, (text, dur) in enumerate(grouped):
            kw = self._extract_keywords(text)
            queries = self._expand_queries(kw, cameras[i % len(cameras)])
            scenes.append(V3Scene(
                scene_number=i + 1,
                start_time=0,
                duration=dur,
                narration=text,
                purpose=purposes[i % len(purposes)],
                emotion=emotions[i % len(emotions)],
                visual_goal=" ".join(kw[:5]),
                camera_style=cameras[i % len(cameras)],
                visual_queries=queries,
                overlay_text=text,
            ))
        return self._normalize_timing(scenes)

    @staticmethod
    def _normalize_timing(scenes: list[V3Scene]) -> list[V3Scene]:
        total = sum(s.duration for s in scenes)
        if total == 0:
            return scenes
        scale = TOTAL_TARGET_DURATION / total
        start = 0.0
        for s in scenes:
            s.duration = max(3.0, min(12.0, s.duration * scale))
        total = sum(s.duration for s in scenes)
        scale = TOTAL_TARGET_DURATION / total
        for s in scenes:
            s.duration = max(3.0, min(12.0, s.duration * scale))
        for s in scenes:
            s.start_time = round(start, 1)
            start += s.duration
        return scenes

    @staticmethod
    def _split_sentences(script: str) -> list[str]:
        raw = re.split(r'(?<=[।?!\n])\s*', script)
        result = [s.strip() for s in raw if len(s.strip()) > 10]
        return result if result else [script]

    @staticmethod
    def _group_sentences(sentences: list[str], n: int) -> list[tuple[str, float]]:
        if len(sentences) <= n:
            dur = TOTAL_TARGET_DURATION / max(len(sentences), 1)
            return [(s, max(3.0, min(12.0, dur))) for s in sentences]
        groups = [[] for _ in range(n)]
        for i, s in enumerate(sentences):
            groups[i % n].append(s)
        total = TOTAL_TARGET_DURATION
        per_group = total / n
        result = []
        for g in groups:
            text = " ".join(g)
            result.append((text, max(3.0, min(12.0, per_group))))
        return result

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        return expand_keywords_multilingual(text, top_k=8)

    @staticmethod
    def _expand_queries(keywords: list[str], camera: str) -> list[str]:
        templates = {
            "Drone": ["{kw} drone aerial", "aerial view {kw}", "{kw} top down", "bird eye {kw}", "drone photography {kw}"],
            "Wide": ["{kw} wide landscape", "panoramic {kw}", "{kw} scenic view", "wide angle {kw}", "landscape {kw}"],
            "Close-up": ["{kw} macro closeup", "{kw} detail shot", "close up {kw}", "{kw} texture", "macro photography {kw}"],
            "Macro": ["{kw} macro", "extreme closeup {kw}", "{kw} detail macro", "macro nature {kw}", "{kw} close up"],
            "Aerial": ["aerial {kw}", "{kw} aerial photography", "from above {kw}", "birds eye {kw}", "sky view {kw}"],
            "Cinematic": ["cinematic {kw}", "{kw} landscape", "{kw} photography", "beautiful {kw}", "scenic {kw}"],
            "Underground": ["underground {kw}", "roots {kw}", "soil {kw}", "underground view {kw}", "cave {kw}"],
            "Tracking": ["{kw} path", "{kw} trail", "through {kw}", "{kw} journey", "moving through {kw}"],
        }
        t = templates.get(camera, templates["Cinematic"])
        queries = []
        for tmpl in t:
            for kw in keywords[:3]:
                q = tmpl.format(kw=kw)
                if len(q.split()) <= 5:
                    queries.append(q)
        queries = list(dict.fromkeys(queries))
        random.shuffle(queries)
        return queries[:8]


class VisualDirector:
    SHOT_MAP = {
        "drone": {"motion": "pan_left", "zoom": "zoom_in", "intensity": "medium"},
        "wide": {"motion": "pan_right", "zoom": "zoom_out", "intensity": "low"},
        "close_up": {"motion": "static", "zoom": "ken_burns_in", "intensity": "low"},
        "macro": {"motion": "static", "zoom": "ken_burns_in", "intensity": "low"},
        "aerial": {"motion": "pan_left", "zoom": "zoom_out", "intensity": "medium"},
        "cinematic": {"motion": "pan_right", "zoom": "ken_burns_in", "intensity": "medium"},
        "underground": {"motion": "static", "zoom": "zoom_in", "intensity": "low"},
        "wildlife": {"motion": "track_right", "zoom": "zoom_in", "intensity": "medium"},
        "overhead": {"motion": "pan_left", "zoom": "zoom_out", "intensity": "low"},
        "tracking": {"motion": "pan_right", "zoom": "ken_burns_in", "intensity": "high"},
    }

    @classmethod
    def direct(cls, scene: V3Scene) -> V3Scene:
        style = scene.camera_style.lower().replace(" ", "_")
        if style in cls.SHOT_MAP:
            config = cls.SHOT_MAP[style]
        else:
            config = random.choice(list(cls.SHOT_MAP.values()))
        scene.shot_type = style
        motions = [config["motion"], config["zoom"], random.choice(["pan_left", "pan_right", "ken_burns_in", "ken_burns_out"])]
        scene.camera_movement = random.choice(motions)
        scene.motion_intensity = config["intensity"]
        return scene


class AssetScorer:
    REJECT_PATTERNS = re.compile(
        r"(map\b|poster\b|logo\b|screenshot|diagram|chart\b|infographic|scanned|document|drawing|"
        r"icon\b|flag\b|svg\b|vector|illustration|clip art|blueprint|"
        r"watermark|text\b|signature|label\b|banner|advertisement|"
        r"album cover|book cover|cd cover|certificate|ticket|receipt|"
        r"invoice|passport|id card|identity|website|screenshot|mockup|"
        r"presentation|slide\b|menu\b|brochure|flyer|catalog|coupon)",
        re.IGNORECASE,
    )

    PREFER_PATTERNS = re.compile(
        r"(photograph|cinematic|landscape|aerial|drone|wildlife|scenic|"
        r"nature|outdoor|travel|panoramic|beauty|natural|"
        r"sunset|sunrise|golden hour|mountain|forest|ocean|river|lake|"
        r"tree\b|flower|plant|garden|park\b|field|meadow|valley|"
        r"professional|high quality|ultra hd|4k\b|hdr\b|"
        r"bokeh|depth of field|macro|close up|wide angle)",
        re.IGNORECASE,
    )

    MIN_WIDTH = 1080
    MIN_HEIGHT = 1080

    @classmethod
    def score(cls, width: int, height: int, title: str, description: str, mime: str) -> float:
        score = 50.0
        if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
            score -= 60.0
        if "svg" in mime.lower():
            score -= 80.0
        combined = f"{title} {description}"
        if cls.REJECT_PATTERNS.search(combined):
            score -= 60.0
        if cls.PREFER_PATTERNS.search(combined):
            score += 30.0
        if width >= 1920 or height >= 1080:
            score += 15.0
        if width >= 3840 or height >= 2160:
            score += 10.0
        if width > height:
            ratio = width / max(height, 1)
            if 1.2 <= ratio <= 2.5:
                score += 10.0
        score += random.uniform(-2, 2)
        return max(0.0, min(100.0, score))

    @classmethod
    def is_rejected(cls, width: int, height: int, title: str, description: str, mime: str) -> bool:
        if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
            return True
        if "svg" in mime.lower():
            return True
        combined = f"{title} {description}"
        if cls.REJECT_PATTERNS.search(combined):
            return True
        return False


class PexelsProvider:
    def __init__(self):
        self._session: httpx.AsyncClient | None = None

    async def search(self, query: str, per_page: int = 15) -> list[V3Asset]:
        if not PEXELS_API_KEY:
            return []
        try:
            if not self._session:
                self._session = httpx.AsyncClient(timeout=15.0)
            resp = await self._session.get(
                PEXELS_API,
                params={"query": query, "per_page": per_page},
                headers={"Authorization": PEXELS_API_KEY},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            assets = []
            for photo in data.get("photos", []):
                src = photo.get("src", {})
                url = src.get("original") or src.get("large") or ""
                if not url:
                    continue
                w, h = photo.get("width", 0), photo.get("height", 0)
                alt = photo.get("alt", "") or ""
                score = AssetScorer.score(w, h, alt, alt, "image/jpeg")
                if AssetScorer.is_rejected(w, h, alt, alt, "image/jpeg"):
                    continue
                assets.append(V3Asset(
                    url=url, width=w, height=h, quality_score=score,
                    source="pexels", mime="image/jpeg", title=alt, description=alt,
                ))
            assets.sort(key=lambda a: -a.quality_score)
            return assets
        except Exception as e:
            logger.debug("pexels_error", query=query, error=str(e)[:80])
            return []


class PixabayProvider:
    def __init__(self):
        self._session: httpx.AsyncClient | None = None

    async def search(self, query: str, per_page: int = 15) -> list[V3Asset]:
        if not PIXABAY_API_KEY:
            return []
        try:
            if not self._session:
                self._session = httpx.AsyncClient(timeout=15.0)
            resp = await self._session.get(PIXABAY_API, params={
                "key": PIXABAY_API_KEY, "q": query, "image_type": "photo",
                "orientation": "horizontal", "safesearch": "true", "per_page": per_page,
            })
            if resp.status_code != 200:
                return []
            data = resp.json()
            assets = []
            for hit in data.get("hits", []):
                url = hit.get("largeImageURL") or hit.get("webformatURL") or ""
                if not url:
                    continue
                w, h = hit.get("imageWidth", 0), hit.get("imageHeight", 0)
                tags = hit.get("tags", "") or ""
                score = AssetScorer.score(w, h, tags, tags, "image/jpeg")
                if AssetScorer.is_rejected(w, h, tags, tags, "image/jpeg"):
                    continue
                assets.append(V3Asset(
                    url=url, width=w, height=h, quality_score=score,
                    source="pixabay", mime="image/jpeg", title=tags, description=tags,
                ))
            assets.sort(key=lambda a: -a.quality_score)
            return assets
        except Exception as e:
            logger.debug("pixabay_error", query=query, error=str(e)[:80])
            return []


class UnsplashProvider:
    def __init__(self):
        self._session: httpx.AsyncClient | None = None

    async def search(self, query: str, per_page: int = 15) -> list[V3Asset]:
        if not UNSPLASH_API_KEY:
            return []
        try:
            if not self._session:
                self._session = httpx.AsyncClient(timeout=15.0)
            resp = await self._session.get(
                UNSPLASH_API,
                params={"query": query, "per_page": per_page},
                headers={"Authorization": f"Client-ID {UNSPLASH_API_KEY}"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            assets = []
            for result in data.get("results", []):
                urls = result.get("urls", {})
                url = urls.get("raw") or urls.get("full") or urls.get("regular") or ""
                if not url:
                    continue
                w, h = result.get("width", 0), result.get("height", 0)
                desc = result.get("description") or result.get("alt_description") or ""
                score = AssetScorer.score(w, h, desc, desc, "image/jpeg")
                if AssetScorer.is_rejected(w, h, desc, desc, "image/jpeg"):
                    continue
                assets.append(V3Asset(
                    url=url, width=w, height=h, quality_score=score,
                    source="unsplash", mime="image/jpeg", title=desc, description=desc,
                ))
            assets.sort(key=lambda a: -a.quality_score)
            return assets
        except Exception as e:
            logger.debug("unsplash_error", query=query, error=str(e)[:80])
            return []


class CommonsProvider:
    @staticmethod
    def is_applicable(keywords: list[str]) -> bool:
        kw_set = set(k.lower() for k in keywords)
        combined = " ".join(kw_set)
        for cat in COMMONS_CATEGORIES:
            if cat in combined or cat in kw_set:
                return True
        return False

    @staticmethod
    async def search(query: str) -> list[V3Asset]:
        try:
            async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                params = {"action": "query", "list": "search", "srsearch": query, "srnamespace": "6", "srlimit": "10", "format": "json", "srprop": "size"}
                sr = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
                if sr.status_code != 200:
                    return []
                titles = [r["title"] for r in sr.json().get("query", {}).get("search", []) if "File:" in r.get("title", "")]
                if not titles:
                    return []
                ip = {"action": "query", "titles": "|".join(titles[:6]), "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "format": "json"}
                ir = await client.get("https://commons.wikimedia.org/w/api.php", params=ip)
                if ir.status_code != 200:
                    return []
                assets = []
                for pid, page in ir.json().get("query", {}).get("pages", {}).items():
                    if pid == "-1":
                        continue
                    ii = page.get("imageinfo", [])
                    if not ii:
                        continue
                    info = ii[0]
                    em = info.get("extmetadata", {})
                    title = page.get("title", "").replace("File:", "", 1)
                    desc = em.get("ImageDescription", {}).get("value", "")
                    mime = info.get("mime", "")
                    w, h = info.get("width", 0), info.get("height", 0)
                    score = AssetScorer.score(w, h, title, desc, mime)
                    if AssetScorer.is_rejected(w, h, title, desc, mime):
                        continue
                    url = info.get("url", "") or info.get("thumburl", "")
                    if not url:
                        continue
                    assets.append(V3Asset(url=url, width=w, height=h, quality_score=score, source="commons", mime=mime or "image/jpeg", title=title, description=desc))
                assets.sort(key=lambda a: -a.quality_score)
                return assets
        except Exception as e:
            logger.debug("commons_error", query=query, error=str(e)[:80])
            return []


class AIImageGenerator:
    def __init__(self, model_id: str = SD_MODEL):
        self.model_id = model_id
        self._pipe = None
        self._available = False

    async def ensure_loaded(self):
        if self._pipe is not None:
            return
        try:
            import torch
            from diffusers import StableDiffusionPipeline
            loop = asyncio.get_event_loop()
            self._pipe = await loop.run_in_executor(
                None,
                lambda: StableDiffusionPipeline.from_pretrained(self.model_id, torch_dtype=torch.float32, safety_checker=None).to("mps" if torch.backends.mps.is_available() else "cpu"),
            )
            self._available = True
            logger.info("sd_loaded", model=self.model_id)
        except Exception as e:
            logger.warning("sd_load_failed", error=str(e)[:120])

    @property
    def available(self) -> bool:
        return self._available

    async def generate(self, prompt: str, output_path: str) -> str | None:
        if not self._available:
            await self.ensure_loaded()
        if not self._available:
            return None
        try:
            import torch
            loop = asyncio.get_event_loop()
            pil = await loop.run_in_executor(
                None,
                lambda: self._pipe(
                    prompt,
                    negative_prompt="blurry, low quality, text, watermark, logo, map, diagram, drawing, illustration, cartoon, painting",
                    num_inference_steps=SD_STEPS, height=512, width=512,
                    generator=torch.Generator(device="mps" if torch.backends.mps.is_available() else "cpu").manual_seed(random.randint(0, 2**32)),
                ).images[0],
            )
            pil.save(output_path)
            logger.info("sd_generated", prompt=prompt[:50])
            return output_path
        except Exception as e:
            logger.warning("sd_failed", error=str(e)[:120])
            return None


class MultiSourceProvider:
    def __init__(self, topic_research_data: dict | None = None):
        self.pexels = PexelsProvider()
        self.pixabay = PixabayProvider()
        self.unsplash = UnsplashProvider()
        self.commons = CommonsProvider()
        self.sd = AIImageGenerator()
        self.map_provider = MapProvider()
        self.asset_library = get_asset_library()
        self._downloaded: dict[str, str] = {}
        self._topic_research_data = topic_research_data
        self._last_selection: list[V3Asset] = []

    async def select_for_scene(self, scene: V3Scene, images_dir: Path) -> list[V3Asset]:
        all_assets: list[V3Asset] = []
        queries = scene.visual_queries[:8] if scene.visual_queries else [scene.visual_goal]

        use_commons = CommonsProvider.is_applicable(scene.visual_queries + [scene.visual_goal])
        logger.info("asset_search", scene=scene.scene_number, queries=len(queries), shot=scene.shot_type, commons=use_commons)

        search_per_page = 20
        for q in queries:
            results = await self.pexels.search(q, per_page=search_per_page)
            all_assets.extend(results)
            results = await self.pixabay.search(q, per_page=search_per_page)
            all_assets.extend(results)
            results = await self.unsplash.search(q, per_page=search_per_page)
            all_assets.extend(results)
            if use_commons:
                results = await CommonsProvider.search(q)
                all_assets.extend(results)
            await asyncio.sleep(0.15)

        seen: set[str] = set()
        deduped = []
        for a in all_assets:
            if a.url not in seen:
                seen.add(a.url)
                deduped.append(a)

        downloaded: list[V3Asset] = []
        for asset in deduped:
            local = await self._download(asset, images_dir)
            if local:
                downloaded.append(local)

        if not downloaded:
            logger.warning("asset_downloads_empty", scene=scene.scene_number)
            return []

        # CLIP re-ranking against scene visual goal
        desc = scene.visual_goal or " ".join(scene.visual_queries[:3])
        local_paths = [a.local_path for a in downloaded]
        scored = await score_assets_async(local_paths, desc)
        path_score_map = dict(scored)
        for a in downloaded:
            a.quality_score = path_score_map.get(a.local_path, a.quality_score)

        downloaded.sort(key=lambda a: -a.quality_score)

        # Compute embeddings for diversity selection
        emb_futures = [compute_embedding_async(a.local_path) for a in downloaded[:20]]
        embeddings = await asyncio.gather(*emb_futures)
        valid_indices = [i for i, e in enumerate(embeddings) if e is not None]
        valid_embeddings = [embeddings[i] for i in valid_indices]
        valid_scores = [downloaded[i].quality_score for i in valid_indices]

        if valid_embeddings and len(valid_embeddings) >= 3:
            diverse_indices = select_diverse(valid_embeddings, valid_scores, k=min(5, len(valid_embeddings)), lmbda=0.6)
            selected = [downloaded[valid_indices[i]] for i in diverse_indices]
        else:
            selected = downloaded[:min(5, len(downloaded))]

        # Store embeddings in asset library for future use
        for i, a in enumerate(downloaded[:20]):
            if i < len(embeddings) and embeddings[i] is not None:
                self.asset_library.add(a.url, a.local_path, a.source,
                                       a.width, a.height, a.mime, a.quality_score,
                                       embedding=embeddings[i])

        # SD fallback if still short
        if len(selected) < 3:
            needed = 3 - len(selected)
            logger.info("asset_sd_fallback", scene=scene.scene_number, needed=needed)
            for i in range(needed):
                prompt = desc + ", high quality photograph, cinematic lighting"
                fname = f"sd_{scene.scene_number:04d}_{i}.png"
                sd_path = str(images_dir / fname)
                result = await self.sd.generate(prompt, sd_path)
                if result:
                    selected.append(V3Asset(url="", local_path=sd_path, width=512, height=512, quality_score=70.0, source="sd", mime="image/png"))

        if len(selected) < 3:
            logger.warning("asset_insufficient", scene=scene.scene_number, count=len(selected))

        # Add map asset for scene 1 if coordinates available
        if scene.scene_number == 1:
            map_path = await self.map_provider.generate_map(
                topic_name="",
                research_data=self._topic_research_data,
            )
            if map_path:
                map_asset = V3Asset(
                    url="", local_path=map_path, width=1080, height=1920,
                    quality_score=85.0, source="map", mime="image/png",
                    title="", description="Location map",
                )
                selected.insert(0, map_asset)
                logger.info("map_asset_added", scene=scene.scene_number, path=map_path)

        for asset in selected:
            asset.shot_type = scene.shot_type
            asset.motion_type = self._pick_motion(scene)
            self.asset_library.record_use(asset.url)

        self.asset_library.flush()
        self._last_selection = selected
        return selected

    def _pick_motion(self, scene: V3Scene) -> str:
        intensity = scene.motion_intensity
        shot = scene.shot_type
        if intensity == "high":
            pool = ["push_in", "pull_out", "track_left", "track_right"]
        elif intensity == "low":
            pool = ["ken_burns_in", "ken_burns_out", "static"]
        else:
            pool = ["ken_burns_in", "ken_burns_out", "pan_left", "pan_right", "zoom_in", "zoom_out"]
        if shot in ("drone", "aerial"):
            pool = ["pan_left", "pan_right", "zoom_out"]
        elif shot in ("close_up", "macro"):
            pool = ["ken_burns_in", "static"]
        return random.choice(pool)

    async def _download(self, asset: V3Asset, images_dir: Path) -> V3Asset | None:
        if not asset.url:
            return asset if asset.local_path else None

        # Check asset library cache first
        cached = self.asset_library.get_cached_path(asset.url)
        if cached:
            asset.local_path = cached
            self._downloaded[asset.url] = cached
            return asset

        if asset.url in self._downloaded:
            asset.local_path = self._downloaded[asset.url]
            return asset
        ext = ".jpg"
        if ".png" in asset.url.lower():
            ext = ".png"
        elif ".webp" in asset.url.lower():
            ext = ".webp"
        fname = f"v3_{uuid.uuid4().hex[:8]}{ext}"
        dest = str(images_dir / fname)
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = await client.get(asset.url)
                if resp.status_code == 200 and len(resp.content) > 2048:
                    Path(dest).write_bytes(resp.content)
                    if await self._validate(dest):
                        asset.local_path = dest
                        self._downloaded[asset.url] = dest
                        return asset
        except Exception:
            pass
        return None

    @staticmethod
    async def _validate(path: str) -> bool:
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        proc = await asyncio.create_subprocess_exec(ffmpeg, "-v", "error", "-i", path, "-f", "null", "-", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, _ = await proc.communicate()
        return proc.returncode == 0


class CinematicRenderer:
    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self.enc = self._detect_encoder()

    @staticmethod
    def _detect_encoder() -> str:
        r = subprocess.run([shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg", "-encoders"], capture_output=True, text=True, timeout=10)
        if "h264_videotoolbox" in r.stdout:
            return "h264_videotoolbox"
        return "libx264"

    def _enc(self) -> list[str]:
        if self.enc == "h264_videotoolbox":
            return ["-c:v", "h264_videotoolbox", "-b:v", "6M"]
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]

    def render_clip(self, asset: V3Asset, output_path: str, duration: float) -> dict:
        motion = asset.motion_type
        img_w = min(asset.width or 1920, 5000)
        img_h = min(asset.height or 1080, 5000)
        aspect = img_w / max(img_h, 1)
        target = 1080 / 1920

        if motion == "ken_burns_in":
            sz, ez, dx, dy = 1.0, 1.08, 0, 0
        elif motion == "ken_burns_out":
            sz, ez, dx, dy = 1.08, 1.0, 0, 0
        elif motion == "pan_left":
            sz, ez, dx, dy = 1.12, 1.12, -0.08, 0
        elif motion == "pan_right":
            sz, ez, dx, dy = 1.12, 1.12, 0.08, 0
        elif motion == "tilt_up":
            sz, ez, dx, dy = 1.12, 1.12, 0, -0.08
        elif motion == "tilt_down":
            sz, ez, dx, dy = 1.12, 1.12, 0, 0.08
        elif motion == "push_in":
            sz, ez, dx, dy = 1.0, 1.15, 0, 0
        elif motion == "pull_out":
            sz, ez, dx, dy = 1.15, 1.0, 0, 0
        elif motion == "zoom_in":
            sz, ez, dx, dy = 1.0, 1.12, 0, 0
        elif motion == "zoom_out":
            sz, ez, dx, dy = 1.12, 1.0, 0, 0
        elif motion == "track_left":
            sz, ez, dx, dy = 1.08, 1.08, -0.12, 0
        elif motion == "track_right":
            sz, ez, dx, dy = 1.08, 1.08, 0.12, 0
        else:
            sz, ez, dx, dy = 1.0, 1.04, 0, 0

        base_w, base_h = int(img_w * 1.5), int(img_h * 1.5)
        sw, sh = base_w, base_h
        if aspect > target:
            sw = int(base_h * target)
        else:
            sh = int(base_w / target)
        sw, sh = max(sw, 1), max(sh, 1)

        n_frames = int(duration * RENDER_FPS)
        denom = max(n_frames - 1, 1)
        zoompan = (
            f"zoompan=z='{sz}+({ez}-{sz})*(on-1)/{denom}':"
            f"d={n_frames}:s=1080x1920:"
            f"x='iw/2-(iw/zoom/2)+{dx}*iw*(on-1)/{denom}':"
            f"y='ih/2-(ih/zoom/2)+{dy}*ih*(on-1)/{denom}'"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-i", asset.local_path,
            "-vf", f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p,{zoompan}",
            "-an", *self._enc(), "-pix_fmt", "yuv420p", "-r", str(RENDER_FPS), "-t", str(duration),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        return {"path": output_path, "duration": duration, "motion": motion}

    @staticmethod
    def concat_clips(clip_infos: list[dict], output_path: str) -> str:
        if not clip_infos:
            return ""
        if len(clip_infos) == 1:
            shutil.copy(clip_infos[0]["path"], output_path)
            return output_path
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        tmp = tempfile.mkdtemp()
        flist = os.path.join(tmp, "files.txt")
        Path(flist).write_text("\n".join(f"file '{ci['path']}'" for ci in clip_infos))
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", flist, "-c", "copy", output_path], capture_output=True, timeout=120)
        return output_path


class SceneAssembler:
    def __init__(self):
        self.renderer = CinematicRenderer()
        self.ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

    async def assemble(self, scene: V3Scene, assets: list[V3Asset], scenes_dir: Path) -> V3SceneRender:
        scene_dir = scenes_dir / f"scene_{scene.scene_number:04d}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        n = max(len(assets), 1)
        per_asset = scene.duration / n
        if per_asset < PER_ASSET_MIN:
            per_asset = PER_ASSET_MIN
        elif per_asset > PER_ASSET_MAX:
            per_asset = PER_ASSET_MAX
        n = max(int(scene.duration / per_asset), 1)
        per_asset = scene.duration / n

        used_assets = (assets * 3)[:n]

        loop = asyncio.get_event_loop()
        clip_infos = []
        for i, asset in enumerate(used_assets):
            clip_path = str(scene_dir / f"clip_{i:04d}.mp4")
            info = await loop.run_in_executor(None, self.renderer.render_clip, asset, clip_path, per_asset)
            clip_infos.append(info)

        concat_path = str(scene_dir / "concat.mp4")
        await loop.run_in_executor(None, CinematicRenderer.concat_clips, clip_infos, concat_path)

        # Single pass: color grading + cinematic FX (grain, vignette) + text overlay
        final_path = str(scene_dir / "final.mp4")
        self._render_with_all_fx(concat_path, final_path, scene.duration, scene.overlay_text)

        logger.info("scene_assembled", scene=scene.scene_number, clips=len(used_assets), per_asset=round(per_asset, 2))
        return V3SceneRender(video_path=final_path, duration=scene.duration, scene_number=scene.scene_number)

    def _render_with_all_fx(self, input_path: str, output_path: str, duration: float, overlay_text: str = "") -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        grain_path = str(tmp_dir / "grain.png")
        vignette_path = str(tmp_dir / "vignette.png")
        overlay_png = str(tmp_dir / "overlay.png")

        self._create_grain_texture(grain_path, duration)
        self._create_vignette(vignette_path)

        has_overlay = bool(overlay_text)
        if has_overlay:
            self._render_overlay_png(overlay_png, overlay_text)

        # Single filter_complex: grade → grain → vignette → overlay
        flt_parts = []
        flt_parts.append(f"[0:v]eq=contrast=1.05:brightness=0.02:saturation=1.08:gamma=0.98,format=yuva420p[graded]")
        flt_parts.append(f"[1:v]format=yuva420p,loop=loop=-1:size=1[grain]")
        flt_parts.append(f"[graded][grain]blend=all_mode=overlay:all_opacity=0.04[withgrain]")
        flt_parts.append(f"[2:v]format=yuva420p[vignette]")
        flt_parts.append(f"[withgrain][vignette]overlay=0:0[withvignette]")

        if has_overlay:
            flt_parts.append(f"[3:v]format=yuva420p[over]")
            flt_parts.append(f"[withvignette][over]overlay=x=(W-w)/2:y=H*0.08:enable='between(t,0,{duration})'[vout]")
            map_label = "[vout]"
        else:
            map_label = "[withvignette]"

        filter_graph = ";".join(flt_parts)

        inputs = ["-i", input_path, "-i", grain_path, "-i", vignette_path]
        if has_overlay:
            inputs += ["-i", overlay_png]

        cmd = [
            self.ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_graph,
            "-map", map_label,
            *self.renderer._enc(), "-pix_fmt", "yuv420p", "-t", str(duration),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=180)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if not os.path.isfile(output_path) or os.path.getsize(output_path) < 1024:
            shutil.copy(input_path, output_path)

    @staticmethod
    def _render_overlay_png(output_path: str, text: str) -> None:
        from PIL import Image, ImageDraw, ImageFont
        font_path = SceneAssembler._resolve_font()
        try:
            font = ImageFont.truetype(font_path, 38)
        except Exception:
            font = ImageFont.load_default()
        img = Image.new("RGBA", (1080, 160), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((540, 80), text, fill=(255, 255, 255, 240), font=font, anchor="mm")
        img.save(output_path)

    @staticmethod
    def _create_grain_texture(path: str, duration: float) -> None:
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            f"nullsrc=s=1080x1920:d={min(duration, 5)}:r=1,noise=alls=8:allf=t+u,format=yuva420p",
            path,
        ], capture_output=True, timeout=30)

    @staticmethod
    def _create_vignette(path: str) -> None:
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "gradients=s=1080x1920:c=black@0.0-black@0.6:rate=1:duration=1,format=yuva420p",
            "-frames:v", "1", path,
        ], capture_output=True, timeout=30)

    @staticmethod
    def _resolve_font() -> str:
        for c in [
            "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
            "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
            "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
            "/System/Library/Fonts/NotoNastaliq.ttc",
        ]:
            if os.path.isfile(c):
                return c
        return "/System/Library/Fonts/Supplemental/DevanagariMT.ttc"


class VideoCompositorV3:
    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

    def compose(self, scene_renders: list[V3SceneRender], audio_path: str | None, srt_path: str | None, output_path: str) -> str:
        concat_path = self._concat_scenes(scene_renders)
        return self._mux(concat_path, audio_path, srt_path, output_path)

    def _concat_scenes(self, renders: list[V3SceneRender]) -> str:
        if len(renders) == 1:
            return renders[0].video_path
        for r in renders:
            if not os.path.isfile(r.video_path):
                logger.error("concat_missing", scene=r.scene_number, path=r.video_path)
        tmp = Path(tempfile.mkdtemp())
        concat_path = str(tmp / "concat.mp4")
        flist = str(tmp / "files.txt")
        Path(flist).write_text("\n".join(f"file '{r.video_path}'" for r in renders))
        r = subprocess.run([self.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", flist, "-c", "copy", concat_path], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.error("concat_failed", stderr=r.stderr[-300:])
        return concat_path

    def _mux(self, video_path: str, audio_path: str | None, srt_path: str | None, output_path: str) -> str:
        has_srt = srt_path and os.path.isfile(srt_path)
        has_audio = audio_path and os.path.isfile(audio_path)
        cmd = [self.ffmpeg, "-y", "-i", video_path]
        if has_audio:
            cmd += ["-i", audio_path]
        if has_srt:
            cmd += ["-i", srt_path]
        if has_audio:
            cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "1"]
        else:
            cmd += ["-map", "0:v:0", "-c:a", "none"]
        cmd += ["-c:v", "copy"]
        if has_srt:
            cmd += ["-c:s", "mov_text", "-map", f"{'2:0' if has_audio else '1:0'}", "-metadata:s:s:0", "language=hin"]
        cmd += [output_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.error("mux_failed", stderr=r.stderr[-400:])
        if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
            logger.info("mux_ok", size=os.path.getsize(output_path))
        else:
            logger.error("mux_invalid", path=output_path)
        return output_path


class VideoShortGeneratorV3:
    def __init__(self, output_root: str | None = None, topic_research_data: dict | None = None):
        self.output_root = Path(output_root) if output_root else V3_DIR
        self.planner = ScenePlannerV3()
        self.provider = MultiSourceProvider(topic_research_data=topic_research_data)
        self.assembler = SceneAssembler()
        self.compositor = VideoCompositorV3()
        self.quality_gate = VideoQualityGate()
        self._topic_research_data = topic_research_data

    async def generate(self, title: str, script: str, output_filename: str = "final_v3.mp4") -> dict:
        uid = uuid.uuid4().hex[:12]
        logger.info("v3_start", title=title, uid=uid)

        dirs = self._setup_dirs(uid)

        audio_path = await self._generate_tts(script, dirs["audio"])
        audio_dur = self._get_audio_duration(audio_path) if audio_path else TOTAL_TARGET_DURATION
        logger.info("v3_audio_dur", duration=round(audio_dur, 1))

        scenes = await self.planner.plan(script)
        scenes = [VisualDirector.direct(s) for s in scenes]
        scenes = self._retime_scenes(scenes, audio_dur)
        logger.info("v3_scenes", count=len(scenes), total_dur=round(sum(s.duration for s in scenes), 1))

        scenes_with_assets = []
        for scene in scenes:
            assets = await self.provider.select_for_scene(scene, dirs["images"])
            scenes_with_assets.append((scene, assets))
            await asyncio.sleep(0.1)

        self._log_report(scenes_with_assets)

        scene_renders = []
        for scene, assets in scenes_with_assets:
            sr = await self.assembler.assemble(scene, assets, dirs["scenes"])
            scene_renders.append(sr)

        srt_path = await self._generate_subtitles(script, scene_renders)
        output_path = str(dirs["final"] / output_filename)

        if audio_path and os.path.isfile(audio_path):
            final = self.compositor.compose(scene_renders, audio_path, srt_path, output_path)
        else:
            concat_path = self.compositor._concat_scenes(scene_renders)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(concat_path, output_path)
            final = output_path

        self._write_report(uid, scenes, scenes_with_assets, scene_renders, final)

        # Video Quality Gate
        unique_asset_urls = set()
        for _, assets in scenes_with_assets:
            for a in assets:
                if a.url:
                    unique_asset_urls.add(a.url)

        quality_meta = {
            "scene_count": len(scene_renders),
            "unique_assets": len(unique_asset_urls),
            "srt_path": srt_path if os.path.isfile(srt_path) else None,
        }
        quality_result = await self.quality_gate.validate(final, quality_meta)
        if not quality_result["passed"]:
            logger.warning("v3_quality_gate_failed", summary=quality_result["summary"])

        logger.info("v3_complete", output=final, duration=round(sum(r.duration for r in scene_renders), 1),
                     quality_passed=quality_result["passed"])
        return {
            "video_path": final,
            "duration": round(sum(r.duration for r in scene_renders), 1),
            "quality": quality_result,
            "uid": uid,
        }

    @staticmethod
    def _get_audio_duration(audio_path: str | None) -> float:
        if not audio_path or not os.path.isfile(audio_path):
            return TOTAL_TARGET_DURATION
        try:
            import subprocess
            r = subprocess.run([
                shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe",
                "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1", audio_path,
            ], capture_output=True, text=True, timeout=15)
            return max(10.0, float(r.stdout.strip().split("=")[-1]))
        except Exception:
            return TOTAL_TARGET_DURATION

    @staticmethod
    def _retime_scenes(scenes: list[V3Scene], target_dur: float) -> list[V3Scene]:
        if not scenes:
            return scenes
        current = sum(s.duration for s in scenes)
        if current == 0:
            return scenes
        scale = target_dur / current
        start = 0.0
        for s in scenes:
            s.duration = max(PER_ASSET_MIN, min(12.0, s.duration * scale))
        total = sum(s.duration for s in scenes)
        scale = target_dur / total
        for s in scenes:
            s.duration = max(PER_ASSET_MIN, min(12.0, s.duration * scale))
        for s in scenes:
            s.start_time = round(start, 1)
            start += s.duration
        return scenes

    def _setup_dirs(self, uid: str) -> dict:
        d = {k: self.output_root / uid / k for k in ("images", "scenes", "audio", "final", "debug")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    async def _generate_tts(self, script: str, audio_dir: Path) -> str | None:
        try:
            import sys
            edge_tts = (shutil.which("edge-tts") or os.path.join(os.path.dirname(sys.executable), "edge-tts"))
            if not os.path.isfile(edge_tts):
                edge_tts = str(Path(sys.executable).parent / "edge-tts")
            out = str(audio_dir / "narration.mp3")
            voice = getattr(settings, "tts_default_voice", "hi-IN-SwaraNeural")
            proc = await asyncio.create_subprocess_exec(edge_tts, "--voice", voice, "--text", script, "--write-media", out, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await asyncio.wait_for(proc.wait(), timeout=120.0)
            if os.path.isfile(out) and os.path.getsize(out) > 1024:
                logger.info("v3_tts_done", path=out)
                return out
        except Exception as e:
            logger.warning("v3_tts_failed", error=str(e)[:80])
        return None

    async def _generate_subtitles(self, script: str, renders: list[V3SceneRender]) -> str:
        try:
            from services.subtitle.generator import SubtitleGenerator
            gen = SubtitleGenerator()
            total = sum(r.duration for r in renders)
            srt = gen.generate(script, total)
            if not srt:
                return ""
            srt_dir = Path(renders[0].video_path).parent.parent if renders else Path(tempfile.mkdtemp())
            srt_path = str(srt_dir / "subtitles.srt")
            Path(srt_path).write_text(srt, encoding="utf-8")
            return srt_path
        except Exception as e:
            logger.warning("v3_srt_failed", error=str(e)[:80])
            return ""

    def _log_report(self, scenes_with_assets: list[tuple[V3Scene, list[V3Asset]]]) -> None:
        for scene, assets in scenes_with_assets:
            logger.info("v3_scene_report",
                scene=scene.scene_number, purpose=scene.purpose, emotion=scene.emotion,
                shot=scene.shot_type, camera=scene.camera_movement, queries=len(scene.visual_queries),
                assets=len(assets,), sources=[a.source for a in assets],
                scores=[round(a.quality_score) for a in assets])

    def _write_report(self, uid: str, scenes: list[V3Scene], scenes_with_assets: list[tuple[V3Scene, list[V3Asset]]], renders: list[V3SceneRender], final_path: str) -> None:
        report = {"uid": uid, "version": "v3", "scenes": [], "quality": {}}
        total = 0.0
        for (s, assets), r in zip(scenes_with_assets, renders):
            scores = [a.quality_score for a in assets]
            avg = sum(scores) / max(len(scores), 1)
            total += avg
            report["scenes"].append({
                "scene": s.scene_number, "duration": round(s.duration, 1), "purpose": s.purpose,
                "emotion": s.emotion, "shot": s.shot_type, "camera": s.camera_movement,
                "queries": s.visual_queries[:3], "assets": len(assets),
                "scores": [round(sc) for sc in scores], "avg": round(avg),
                "sources": list(dict.fromkeys(a.source for a in assets)),
            })
        overall = (total / max(len(scenes), 1)) if scenes else 0
        total_assets = sum(len(a) for _, a in scenes_with_assets)
        report["quality"] = {
            "overall": round(overall, 1), "scenes": len(scenes),
            "total_assets": total_assets,
            "avg_per_scene": round(total_assets / max(len(scenes_with_assets), 1), 1),
            "duration": round(sum(r.duration for r in renders), 1),
        }
        debug_dir = self.output_root / uid / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        Path(str(debug_dir / "report.json")).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        logger.info("v3_report", path=str(debug_dir / "report.json"))
