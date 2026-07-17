import asyncio
import logging
import re

import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

logger = logging.getLogger("atlas.vision.clip")

CONCEPT_POOL = [
    "aerial view landscape", "mountain range panorama", "dense forest canopy",
    "desert sand dunes", "ocean waves coast", "river flowing water",
    "lake reflection water", "waterfall cascade", "jungle tropical vegetation",
    "temple ancient architecture", "monument stone structure", "fort fortress walls",
    "palace royal building", "cave rock formation", "ruins archaeological site",
    "museum building interior", "statue sculpture art", "pillars corridor architecture",
    "city skyline urban", "village rural houses", "market street bazaar",
    "bridge structure river", "dam water infrastructure", "road highway",
    "railway train tracks", "airport runway", "harbor port ships",
    "agriculture farm fields", "terrace farming hills", "vineyard grapes",
    "garden botanical park", "wildlife animal nature", "bird flying sky",
    "fish underwater ocean", "butterfly insect macro", "flower blossom garden",
    "tree trunk bark", "sunset sky clouds", "sunrise morning light",
    "night sky stars", "snow mountain peak", "glacier ice blue",
    "volcano mountain eruption", "island beach tropical", "coral reef underwater",
    "map geographic location", "flag national symbol", "coastline shore beach",
    "valley green grass", "plateau flat land", "hill rolling terrain",
    "canyon deep rock", "cliff steep edge", "meadow wildflowers",
    "lightning storm weather", "rain forest wet", "fog mist atmospheric",
    "rainbow sky colorful", "aurora borealis night", "space earth orbit",
    "drone aerial photography", "wide angle panoramic", "close up detail texture",
    "macro extreme detail", "cinematic dramatic lighting", "golden hour warm light",
    "underground cave interior", "underwater sea ocean", "top down overhead view",
    "historical painting artwork", "cultural festival celebration", "people crowd gathering",
    "traditional costume dress", "religious ceremony ritual", "sun rays through trees",
    "path trail walking", "stairs steps climbing", "door entrance gateway",
    "window architectural detail", "roof tile pattern", "wall stone texture",
    "dome ceiling architecture", "minaret tower spire", "courtyard open space",
    "fountain water feature", "garden flowers bloom", "park bench trees",
    "forest path sunlight", "river bank shoreline", "mountain lake reflection",
    "snow covered landscape", "autumn forest colorful", "spring blossom flowers",
    "desert sand dunes sunset", "tropical beach palm trees", "rice fields terrace",
    "tea garden plantation", "heritage site unesco", "ancient civilization remains",
    "rock cut architecture", "cave painting ancient", "manuscript old text",
    "observatory stars telescope", "science laboratory research", "industry factory plant",
    "solar panels energy", "wind turbines farm", "spacecraft rocket launch",
    "map location marker", "geographic terrain elevation", "satellite view earth",
    "district boundary map", "city plan urban layout", "travel destination landmark",
]

EMPTY_EMBEDDING = np.zeros(512, dtype=np.float32).tobytes()


def _lazy_load():
    if _lazy_load.model is None:
        try:
            _lazy_load.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _lazy_load.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            _lazy_load.device = "mps" if torch.backends.mps.is_available() else "cpu"
            _lazy_load.model = _lazy_load.model.to(_lazy_load.device)
            _lazy_load.model.eval()
            logger.info("clip_model_loaded", device=_lazy_load.device)
        except Exception as e:
            logger.warning("clip_model_failed", error=str(e)[:120])
            _lazy_load.model = None

    if _lazy_load.concepts is None and _lazy_load.model is not None:
        try:
            inputs = _lazy_load.processor(text=CONCEPT_POOL, return_tensors="pt", padding=True, truncation=True).to(_lazy_load.device)
            with torch.no_grad():
                out = _lazy_load.model.get_text_features(**inputs)
                if hasattr(out, 'pooler_output'):
                    features = out.pooler_output
                elif hasattr(out, 'text_embeds'):
                    features = out.text_embeds
                else:
                    features = out[0] if isinstance(out, (list, tuple)) else out
            features = features / features.norm(dim=-1, keepdim=True)
            _lazy_load.concepts = features.cpu().numpy()
            logger.info("clip_concepts_encoded", count=len(CONCEPT_POOL))
        except Exception:
            logger.warning("clip_concepts_encode_failed", exc_info=True)

    return _lazy_load.model, _lazy_load.processor, _lazy_load.device, _lazy_load.concepts


_lazy_load.model = None
_lazy_load.processor = None
_lazy_load.device = "cpu"
_lazy_load.concepts = None


def _encode_texts(texts: list[str]) -> np.ndarray | None:
    model, processor, device, _ = _lazy_load()
    if model is None:
        return None
    try:
        inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True).to(device)
        with torch.no_grad():
            out = model.get_text_features(**inputs)
            if hasattr(out, 'pooler_output'):
                features = out.pooler_output
            elif hasattr(out, 'text_embeds'):
                features = out.text_embeds
            else:
                features = out[0] if isinstance(out, (list, tuple)) else out
        features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy()
    except Exception:
        logger.warning("clip_encode_texts_failed", exc_info=True)
        return None


def _encode_image(image_path: str) -> np.ndarray | None:
    model, processor, device, _ = _lazy_load()
    if model is None:
        return None
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.get_image_features(**inputs)
            if hasattr(out, 'pooler_output'):
                features = out.pooler_output
            elif hasattr(out, 'image_embeds'):
                features = out.image_embeds
            else:
                features = out[0] if isinstance(out, (list, tuple)) else out
        features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten()
    except Exception:
        logger.debug("clip_encode_image_failed", path=image_path[-40:], exc_info=True)
        return None


def expand_keywords_multilingual(hindi_text: str, top_k: int = 8) -> list[str]:
    try:
        concepts_emb = _lazy_load.concepts
        if concepts_emb is None:
            return _fallback_keywords(hindi_text)

        model, processor, device, _ = _lazy_load()
        if model is None:
            return _fallback_keywords(hindi_text)

        inputs = processor(text=[hindi_text], return_tensors="pt", padding=True, truncation=True).to(device)
        with torch.no_grad():
            out = model.get_text_features(**inputs)
            if hasattr(out, 'pooler_output'):
                text_emb = out.pooler_output
            elif hasattr(out, 'text_embeds'):
                text_emb = out.text_embeds
            else:
                text_emb = out[0] if isinstance(out, (list, tuple)) else out
        text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)
        text_emb_np = text_emb.cpu().numpy()

        scores = concepts_emb @ text_emb_np.T
        top_indices = np.argsort(scores.flatten())[::-1][:top_k]
        seen = set()
        results = []
        for idx in top_indices:
            concept = CONCEPT_POOL[idx]
            words = concept.split()
            for w in words:
                w_clean = w.strip(",.")
                if w_clean not in seen:
                    seen.add(w_clean)
                    results.append(w_clean)
        return results[:top_k]
    except Exception as e:
        logger.debug("expand_keywords_failed", error=str(e)[:80])
        return _fallback_keywords(hindi_text)


def _fallback_keywords(text: str) -> list[str]:
    fallback_map = {
        "पेड़": "tree forest", "जंगल": "forest jungle", "पहाड़": "mountain hill",
        "नदी": "river stream", "समुद्र": "ocean sea", "झील": "lake water",
        "मंदिर": "temple architecture", "गुफा": "cave rock", "किला": "fort fortress",
        "महल": "palace royal", "शहर": "city urban", "गाँव": "village rural",
        "इतिहास": "history ancient", "संस्कृति": "culture tradition",
        "प्रकृति": "nature landscape", "पानी": "water river", "हवा": "wind air",
        "आसमान": "sky clouds", "सूरज": "sun sunrise", "चाँद": "moon night",
        "तारा": "star night", "बादल": "cloud sky", "बारिश": "rain weather",
        "बर्फ": "snow ice", "आग": "fire flame", "जमीन": "ground earth",
        "रास्ता": "path trail", "सड़क": "road street", "पुल": "bridge structure",
        "दीवार": "wall stone", "दरवाजा": "door entrance", "खिड़की": "window architecture",
        "सीढ़ी": "stairs steps", "बगीचा": "garden park", "खेत": "field farm",
        "पशु": "animal wildlife", "पक्षी": "bird wildlife", "मछली": "fish underwater",
        "फूल": "flower blossom", "पत्ता": "leaf plant", "फल": "fruit food",
    }
    found = set()
    for hindi_word, eng in fallback_map.items():
        if hindi_word in text:
            for kw in eng.split():
                found.add(kw)
    if not found:
        for word in re.findall(r"[\u0900-\u097F]{3,}", text):
            if word in fallback_map:
                for kw in fallback_map[word].split():
                    found.add(kw)
    if not found:
        found = {"landscape", "nature", "scenic", "travel", "photography"}
    return list(found)[:8]


async def score_assets_async(asset_paths: list[str], description: str) -> list[tuple[str, float]]:
    loop = asyncio.get_event_loop()
    desc_emb = await loop.run_in_executor(None, lambda: _encode_texts([description]))
    if desc_emb is None:
        return [(p, 50.0) for p in asset_paths]

    def _score_all():
        results = []
        for path in asset_paths:
            img_emb = _encode_image(path)
            if img_emb is None:
                results.append((path, 50.0))
            else:
                sim = float(desc_emb[0] @ img_emb)
                sim = max(0.0, min(100.0, (sim + 1) * 50))
                results.append((path, sim))
        return results

    return await loop.run_in_executor(None, _score_all)


async def compute_embedding_async(image_path: str) -> bytes | None:
    loop = asyncio.get_event_loop()
    emb = await loop.run_in_executor(None, lambda: _encode_image(image_path))
    if emb is None:
        return None
    return emb.astype(np.float32).tobytes()


async def compute_text_embedding_async(text: str) -> np.ndarray | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _encode_texts([text]))


def cosine_similarity(a: bytes, b: bytes) -> float:
    try:
        a_arr = np.frombuffer(a, dtype=np.float32)
        b_arr = np.frombuffer(b, dtype=np.float32)
        a_norm = a_arr / np.linalg.norm(a_arr)
        b_norm = b_arr / np.linalg.norm(b_arr)
        return float(a_norm @ b_norm)
    except Exception:
        return 0.0


def select_diverse(embeddings: list[bytes], scores: list[float], k: int = 5, lmbda: float = 0.6) -> list[int]:
    if not embeddings or len(embeddings) <= k:
        return list(range(len(embeddings)))

    n = len(embeddings)
    emb_list = []
    for e in embeddings:
        arr = np.frombuffer(e, dtype=np.float32)
        nrm = np.linalg.norm(arr)
        emb_list.append(arr / nrm if nrm > 0 else arr)
    emb_matrix = np.array(emb_list)
    sim_matrix = emb_matrix @ emb_matrix.T
    sim_matrix = np.clip((sim_matrix + 1) / 2, 0.0, 1.0)

    selected = [int(np.argmax(scores))]
    remaining = list(range(n))
    remaining.remove(selected[0])

    while len(selected) < k and remaining:
        best_mmr = -float("inf")
        best_idx = -1
        for i in remaining:
            relevance = scores[i] / 100.0
            max_sim = max(sim_matrix[i][s] for s in selected) if selected else 0.0
            mmr = lmbda * relevance - (1 - lmbda) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
        if best_idx >= 0:
            selected.append(best_idx)
            remaining.remove(best_idx)
        else:
            break

    for r in remaining:
        if len(selected) >= k:
            break
        selected.append(r)

    return selected
