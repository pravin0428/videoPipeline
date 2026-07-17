#!/usr/bin/env python3
"""
Pipeline: Generate a complete documentary video from a Hindi script.
Uses Media Intelligence Engine for visual planning,
Pexels for stock media, edge-tts for Hindi narration,
and FFmpeg for composition.

Usage:
  /path/to/atlas/venv/bin/python media_lab/make_documentary.py
"""
import sys, os, json, asyncio, subprocess, time, shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import requests
from collections import Counter
from media_intelligence.engine import MediaIntelligenceEngine
from media_intelligence.enhanced import (
    EnhancedPlanner, EnhancedShot, EnhancedScene, EnhancedPlan, SHOT_TYPES,
)

# ── Configuration ──
RESOLUTION = "1080x1920"
FPS = 30
TTS_VOICE = "hi-IN-SwaraNeural"
FONT_PATH = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"

# ── Scripts Library ──
SCRIPTS = {
    "velas": {
        "title": "velas",
        "output_dir": "velas",
        "filename": "velas_documentary.mp4",
        "scenes": [
            {"hi": "महाराष्ट्र का वह गांव जहाँ लोग कछुओं को बचाने के लिए पूरी दुनिया में मशहूर हैं",
             "en": "A village in Maharashtra is famous worldwide for people saving turtles"},
            {"hi": "क्या आप जानते हैं कि महाराष्ट्र में एक छोटा-सा गांव ऐसा भी है, जहाँ हर साल हजारों लोग किसी त्योहार के लिए नहीं, बल्कि छोटे-छोटे कछुओं को समुद्र तक पहुँचाने के लिए आते हैं?",
             "en": "Do you know that in Maharashtra there is a small village where thousands of people come every year not for a festival but to help tiny turtles reach the ocean"},
            {"hi": "इस गांव का नाम है वेलास।",
             "en": "The name of this village is Velas"},
            {"hi": "रत्नागिरी जिले में स्थित यह शांत समुद्री गांव ऑलिव रिडले समुद्री कछुओं के संरक्षण के लिए पूरी दुनिया में जाना जाता है।",
             "en": "Located in Ratnagiri district this peaceful coastal village is known worldwide for the conservation of Olive Ridley sea turtles"},
            {"hi": "जब छोटे कछुए अंडों से बाहर निकलते हैं, तो स्थानीय लोग और स्वयंसेवक उन्हें सुरक्षित तरीके से समुद्र तक पहुँचाते हैं।",
             "en": "When baby turtles hatch from their eggs local villagers and volunteers safely guide them to the sea"},
            {"hi": "आज यह गांव दिखाता है कि यदि पूरा समुदाय चाहे, तो विलुप्त होती प्रजातियों को भी बचाया जा सकता है।",
             "en": "Today this village shows that if the whole community comes together even endangered species can be saved"},
            {"hi": "क्या आप भी ऐसे गांव की यात्रा करना चाहेंगे जहाँ इंसान और प्रकृति साथ मिलकर भविष्य बचा रहे हैं?",
             "en": "Would you also like to visit a village where humans and nature together are saving the future"},
        ],
        "scene_queries": {
            0: ["village Maharashtra", "turtle conservation India", "village landscape India"],
            1: ["turtle ocean beach", "baby sea turtle", "ocean waves beach"],
            2: ["village Maharashtra coast", "coastal village India", "small village"],
            3: ["peaceful coastal village", "sea coast Maharashtra", "ocean sunset village"],
            4: ["baby turtle hatching", "turtle hatchling beach", "sea turtle ocean"],
            5: ["village community India", "people working together", "nature conservation volunteers"],
            6: ["nature sunset beach", "human nature coexistence", "beach ocean sunrise"],
        },
    },
    "tadoba": {
        "title": "tadoba",
        "output_dir": "tadoba",
        "filename": "tadoba_documentary.mp4",
        "scenes": [
            {"hi": "क्या आप जानते हैं कि महाराष्ट्र का एक जंगल दुनिया भर के वन्यजीव प्रेमियों के लिए किसी स्वर्ग से कम नहीं माना जाता?",
             "en": "Do you know that a forest in Maharashtra is considered no less than a paradise for wildlife lovers worldwide"},
            {"hi": "यह है ताडोबा-अंधारी टाइगर रिज़र्व।",
             "en": "This is Tadoba Andhari Tiger Reserve"},
            {"hi": "यह महाराष्ट्र का सबसे पुराना और सबसे प्रसिद्ध टाइगर रिज़र्व है।",
             "en": "This is Maharashtra oldest and most famous tiger reserve"},
            {"hi": "घने जंगल, शांत झीलें और सैकड़ों प्रजातियों के जीव यहाँ का संतुलित पारिस्थितिकी तंत्र बनाते हैं।",
             "en": "Dense forests quiet lakes and hundreds of species of animals create a balanced ecosystem here"},
            {"hi": "अगर किस्मत साथ दे, तो यहाँ खुले जंगल में बाघ को चलते हुए देखना भी संभव है।",
             "en": "If luck favors it is possible to see a tiger walking in the open forest here"},
            {"hi": "ताडोबा हमें याद दिलाता है कि जंगल सिर्फ जानवरों का घर नहीं, बल्कि पूरी पृथ्वी की साँस हैं।",
             "en": "Tadoba reminds us that forests are not just homes for animals but the breath of the entire Earth"},
        ],
        "scene_queries": {
            0: ["Tadoba tiger reserve", "jungle forest Maharashtra", "wildlife sanctuary India"],
            1: ["tiger reserve forest", "jungle entrance nature", "wildlife park India"],
            2: ["tiger reserve Maharashtra", "Tadoba forest", "Indian tiger sanctuary"],
            3: ["dense jungle forest", "lake forest ecosystem", "wildlife habitat India"],
            4: ["tiger walking in forest", "Bengal tiger wild", "big cat nature"],
            5: ["forest trees nature", "green forest landscape", "wilderness nature India"],
        },
    },
    "sky": {
        "title": "sky",
        "output_dir": "sky",
        "filename": "sky_documentary.mp4",
        "scenes": [
            {"hi": "क्या आपने कभी सोचा है कि आसमान नीला ही क्यों दिखाई देता है?",
             "en": "Have you ever wondered why the sky appears blue"},
            {"hi": "असल में सूरज की सफेद रोशनी कई रंगों से मिलकर बनी होती है।",
             "en": "Actually sunlight is made up of many colors combined together"},
            {"hi": "जब यह रोशनी पृथ्वी के वातावरण से गुजरती है, तो नीली रोशनी बाकी रंगों की तुलना में ज़्यादा बिखर जाती है।",
             "en": "When this light passes through Earth atmosphere blue light scatters more than other colors"},
            {"hi": "इसी प्रक्रिया को रेले स्कैटरिंग कहा जाता है।",
             "en": "This process is called Rayleigh scattering"},
            {"hi": "यही कारण है कि दिन में आसमान नीला दिखाई देता है, जबकि सूर्योदय और सूर्यास्त के समय लाल और नारंगी रंग ज़्यादा दिखाई देते हैं।",
             "en": "This is why the sky appears blue during the day while at sunrise and sunset red and orange colors are more visible"},
            {"hi": "यानी रंग बदलता आसमान हमें हर दिन विज्ञान का एक खूबसूरत प्रयोग दिखाता है।",
             "en": "Meaning the changing colors of the sky show us a beautiful science experiment every day"},
        ],
        "scene_queries": {
            0: ["blue sky nature", "sunlight atmosphere", "sky clouds blue"],
            1: ["sunlight prism rainbow", "light spectrum", "sun rays nature"],
            2: ["Earth atmosphere", "sky blue scattering", "sunlight particles atmosphere"],
            3: ["science experiment light", "physics demonstration", "scientific visualization"],
            4: ["sunrise sky red orange", "sunset horizon colors", "colorful sky sunrise"],
            5: ["beautiful colorful sky", "nature sky clouds", "dramatic sky colors"],
        },
    },
    "raigad": {
        "title": "raigad",
        "output_dir": "raigad",
        "filename": "raigad_documentary.mp4",
        "scenes": [
            {"hi": "क्या आप जानते हैं कि भारत के इतिहास का एक सबसे महत्वपूर्ण राज्याभिषेक महाराष्ट्र के इसी किले पर हुआ था?",
             "en": "Do you know that one of the most important coronations in Indian history took place at this fort in Maharashtra"},
            {"hi": "यह है रायगढ़ किला।",
             "en": "This is Raigad Fort"},
            {"hi": "समुद्र तल से लगभग 2700 फीट की ऊँचाई पर स्थित यह किला मराठा साम्राज्य की राजधानी था।",
             "en": "Located at an altitude of about 2700 feet above sea level this fort was the capital of the Maratha Empire"},
            {"hi": "1674 में यहीं पर छत्रपति शिवाजी महाराज का राज्याभिषेक हुआ और स्वराज्य का सपना एक वास्तविक साम्राज्य में बदल गया।",
             "en": "In 1674 the coronation of Chhatrapati Shivaji Maharaj took place here and the dream of Swarajya turned into a real empire"},
            {"hi": "आज भी यहाँ का सिंहासन, बाज़ार और महादरवाज़ा इतिहास की गवाही देते हैं।",
             "en": "Even today the throne market and great gate here bear witness to history"},
            {"hi": "रायगढ़ केवल एक किला नहीं, बल्कि भारत के आत्मसम्मान का प्रतीक है।",
             "en": "Raigad is not just a fort but a symbol of India self respect"},
        ],
        "scene_queries": {
            0: ["Raigad fort Maharashtra", "Shivaji Maharaj fort", "historical fort India"],
            1: ["Raigad fort aerial view", "hill fort Maharashtra", "mountain fort India"],
            2: ["Maratha empire fort", "ancient fort architecture", "hilltop fort India"],
            3: ["Shivaji Maharaj coronation", "Raigad fort history", "Chhatrapati Shivaji"],
            4: ["Raigad fort ruins", "historic fortress India", "ancient Indian architecture"],
            5: ["Raigad fort top view", "Indian flag fort", "fort symbol pride India"],
        },
    },
    "lonar": {
        "title": "lonar",
        "output_dir": "lonar",
        "filename": "lonar_documentary.mp4",
        "scenes": [
            {"hi": "क्या आप जानते हैं कि महाराष्ट्र में एक ऐसी झील है, जिसे किसी नदी ने नहीं, बल्कि अंतरिक्ष से आए एक विशाल उल्कापिंड ने बनाया था?",
             "en": "Do you know that in Maharashtra there is a lake that was formed not by a river but by a giant meteorite that came from space"},
            {"hi": "यह है लोनार झील।",
             "en": "This is Lonar Lake"},
            {"hi": "करीब 50 हजार साल पहले एक विशाल उल्का पृथ्वी से टकराई और इस विशाल गोलाकार झील का निर्माण हुआ।",
             "en": "About 50000 years ago a giant meteor struck the Earth and formed this huge circular lake"},
            {"hi": "दुनिया में बहुत कम ऐसी झीलें हैं जिनका पानी खारा भी है और क्षारीय भी।",
             "en": "There are very few lakes in the world whose water is both saline and alkaline"},
            {"hi": "यही कारण है कि दुनियाभर के वैज्ञानिक आज भी यहाँ शोध करने आते हैं।",
             "en": "This is why scientists from around the world still come here to research"},
            {"hi": "लोनार हमें याद दिलाती है कि कभी-कभी धरती के सबसे बड़े रहस्य आसमान से आते हैं।",
             "en": "Lonar reminds us that sometimes the Earth's greatest mysteries come from the sky"},
        ],
        "scene_queries": {
            0: ["meteor crater lake", "Lonar lake Maharashtra", "impact crater India"],
            1: ["Lonar lake aerial", "crater lake India", "circular lake nature"],
            2: ["meteor impact crater", "asteroid strike Earth", "space rock crater"],
            3: ["saline lake water", "alkaline lake", "lake water texture"],
            4: ["scientists researching lake", "scientists field work India", "laboratory research nature"],
            5: ["mystery sky space", "sunset crater lake", "aerial view crater lake"],
        },
    },
    "ants": {
        "title": "ants",
        "output_dir": "ants",
        "filename": "ants_documentary.mp4",
        "scenes": [
            {"hi": "क्या आप जानते हैं कि एक छोटी-सी चींटी अकेले लगभग कुछ भी नहीं कर सकती, लेकिन लाखों चींटियाँ मिलकर ऐसे काम कर देती हैं जो किसी बड़े जानवर के लिए भी मुश्किल हो?",
             "en": "Do you know that a single ant alone can do almost nothing, but millions of ants together can do things difficult even for large animals"},
            {"hi": "एक चींटी जब खाना ढूँढ़ लेती है, तो वह वापस जाते समय ज़मीन पर एक खास रासायनिक रास्ता छोड़ती है। दूसरी चींटियाँ उसी रास्ते का पीछा करती हैं और देखते ही देखते पूरी कॉलोनी खाने तक पहुँच जाती है।",
             "en": "When an ant finds food it leaves a chemical trail on the ground while returning. Other ants follow that trail and soon the entire colony reaches the food"},
            {"hi": "अगर रास्ते में कोई बाधा आ जाए, तो चींटियाँ नया रास्ता खोज लेती हैं और कुछ ही मिनटों में पूरी कॉलोनी अपनी दिशा बदल देती है।",
             "en": "If any obstacle comes in the way ants find a new path and within minutes the entire colony changes direction"},
            {"hi": "सबसे हैरानी की बात यह है कि उनकी रानी चींटी हर काम का आदेश नहीं देती। पूरी कॉलोनी छोटे-छोटे संकेतों के आधार पर खुद फैसले लेती है।",
             "en": "The most surprising thing is that the queen ant does not command every task. The entire colony makes its own decisions based on small signals"},
            {"hi": "यही वजह है कि वैज्ञानिक चींटियों के इस व्यवहार से प्रेरणा लेकर रोबोटिक्स, इंटरनेट नेटवर्क और आधुनिक ट्रैफिक सिस्टम तक डिज़ाइन कर रहे हैं।",
             "en": "This is why scientists are taking inspiration from ant behavior to design robotics internet networks and modern traffic systems"},
            {"hi": "सोचिए... अगर लाखों छोटी चींटियाँ बिना किसी नेता के इतना शानदार तालमेल बना सकती हैं, तो इंसान मिलकर क्या कुछ नहीं कर सकते?",
             "en": "Imagine if millions of tiny ants can create such amazing coordination without any leader what can humans not achieve together"},
        ],
        "scene_queries": {
            0: ["ant colony teamwork", "ants working together", "ant colony nature"],
            1: ["ant trail pheromone", "ants following trail", "ant food carrying"],
            2: ["ants obstacle path", "ants changing direction", "ants new path"],
            3: ["queen ant colony", "ant colony hierarchy", "ant colony inside"],
            4: ["ant robot technology", "robotics nature inspiration", "swarm robotics"],
            5: ["ant teamwork amazing", "nature cooperation", "ants collective intelligence"],
        },
    },
}

# ── Global config (set by main() based on CLI arg) ──
SCRIPT = []
OUTPUT_DIR = Path("/tmp")
SCENE_QUERIES = {}
SCRIPT_ID = ""


def log(msg: str):
    print(f"[Pipeline] {msg}")


def create_dir(path: str):
    os.makedirs(path, exist_ok=True)


def ffprobe_duration(filepath: str) -> float:
    """Get media duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath],
            capture_output=True, text=True, timeout=15
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except:
        return 0.0


# ── Phase 1: TTS Generation (async) ──

async def generate_tts(text: str, output_path: str) -> float:
    """Generate Hindi TTS audio file, return duration in seconds."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text, voice=TTS_VOICE, rate="+0%", pitch="+0Hz"
    )
    await communicate.save(output_path)
    dur = ffprobe_duration(output_path)
    log(f"  TTS generated: {os.path.basename(output_path)} ({dur:.1f}s)")
    return dur


async def generate_all_tts() -> list[float]:
    """Generate TTS for all sentences, return list of durations. Skips existing files."""
    log("Phase 1: Generating TTS audio for all sentences...")
    tts_dir = str(OUTPUT_DIR / "tts")
    create_dir(tts_dir)
    durations = []
    tasks = []
    indices = []
    for i, s in enumerate(SCRIPT):
        out_path = os.path.join(tts_dir, f"scene_{i+1:02d}.mp3")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            dur = ffprobe_duration(out_path)
            log(f"  TTS exists: scene_{i+1:02d}.mp3 ({dur:.1f}s)")
            durations.append((i, dur))
        else:
            tasks.append(generate_tts(s["hi"], out_path))
            indices.append(i)
    if tasks:
        new_durations = await asyncio.gather(*tasks)
        for idx, dur in zip(indices, new_durations):
            durations.append((idx, dur))
    durations.sort(key=lambda x: x[0])
    return [d for _, d in durations]


# ── Phase 2: Media Intelligence Planning ──

def run_enhanced_planner() -> EnhancedPlan:
    """Run enhanced planner: shot sequences, establishing, B-roll, rhythm."""
    log("Phase 2: Enhanced planning with shot sequences...")
    engine = MediaIntelligenceEngine()
    plans = [engine.plan(s["en"]) for s in SCRIPT]

    # Log basic plans
    for i, plan in enumerate(plans):
        log(f"  Scene {i+1}: {plan.media_type.label} ({plan.confidence:.0%}) — {plan.reasoning[:50]}...")

    # Enhance with shot sequences, establishing, B-roll, rhythm
    planner = EnhancedPlanner()
    enhanced = planner.enhance(plans, SCRIPT, SCRIPT_ID)

    # Log enhanced plan
    log(f"  Establishing shots: {len(enhanced.establishing_shots)}")
    total_primary = sum(len(s.primary_shots) for s in enhanced.scenes)
    total_broll = sum(len(s.b_roll_shots) for s in enhanced.scenes)
    log(f"  Primary shots: {total_primary} | B-roll shots: {total_broll}")
    log(f"  Rhythm positions: {[s.narrative_position for s in enhanced.scenes]}")
    log(f"  Diversity score: {enhanced.shot_diversity.get('diversity_score', 'N/A')}")

    return enhanced


# ── Phase 3: Media Download (Pexels) ──

PEXELS_API_KEY = ""
PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"


def download_pexels_video(query: str, output_path: str, target_duration: float) -> bool:
    """Search and download best matching stock video from Pexels. Returns success."""
    if not PEXELS_API_KEY:
        return False
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "per_page": 15,
            "orientation": "portrait",
            "size": "medium",
        }
        resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            log(f"    No Pexels video results for: {query}")
            return False

        best = None
        for v in videos:
            for vf in v.get("video_files", []):
                if vf.get("width") and vf.get("height"):
                    w, h = vf["width"], vf["height"]
                    dur = v.get("duration", 0)
                    if best is None or (dur >= target_duration * 0.8 and w * h > best["area"]):
                        best = {"file": vf, "area": w * h, "duration": dur}
        if best is None:
            return False

        # Download directly to output path first
        dl_resp = requests.get(best["file"]["link"], timeout=60)
        dl_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(dl_resp.content)

        # Trim and scale to target resolution
        target_w, target_h = [int(x) for x in RESOLUTION.split("x")]
        trim_duration = min(target_duration, best["duration"])
        trimmed_path = output_path.replace(".mp4", "_trimmed.mp4")
        scale_filter = (
            f"scale='max({target_w},iw*{target_h}/ih)':'max({target_h},ih*{target_w}/iw)',"
            f"crop={target_w}:{target_h}"
        )
        subprocess.run([
            "ffmpeg", "-y", "-i", output_path,
            "-t", str(trim_duration),
            "-vf", scale_filter,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "18",
            trimmed_path,
        ], capture_output=True, timeout=120)
        if os.path.exists(trimmed_path) and os.path.getsize(trimmed_path) > 1000:
            os.replace(trimmed_path, output_path)
        else:
            return False
        log(f"    Downloaded Pexels video (trimmed to {trim_duration:.1f}s)")
        return True
    except Exception as e:
        log(f"    Pexels video error: {e}")
        if "output_path" in locals() and os.path.exists(output_path):
            os.remove(output_path)
        return False


def download_pexels_photo(query: str, output_path: str) -> bool:
    """Search and download best matching stock photo from Pexels. Returns success."""
    if not PEXELS_API_KEY:
        return False
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": 5, "orientation": "portrait"}
        resp = requests.get(PEXELS_PHOTO_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            log(f"    No Pexels photo results for: {query}")
            return False
        # Pick highest resolution
        best = max(photos, key=lambda p: p.get("width", 0) * p.get("height", 0))
        photo_url = best["src"]["large"]
        dl_resp = requests.get(photo_url, timeout=60)
        dl_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(dl_resp.content)
        log(f"    Downloaded Pexels photo")
        return True
    except Exception as e:
        log(f"    Pexels photo error: {e}")
        return False


def ken_burns_effect(image_path: str, output_path: str, duration: float):
    """Apply Ken Burns pan effect to a still image."""
    target_w, target_h = [int(x) for x in RESOLUTION.split("x")]
    zoom_factor = 1.08
    src_w = int(target_w * zoom_factor)
    src_h = int(target_h * zoom_factor)

    base_dir = os.path.dirname(output_path)
    scaled_path = os.path.join(base_dir, "_scaled.png")

    # Pre-scale
    subprocess.run([
        "ffmpeg", "-y", "-i", image_path,
        "-vf", f"scale={src_w}:{src_h}:force_original_aspect_ratio=increase,crop={src_w}:{src_h}",
        "-frames:v", "1", scaled_path,
    ], capture_output=True, timeout=60)

    # Animated crop (pan left to right)
    pan_pixels = src_w - target_w
    x_expr = f"{pan_pixels}*t/{duration}"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", scaled_path,
        "-vf", f"crop={target_w}:{target_h}:{x_expr}:0,format=yuv420p",
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "23",
        output_path,
    ], capture_output=True, timeout=120)

    if os.path.exists(scaled_path):
        os.remove(scaled_path)
    log(f"    Ken Burns effect applied ({duration:.1f}s)")


def create_fallback_scene(output_path: str, duration: float, text_lines: list[str]):
    """Create a fallback scene using Pillow text image + Ken Burns."""
    from PIL import Image, ImageDraw, ImageFont
    target_w, target_h = [int(x) for x in RESOLUTION.split("x")]
    img = Image.new("RGB", (target_w, target_h), (26, 39, 68))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 48)
    except Exception:
        font = ImageFont.load_default()
    joined = "\n".join(text_lines)
    bbox = draw.multiline_textbbox((0, 0), joined, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (target_w - tw) // 2
    y = (target_h - th) // 2
    draw.multiline_text((x, y), joined, fill=(255, 255, 255), font=font, align="center")
    img_path = output_path.replace(".mp4", "_fb.jpg")
    img.save(img_path, "JPEG", quality=95)
    ken_burns_effect(img_path, output_path, duration)
    os.remove(img_path)
    log(f"    Created fallback scene from Pillow text ({duration:.1f}s)")


def create_subtitle_srt(script: list, tts_durations: list, output_path: str, start_offset: float = 0.0):
    """Create an SRT subtitle file from script text and TTS durations."""
    lines = []
    current_time = start_offset
    for i, (entry, dur) in enumerate(zip(script, tts_durations)):
        start = current_time
        end = current_time + dur
        text = entry["hi"]
        fmt = lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{t%60:06.3f}".replace(".", ",")
        lines.append(str(i + 1))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(text)
        lines.append("")
        current_time = end
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    log(f"  Created SRT with {len(script)} subtitle entries")


def download_shot(shot: EnhancedShot, output_path: str, target_duration: float) -> str:
    """Download media for a single shot. Returns path to video file."""
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        if abs(ffprobe_duration(output_path) - target_duration) < 1.0:
            return output_path

    # Try curated queries first, then fall back to shot search_prompt
    queries = [shot.search_prompt]

    # Add per-shot-type modifiers for better search results
    type_modifiers = {
        "aerial": ["aerial view", "drone shot", "from above"],
        "wide": ["wide angle", "panorama", "landscape"],
        "medium": ["medium shot", "eye level view"],
        "close_up": ["close up", "macro", "detail view"],
        "detail": ["texture", "pattern", "close up detail"],
        "macro": ["extreme close up", "macro detail"],
        "transition": ["time lapse", "transition scene"],
    }
    for mod in type_modifiers.get(shot.shot_type, []):
        if mod not in queries[0].lower():
            queries.append(f"{mod} {queries[0]}")

    success = False
    for q in queries:
        if download_pexels_video(q, output_path, target_duration):
            actual_dur = ffprobe_duration(output_path)
            if actual_dur >= target_duration * 0.7:
                if actual_dur < target_duration * 0.85:
                    padded_path = output_path.replace(".mp4", "_pad.mp4")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", output_path,
                        "-vf", f"tpad=stop_mode=clone:stop_duration={target_duration - actual_dur}",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-preset", "ultrafast", "-crf", "23",
                        padded_path,
                    ], capture_output=True, timeout=60)
                    shutil.move(padded_path, output_path)
                success = True
                break

    if not success:
        # Fallback: photo + Ken Burns
        for q in queries:
            photo_path = output_path.replace(".mp4", ".jpg")
            if download_pexels_photo(q, photo_path):
                ken_burns_effect(photo_path, output_path, target_duration)
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                success = True
                break

    if not success:
        create_fallback_scene(output_path, target_duration, ["..."])
        success = True

    return output_path


def render_shot_list(
    shots: list[EnhancedShot],
    scene_dir: str,
    prefix: str,
) -> list[str]:
    """Render a list of shots into video files. Returns list of file paths."""
    paths = []
    for i, shot in enumerate(shots):
        dur = shot.duration
        path = os.path.join(scene_dir, f"{prefix}_{i+1:02d}.mp4")
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            actual = ffprobe_duration(path)
            if abs(actual - dur) < 1.5:
                paths.append(path)
                continue

        # Track shot type for internal note
        log(f"    [{shot.shot_type:10s}][{shot.purpose:10s}] {shot.search_prompt[:40]:40s} {dur:.1f}s")
        download_shot(shot, path, dur)
        paths.append(path)

    return paths


# ── Phase 4: Composition ──

def create_srt(subtitle_entries: list[dict], output_path: str):
    """Create SRT subtitle file from timecoded entries."""
    lines = []
    for i, entry in enumerate(subtitle_entries, 1):
        start = entry["start"]
        end = entry["end"]
        text = entry["text"]
        fmt_time = lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{t%60:06.3f}".replace(".", ",")
        lines.append(str(i))
        lines.append(f"{fmt_time(start)} --> {fmt_time(end)}")
        lines.append(text)
        lines.append("")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def compose_enhanced_video(
    all_videos: list[str],
    all_shots: list[EnhancedShot],
    shot_durations: list[float],
    subtitle_labels: list[str],
    tts_files: list[str],
    tts_durations: list[float],
    enhanced: EnhancedPlan,
    output_path: str,
):
    """Concatenate shot videos, add TTS audio, soft subtitles."""
    log("  Composing enhanced video...")
    work_dir = os.path.dirname(output_path)
    create_dir(work_dir)

    # Normalize all shots to 30fps with silent audio
    log("  Normalizing shots to 30fps...")
    normalized = []
    for i, sv in enumerate(all_videos):
        norm_path = sv.replace(".mp4", "_n.mp4")
        if os.path.exists(norm_path) and os.path.getsize(norm_path) > 1000:
            normalized.append(norm_path)
            continue
        dur = shot_durations[i] if i < len(shot_durations) else 3.0
        cmd = [
            "ffmpeg", "-y", "-i", sv,
            "-f", "lavfi", "-t", str(max(dur, 1)), "-i", "anullsrc=r=48000:cl=mono",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "30",
            "-preset", "ultrafast", "-crf", "18",
            "-c:a", "aac", "-b:a", "32k",
            "-shortest",
            norm_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            normalized.append(norm_path)
        else:
            log(f"  Normalize failed for shot {i+1}, using original")
            normalized.append(sv)
    log(f"  Normalized {len(normalized)} shots")

    # Concat demuxer (fast: no re-encode, all shots are already normalized)
    concat_list = os.path.join(work_dir, "_concat_list.txt")
    with open(concat_list, "w") as f:
        for nv in normalized:
            f.write(f"file '{nv}'\n")

    concat_video = os.path.join(work_dir, "_concat_video.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_video,
    ], capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log(f"  Concat demuxer failed, retrying with filter_complex...")
        # Fallback: filter_complex concat
        filter_parts = []
        for i in range(len(normalized)):
            filter_parts.append(f"[{i}:v][{i}:a]")
        filter_str = "".join(filter_parts) + f"concat=n={len(normalized)}:v=1:a=1[outv][outa]"
        input_args = []
        for nv in normalized:
            input_args.extend(["-i", nv])
        result = subprocess.run(
            ["ffmpeg", "-y"] + input_args + [
                "-filter_complex", filter_str,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                concat_video,
            ], capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            log(f"  Concat failed: {result.stderr[-300:]}")
            return
    log(f"  Concatenated {len(normalized)} shots")

    # Concatenate TTS files
    tts_list = os.path.join(work_dir, "tts_list.txt")
    with open(tts_list, "w") as f:
        for tf in tts_files:
            f.write(f"file '{tf}'\n")
    concat_audio = os.path.join(work_dir, "_concat_audio.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", tts_list, "-c", "copy", concat_audio,
    ], capture_output=True, timeout=120)

    # Build enhanced SRT with establishing labels + scene subtitles
    # Timeline: shot_durations define video clip positions, 
    #           tts_durations define subtitle positions
    srt_path = os.path.join(work_dir, "_subtitles.srt")
    video_time = 0.0
    srt_lines = []
    entry_num = 1

    # First pass: establishing shots get label subtitles
    for i, (shot, dur, label) in enumerate(
        zip(all_shots, shot_durations, subtitle_labels)
    ):
        if label:
            start = video_time
            end = start + dur
            fmt = lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{t%60:06.3f}".replace(".", ",")
            srt_lines.append(str(entry_num))
            srt_lines.append(f"{fmt(start)} --> {fmt(end)}")
            srt_lines.append(f"📍 {label}")
            srt_lines.append("")
            entry_num += 1
        video_time += dur

    # Second pass: scene subtitles (Hindi narration text)
    current_time = 0.0
    for i, dur in enumerate(tts_durations):
        label = SCRIPT[i]["hi"]
        start = current_time
        end = current_time + dur
        fmt = lambda t: f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{t%60:06.3f}".replace(".", ",")
        srt_lines.append(str(entry_num))
        srt_lines.append(f"{fmt(start)} --> {fmt(end)}")
        srt_lines.append(label)
        srt_lines.append("")
        entry_num += 1
        current_time += dur

    with open(srt_path, "w") as f:
        f.write("\n".join(srt_lines))
    log(f"  SRT: {entry_num - 1} entries (labels + narration)")

    # Mux video + audio + subtitles
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_video, "-i", concat_audio, "-i", srt_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=hin",
        "-af", "volume=6.0",
        "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0",
        "-shortest",
        output_path,
    ], capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log(f"  Mux failed: {result.stderr[-300:]}")
        return

    # Clean normalized files
    for nv in normalized:
        if nv.endswith("_n.mp4") and os.path.exists(nv):
            os.remove(nv)

    # Report
    final_size = os.path.getsize(output_path) / 1e6
    final_dur = ffprobe_duration(output_path)
    log(f"  Final: {output_path}")
    log(f"  Size: {final_size:.1f} MB, Duration: {final_dur:.1f}s")

    # Quality report
    qr = enhanced.quality_report
    checks = qr.get("checks", {})
    log(f"\n{'='*55}")
    log(f"  AI DOCUMENTARY STUDIO — QUALITY REPORT")
    log(f"{'='*55}")
    log(f"  Overall Quality:     {qr.get('overall_quality_score', 'N/A')}/100")
    log(f"  Category:            {checks.get('category', 'N/A')}")
    log(f"  Emotion Arc:         {' → '.join(checks.get('emotion_arc', []))}")
    log(f"  Hero Moments:        {checks.get('hero_moments_detected', [])}")
    log(f"{'─'*55}")
    for name, score in qr.get("component_scores", []):
        bar = "█" * max(1, int(score / 5)) if score >= 30 else "░" * 3
        log(f"  {name:25s} {score:5.1f}/100  {bar}")
    log(f"{'─'*55}")
    log(f"  Shots: {enhanced.shot_diversity.get('total_shots', 0)}  |  "
         f"Types: {enhanced.shot_diversity.get('n_shot_types_used', 0)}/{len(SHOT_TYPES)}  |  "
         f"Diversity: {qr.get('visual_diversity_score', enhanced.shot_diversity.get('diversity_score', 'N/A'))}")
    log(f"  Subject Identity Avg: {checks.get('subject_identity_avg', 'N/A')}  |  "
         f"Above Threshold: {checks.get('identity_above_threshold', 'N/A')}%")
    weaknesses = checks.get("weaknesses", [])
    if weaknesses:
        log(f"{'─'*55}")
        for w in weaknesses:
            icon = "🔴" if w["severity"] == "critical" else "⚠️"
            log(f"  {icon} {w['dimension']}: {w['score']}/100 ({w['severity']})")
    log(f"{'='*55}")


# ── Main Pipeline ──

async def main():
    global SCRIPT, OUTPUT_DIR, SCENE_QUERIES, SCRIPT_ID, PEXELS_API_KEY

    script_name = sys.argv[1] if len(sys.argv) > 1 else "velas"
    if script_name not in SCRIPTS:
        print(f"Unknown script: {script_name}. Available: {list(SCRIPTS.keys())}")
        sys.exit(1)

    config = SCRIPTS[script_name]
    SCRIPT = config["scenes"]
    SCRIPT_ID = config["title"]
    SCENE_QUERIES = config["scene_queries"]
    OUTPUT_DIR = Path(__file__).parent / "output" / config["output_dir"]
    final_filename = config["filename"]

    log(f"Script: {script_name} ({len(SCRIPT)} scenes)")
    start_time = time.time()

    # Setup
    create_dir(str(OUTPUT_DIR))
    scenes_dir = str(OUTPUT_DIR / "scenes")
    create_dir(scenes_dir)

    # Load API key (try .env first, then environment)
    env_path = Path(__file__).parent.parent / "atlas" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
    if not PEXELS_API_KEY:
        log("WARNING: PEXELS_API_KEY not set! Will use fallback text scenes.")

    # Phase 1: TTS
    tts_durations = await generate_all_tts()
    tts_files = [str(OUTPUT_DIR / "tts" / f"scene_{i+1:02d}.mp3") for i in range(len(SCRIPT))]

    # Phase 2: Enhanced Planning
    enhanced = run_enhanced_planner()

    # Phase 3: Render all shots
    log("Phase 3: Rendering shot sequences...")

    # 3a: Establishing shots
    log("  Rendering establishing shots...")
    establishing_videos = []
    if enhanced.establishing_shots:
        est_dir = str(OUTPUT_DIR / "establishing")
        create_dir(est_dir)
        establishing_videos = render_shot_list(
            enhanced.establishing_shots, est_dir, "est"
        )
        log(f"  → {len(establishing_videos)} establishing shots")

    # 3b: Scene shots (primary + B-roll interleaved)
    log("  Rendering scene shots...")
    scene_video_groups = {}  # scene_idx → list of shot video paths
    for i, scene in enumerate(enhanced.scenes):
        scene_dir_i = str(OUTPUT_DIR / "scenes" / f"scene_{i+1:02d}")
        create_dir(scene_dir_i)

        # Interleave: Primary → B-roll → Primary (if B-roll exists)
        interleaved = []
        primary = scene.primary_shots
        broll = scene.b_roll_shots

        if broll:
            # Distribute B-roll between primary shots
            for j in range(len(primary)):
                interleaved.append(primary[j])
                if j < len(broll) and j < len(primary) - 1:
                    interleaved.append(broll[j])
        else:
            interleaved = primary

        paths = render_shot_list(interleaved, scene_dir_i, f"s{i+1:02d}")
        scene_video_groups[i] = paths
        log(f"  Scene {i+1}: {len(paths)} shots ({scene.narrative_position})")

    # Phase 4: Compose everything
    log("Phase 4: Composing final video...")

    # Build flat shot list for SRT timing
    # First: establishing shots (with subtitle labels)
    all_shots_for_srt = []
    all_shot_durations = []
    all_subtitle_labels = []

    for shot in enhanced.establishing_shots:
        all_shots_for_srt.append(shot)
        all_shot_durations.append(shot.duration)
        label = shot.subtitle_label or ""
        all_subtitle_labels.append(label)

    # Then: all scene shots
    for i, scene in enumerate(enhanced.scenes):
        interleaved = []
        primary = scene.primary_shots
        broll = scene.b_roll_shots
        if broll:
            for j in range(len(primary)):
                interleaved.append(primary[j])
                if j < len(broll) and j < len(primary) - 1:
                    interleaved.append(broll[j])
        else:
            interleaved = primary

        for shot in interleaved:
            all_shots_for_srt.append(shot)
            all_shot_durations.append(shot.duration)
            all_subtitle_labels.append("")

    # Build the flat video list
    all_videos = establishing_videos.copy()
    for i in range(len(enhanced.scenes)):
        all_videos.extend(scene_video_groups.get(i, []))

    # Generate SRT with establishing labels + scene subtitles
    compose_enhanced_video(
        all_videos, all_shots_for_srt, all_shot_durations,
        all_subtitle_labels, tts_files, tts_durations,
        enhanced, str(OUTPUT_DIR / final_filename),
    )

    elapsed = time.time() - start_time
    log(f"\n{'='*50}")
    log(f"Pipeline complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    log(f"Output: {os.path.join(OUTPUT_DIR, final_filename)}")
    log(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
