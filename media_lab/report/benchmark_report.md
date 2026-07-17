# Media Lab Benchmark Report

**Date:** 2026-07-02T00:00:54.735348
**Hardware:** Darwin arm64
**RAM:** 17.2 GB
**MPS Available:** True
**GPU Note:** Apple Silicon shared memory: 17.2 GB
**Python:** 3.12.13 (main, Mar  3 2026, 12:39:30) [Clang 21.0.0 (clang-2100.0.123.102)]
**PyTorch:** 2.12.1
**diffusers:** 0.38.0
**FFmpeg:** ffmpeg version 8.0.1 Copyright (c) 2000-2025 the FFmpeg developers

---

## Benchmark Scene

```
scene:
  id: "khajuraho_sunrise_01"
  title: "Khajuraho Temple at Sunrise"
  description: >
    A wide shot of the ancient Khajuraho temples at sunrise.
    Golden morning light illuminates the intricate sandstone carvings.
    Birds circle the tall spire against a warm orange-blue sky.
    Light mist hovers at the base of the temple.
    The camera slowly pans right, revealing the full temple facade.
  duration_seconds: 5
  resolution: "1080x1920"  # vertical for documentaries
  fps: 30
  cinematic_prompt: >
    Cinematic wide shot of ancient Khajuraho temple at sunrise,
    golden hour light on sandstone carvings, birds circling spire,
    warm orange and blue sky, light mist at base, slow pan right,
    National Geographic documentary quality, 4K, shallow depth of field
  stock_search_queries:
    pexels: "Khajuraho temple sunrise ancient architecture India"
    pixabay: "ancient temple sunrise India architecture"
  ai_image_prompt:
    positive: >
      Ancient Khajuraho temple at sunrise, golden light on intricate sandstone
      carvings, tall shikhara spire, orange and blue sky, birds circling,
      light mist, National Geographic photography, 4K, cinematic lighting,
      shallow depth of field, wide angle lens
    negative: >
      blurry, low quality, distorted, ugly, deformed, watermark, text,
      modern buildings, people, cars, electricity wires, oversaturated
  i2v_prompt: >
    Slow pan right across temple facade, golden sunlight flickers through
    clouds, birds soar in circle around spire, mist drifts slowly at base
  t2v_prompt: >
    Cinematic drone shot of ancient Khajuraho temples at sunrise, golden
    light on sandstone carvings, birds circling tall spire, mist at base,
    slow camera pan, warm colors, National Geographic documentary style

```

---

## Results Summary

| # | Technique | Status | Total Time (s) | Gen Time (s) | Peak VRAM (GB) | Peak RAM (GB) | Output (MB) | Resolution | Duration (s) |
|---|-----------|--------|---------------|-------------|---------------|--------------|------------|------------|-------------|
| 1 | AI Image (SD 1.5) + Ken Burns | ✅ completed | 81.0 | 74.8 | 4.27 | 0.00 | 1.5 | 1080x1920 | 5.0s |
| 2 | Hybrid: Pexels Video + AI Overlay | ✅ completed | 96.3 | 83.8 | 0.00 | 0.00 | 0.5 | 1080x1920 | 5.0s |
| 3 | Pexels Photo + Ken Burns | ✅ completed | 5.6 | 0.1 | 0.00 | 0.09 | 2.2 | 1080x1920 | 5.0s |
| 4 | Pexels Stock Video | ✅ completed | 20.0 | 1.6 | 0.00 | 0.04 | 6.1 | 1080x1920 | 5.0s |

---

## Quality Assessment

### Scoring Rubric (1-10)

| Criterion | Description |
|-----------|-------------|
| Realism | How realistic/natural the footage looks |
| Cinematic Quality | Lighting, composition, depth of field |
| Motion Quality | Smoothness and naturalness of movement |
| Prompt Adherence | How well it matches the scene description |
| Documentary Feel | Suitability for documentary context |
| Speed | Generation time penalty (10 = <5s, 0 = >300s) |
| Hardware Fit | Runs on M2 16GB? (10 = yes, 0 = no) |


### Quality Scores

| Technique | Realism | Cinematic Quality | Motion Quality | Prompt Adherence | Documentary Feel | Speed | Hardware Fit (M2) | Avg |
|---|---|---|---|---|---|---|---|---|
| ✅ AI Image (SD 1.5) + Ken Burns | 6 | 7 | 6 | 8 | 6 | 2 | 7 | 6.0 |
| ✅ Hybrid: Pexels Video + AI Overlay | 8 | 8 | 9 | 7 | 8 | 2 | 5 | 6.7 |
| ✅ Pexels Photo + Ken Burns | 9 | 8 | 6 | 7 | 7 | 8 | 10 | 7.9 |
| ✅ Pexels Stock Video | 8 | 7 | 9 | 6 | 9 | 6 | 10 | 7.9 |

---


---

## Skipped Experiments

- **AI Image + I2V (SVD)**: SVD model too large for M2 16GB; partially downloaded, requires ~6GB+ VRAM

---

## Detailed Experiment Logs

### Pexels Stock Video

- **Status:** completed
- **Total Time:** 20.0s
- **Generation Time:** 1.6s
- **Render Time:** 18.3s
- **Peak VRAM:** 0.00 GB
- **Peak RAM:** 0.04 GB
- **Output File:** /Users/pravinmohite/Desktop/youtubePipeline/media_lab/output/pexels_video/pexels_final.mp4
- **Output Size:** 6.1 MB
- **Resolution:** 1080x1920
- **Duration:** 5.0s

**Notes:**
  - query: Khajuraho temple sunrise ancient architecture India
  - pexels_video_id: 12284773
  - matched_duration: 5
  - source_url: https://videos.pexels.com/video-files/12284773/12284773-uhd_2160_3840_30fps.mp4

### Pexels Photo + Ken Burns

- **Status:** completed
- **Total Time:** 5.6s
- **Generation Time:** 0.1s
- **Render Time:** 5.6s
- **Peak VRAM:** 0.00 GB
- **Peak RAM:** 0.09 GB
- **Output File:** /Users/pravinmohite/Desktop/youtubePipeline/media_lab/output/pexels_photo_kb/photo_kb.mp4
- **Output Size:** 2.2 MB
- **Resolution:** 1080x1920
- **Duration:** 5.0s

**Notes:**
  - query: Khajuraho temple sunrise ancient architecture India
  - pexels_photo_id: 11397593
  - photographer: tanmoy das
  - source_url: https://images.pexels.com/photos/11397593/pexels-photo-11397593.png

### AI Image (SD 1.5) + Ken Burns

- **Status:** completed
- **Total Time:** 81.0s
- **Generation Time:** 74.8s
- **Render Time:** 6.1s
- **Peak VRAM:** 4.27 GB
- **Peak RAM:** 0.00 GB
- **Output File:** /Users/pravinmohite/Desktop/youtubePipeline/media_lab/output/ai_image_kb/ai_image_kb.mp4
- **Output Size:** 1.5 MB
- **Resolution:** 1080x1920
- **Duration:** 5.0s

**Notes:**
  - gen_time_s: 53.02

### Hybrid: Pexels Video + AI Overlay

- **Status:** completed
- **Total Time:** 96.3s
- **Generation Time:** 83.8s
- **Render Time:** 12.5s
- **Peak VRAM:** 0.00 GB
- **Peak RAM:** 0.00 GB
- **Output File:** /Users/pravinmohite/Desktop/youtubePipeline/media_lab/output/hybrid/hybrid.mp4
- **Output Size:** 0.5 MB
- **Resolution:** 1080x1920
- **Duration:** 5.0s

**Notes:**
  - overlay_generated: True


---

## Conclusions & Recommendations

*To be filled after reviewing all generated clips.*

### Ranking

Ranking by average quality score (from table above):

1. **Pexels Photo + Ken Burns** — Avg Score: 7.9
2. **Pexels Stock Video** — Avg Score: 7.9
3. **Hybrid: Pexels Video + AI Overlay** — Avg Score: 6.7
4. **AI Image (SD 1.5) + Ken Burns** — Avg Score: 6.0