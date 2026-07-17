from __future__ import annotations

from video_engine.models import Project, Scene, Shot
from video_engine.utils.logging import LOG

CAMERA_MOVEMENT_LABELS: dict[str, str] = {
    "static": "static shot",
    "pan_left": "panning left",
    "pan_right": "panning right",
    "tilt_up": "tilting up",
    "tilt_down": "tilting down",
    "dolly_in": "dolly zoom in",
    "dolly_out": "dolly zoom out",
    "truck_left": "tracking left",
    "truck_right": "tracking right",
    "crane_up": "crane rising",
    "crane_down": "crane descending",
    "handheld": "handheld camera",
    "steadicam": "smooth steadicam",
    "slow_pan": "slow panning",
    "push_in": "pushing in",
    "pull_out": "pulling out",
    "aerial": "aerial shot",
    "drone": "drone footage",
    "tracking": "tracking shot",
    "orbit": "orbiting around",
}

CAMERA_ANGLE_LABELS: dict[str, str] = {
    "eye_level": "eye level",
    "low_angle": "low angle",
    "high_angle": "high angle",
    "overhead": "overhead view",
    "worm_eye": "worm eye view",
    "shoulder": "over the shoulder",
    "profile": "profile view",
    "three_quarter": "three quarter view",
    "dutch": "dutch angle",
    "aerial_view": "aerial perspective",
    "first_person": "first person view",
    "macro": "macro close up",
    "extreme_closeup": "extreme close up",
    "wide": "wide shot",
    "ultra_wide": "ultra wide shot",
}

LENS_LABELS: dict[str, str] = {
    "standard": "standard lens",
    "wide_angle": "wide angle lens",
    "ultra_wide": "ultra wide lens",
    "telephoto": "telephoto lens",
    "macro": "macro lens",
    "fisheye": "fisheye lens",
    "anamorphic": "anamorphic lens",
    "long_lens": "long lens",
    "short_lens": "short lens",
    "zoom": "zoom lens",
    "prime": "prime lens",
    "tilt_shift": "tilt shift lens",
}

TIME_OF_DAY_LABELS: dict[str, str] = {
    "morning": "early morning light",
    "golden_hour": "golden hour",
    "midday": "midday sun",
    "afternoon": "afternoon light",
    "sunset": "sunset light",
    "twilight": "twilight",
    "night": "night time",
    "blue_hour": "blue hour",
    "dawn": "dawn light",
    "dusk": "dusk light",
    "overcast": "overcast light",
    "any": "",
}

WEATHER_LABELS: dict[str, str] = {
    "clear": "clear sky",
    "cloudy": "cloudy sky",
    "overcast": "overcast sky",
    "rain": "rainy",
    "storm": "stormy",
    "snow": "snowy",
    "fog": "foggy",
    "mist": "misty",
    "windy": "windy",
    "humid": "humid",
    "drought": "dry drought",
    "any": "",
}

MOOD_LABELS: dict[str, str] = {
    "serene": "serene atmosphere",
    "dramatic": "dramatic mood",
    "mysterious": "mysterious atmosphere",
    "epic": "epic cinematic",
    "intimate": "intimate close",
    "contemplative": "contemplative mood",
    "tense": "tense atmosphere",
    "peaceful": "peaceful scene",
    "awe": "awe inspiring",
    "somber": "somber mood",
    "joyful": "joyful scene",
    "neutral": "",
    "hopeful": "hopeful scene",
    "melancholic": "melancholic mood",
    "sacred": "sacred atmosphere",
    "urgent": "urgent action",
    "wonder": "sense of wonder",
}

STYLE_LABELS: dict[str, str] = {
    "naturalistic": "nature documentary style",
    "cinematic": "cinematic film style",
    "bbc_earth": "bbc earth documentary",
    "natgeo": "national geographic style",
    "planet_earth": "planet earth series style",
    "blue_planet": "blue planet ocean documentary",
    "attenborough": "david attenborough style",
    "wildlife": "wildlife documentary",
    "macro_wonder": "macro insect documentary",
    "aerial_serenity": "aerial landscape documentary",
    "scientific": "scientific educational style",
    "documentary_drama": "cinematic documentary drama",
    "timelapse_world": "time lapse photography",
    "cultural_portrait": "cultural documentary portrait",
}

COMPOSITION_LABELS: dict[str, str] = {
    "rule_of_thirds": "rule of thirds composition",
    "center": "centered composition",
    "leading_lines": "leading lines composition",
    "symmetry": "symmetrical composition",
    "diagonal": "diagonal composition",
    "framing": "framed composition",
    "golden_ratio": "golden ratio composition",
    "depth": "deep depth composition",
    "pattern": "pattern composition",
    "texture": "texture composition",
    "balance": "balanced composition",
    "dynamic": "dynamic composition",
    "minimalist": "minimalist composition",
    "abstract": "abstract composition",
}

DEPTH_OF_FIELD_LABELS: dict[str, str] = {
    "very_shallow": "very shallow depth of field bokeh",
    "shallow": "shallow depth of field",
    "medium": "medium depth of field",
    "deep": "deep focus everything sharp",
    "extremely_shallow": "extreme macro shallow depth of field",
}

COLOR_PALETTE_LABELS: dict[str, str] = {
    "natural": "natural colors",
    "warm": "warm golden tones",
    "cool_blue": "cool blue tones",
    "vibrant": "vibrant saturated colors",
    "rich_warm": "rich warm color grade",
    "desaturated": "desaturated muted colors",
    "neutral": "neutral color palette",
    "monochrome": "monochrome black and white",
    "pastel": "soft pastel colors",
    "dark": "dark moody colors",
    "earthy": "earthy tones",
}


def _label(d: dict[str, str], key: str | None) -> str:
    if not key:
        return ""
    return d.get(key, "")


def format_shot_prompt(shot: Shot, scene: Scene, project: Project) -> str:
    if shot.search_prompt.strip():
        return shot.search_prompt.strip()

    parts: list[str] = []

    if shot.subject:
        parts.append(shot.subject)
    if shot.action:
        parts.append(shot.action)
    if shot.environment:
        parts.append(shot.environment)

    cam_movement = _label(CAMERA_MOVEMENT_LABELS, shot.camera_movement.value if shot.camera_movement else None)
    if cam_movement:
        parts.append(cam_movement)
    cam_angle = _label(CAMERA_ANGLE_LABELS, shot.camera_angle.value if shot.camera_angle else None)
    if cam_angle and cam_angle not in parts:
        parts.append(cam_angle)
    lens = _label(LENS_LABELS, shot.lens.value if shot.lens else None)
    if lens and lens not in parts:
        parts.append(lens)

    tod = _label(TIME_OF_DAY_LABELS, shot.time_of_day.value if shot.time_of_day else None)
    if tod:
        parts.append(tod)
    weather = _label(WEATHER_LABELS, shot.weather.value if shot.weather else None)
    if weather:
        parts.append(weather)
    mood = _label(MOOD_LABELS, shot.mood.value if shot.mood else None)
    if mood:
        parts.append(mood)
    style_label = _label(STYLE_LABELS, shot.profile)
    if not style_label:
        style_label = _label(STYLE_LABELS, project.profile)
    if not style_label:
        style_label = "nature documentary style"
    if style_label and style_label not in parts:
        parts.append(style_label)

    dof = _label(DEPTH_OF_FIELD_LABELS, shot.depth_of_field)
    if dof:
        parts.append(dof)
    comp = _label(COMPOSITION_LABELS, shot.composition.value if shot.composition else None)
    if comp and comp not in parts:
        parts.append(comp)
    color = _label(COLOR_PALETTE_LABELS, shot.color_palette)
    if color and color not in parts:
        parts.append(color)

    if shot.focus_subject and shot.focus_subject not in parts:
        parts.append(f"focus on {shot.focus_subject}")

    if parts:
        return ", ".join(parts)

    words = scene.narration.split()[:8]
    stop_words = {"the", "a", "an", "in", "of", "to", "is", "and", "it",
                  "this", "that", "for", "with", "on", "at", "by", "from",
                  "का", "के", "की", "में", "से", "को", "एक", "है", "यह"}
    keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]
    return " ".join(keywords[:4]) if keywords else "nature documentary style"


def format_all_prompts(project: Project) -> Project:
    LOG.info("Formatting search prompts...")
    count = 0
    for scene in project.scenes:
        for shot in scene.shots:
            if not shot.search_prompt.strip():
                shot.search_prompt = format_shot_prompt(shot, scene, project)
                count += 1
    LOG.info(f"  Formatted {count} prompts")
    return project
