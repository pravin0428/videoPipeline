"""
SentenceAnalyzer extracts linguistic features from a single narration sentence.
Uses keyword matching and pattern heuristics — no LLM dependency.
"""
import re
from ..models import SentenceFeatures


# ── Location / Geography ──────────────────────────────────────────
# Words that indicate geographic FRAMING (not just any geographic feature)
LOCATION_FRAME_WORDS = {
    "located", "situated", "lies", "stands", "nestled",
    "region", "province", "district", "state", "country",
    "territory", "kingdom", "empire", "capital",
    "border", "borders", "boundary", "geographical", "geographic",
    "latitude", "longitude", "hemisphere", "settlement",
    "coast", "coastal", "inland", "peninsula", "subcontinent",
}

# Specific place names we can detect
NAMED_PLACES = {
    "india", "china", "nepal", "bhutan", "myanmar", "bangladesh",
    "sri lanka", "pakistan", "afghanistan", "tibet", "himalaya",
    "himalayas", "gangetic", "deccan", "rajasthan", "mumbai",
    "delhi", "kolkata", "chennai", "varanasi", "khajuraho",
    "ajanta", "ellora", "taj mahal", "shani shingnapur",
    "maharashtra", "madhya pradesh", "uttar pradesh",
    "karnataka", "tamil nadu", "kerala", "gujarat", "punjab",
    "west bengal", "odisha", "assam", "bihar", "jharkhand",
    "haryana", "himachal", "uttarakhand", "goa",
    "arabian sea", "bay of bengal", "indian ocean",
    "hindu kush", "vindhya", "satpura", "western ghats",
    "eastern ghats", "gangetic plain", "thar desert",
    "sundarbans", "nilgiris", "kashi", "prayagraj",
    "ayodhya", "mathura", "dwarka", "ujjain", "nasik",
}

LOCATION_KEYWORDS = LOCATION_FRAME_WORDS | NAMED_PLACES | {
    "city", "town", "village", "island", "continent",
}

# Pure geographic features (scenic, not frame-setting)
GEOGRAPHIC_FEATURES = {
    "valley", "mountain", "river", "lake", "ocean", "sea",
    "desert", "forest", "jungle", "cape", "bay", "gulf",
    "plain", "plateau", "hill", "range", "waterfall",
    "cave", "canyon", "cliff", "peak", "summit", "glacier",
}

DIRECTION_KEYWORDS = {
    "north", "south", "east", "west", "northeast", "northwest",
    "southeast", "southwest", "northward", "southward", "eastward",
    "westward", "upstream", "downstream", "upriver", "downriver",
    "northern", "southern", "eastern", "western",
    "beyond", "toward", "towards", "northeastern", "northwestern",
    "southeastern", "southwestern",
}

BOUNDARY_KEYWORDS = {
    "borders", "boundary", "boundaries", "divides", "separates",
    "demarcates", "edge", "frontier", "perimeter",
    "bordering", "bounded", "between", "along", "across", "through",
}

# Known populated places / regions we can detect
KNOWN_PLACES = {
    "india", "china", "nepal", "bhutan", "myanmar", "bangladesh",
    "sri lanka", "pakistan", "afghanistan", "tibet", "himalaya",
    "himalayas", "gangetic", "deccan", "rajasthan", "mumbai",
    "delhi", "kolkata", "chennai", "varanasi", "khajuraho",
    "ajanta", "ellora", "taj mahal", "shani shingnapur",
    "maharashtra", "madhya pradesh", "uttar pradesh",
    "karnataka", "tamil nadu", "kerala", "gujarat", "punjab",
    "west bengal", "odisha", "assam", "bihar", "jharkhand",
    "haryana", "himachal", "uttarakhand", "goa",
}

# ── Statistics / Data ─────────────────────────────────────────────
STATS_PATTERNS = [
    re.compile(r"\d+[%‱]"),
    re.compile(r"\d+\s*percent"),
    re.compile(r"(over|more than|less than|approximately|about|nearly|roughly)\s+\d+"),
    re.compile(r"one in|two in|three in|\d+ out of"),
    re.compile(r"half|third|quarter|majority|minority|plurality"),
]

COMPARISON_KEYWORDS = {
    "than", "compared", "versus", "vs", "relative", "larger",
    "smaller", "greater", "lesser", "higher", "lower", "faster",
    "slower", "more", "less", "bigger", "smaller", "taller",
    "shorter", "wider", "narrower", "similar", "different",
    "contrast", "opposite", "whereas", "while", "although",
    "differ", "difference", "similarly", "likewise",
}

NUMBER_PATTERN = re.compile(r"\b\d[\d,]*\.?\d*\b")

# ── Process / Mechanism ───────────────────────────────────────────
PROCESS_KEYWORDS = {
    "process", "processes", "mechanism", "mechanisms",
    "procedure", "method", "technique",
    "forms", "formed", "forming",
    "creates", "created", "creating",
    "results", "resulted", "resulting",
    "produces", "produced", "producing",
    "generates", "generated", "generating",
    "transforms", "transformed", "transforming",
    "converts", "converted", "converting",
    "changes", "changed", "changing",
    "evolves", "evolved", "evolving",
    "develops", "developed", "developing",
    "grows", "grew", "growing",
    "becomes", "became", "becoming",
    "transitions", "transitioned", "transitioning",
    "converts", "converted", "converting",
    "how", "works", "function", "operation",
    "stage", "stages", "phase", "phases",
    "sequence", "cycle", "cycles", "loops",
    "reaction", "chemical", "physical", "biological",
    "photosynthesis", "evaporation", "condensation", "erosion",
    "deposition", "sedimentation", "metamorphosis",
    "evaporates", "condenses", "erodes",
    "collide", "collides", "collided", "colliding",
    "collision",
}

CAUSE_EFFECT_KEYWORDS = {
    "because", "therefore", "thus", "hence", "consequently",
    "as a result", "leads to", "leads", "results in",
    "causes", "caused", "causing", "cause",
    "triggered", "triggers", "triggering",
    "sparked", "sparks", "sparking",
    "prompted", "prompts", "prompting",
    "due to", "owing to", "thanks to",
    "on account of", "thereby",
}

STEPS_KEYWORDS = {
    "first", "second", "third", "then", "next", "after",
    "before", "during", "while", "simultaneously", "finally",
    "step", "stage", "phase", "sequence", "gradually",
    "over time", "eventually", "ultimately",
}

NATURAL_PHENOMENON_KEYWORDS = {
    "earthquake", "volcano", "eruption", "tsunami", "flood",
    "drought", "storm", "hurricane", "tornado", "cyclone",
    "monsoon", "rainfall", "sunrise", "sunset", "eclipse",
    "moon", "tide", "current", "wind", "weather", "climate",
    "season", "spring", "summer", "autumn", "winter",
    "rainbow", "aurora", "lightning", "thunder",
}

# ── Visual / Concrete ─────────────────────────────────────────────
CONCRETE_VISUAL_NOUNS = {
    "temple", "building", "house", "bridge", "road", "river",
    "mountain", "tree", "flower", "animal", "bird", "fish",
    "person", "people", "crowd", "market", "street", "city",
    "village", "field", "farm", "ocean", "beach", "sky",
    "cloud", "stone", "rock", "wall", "door", "window",
    "tower", "spire", "dome", "pillar", "statue", "carving",
    "sculpture", "painting", "fabric", "jewel", "crown",
    "sword", "shield", "armor",     "vehicle", "boat", "ship",
    "train", "airplane", "cart", "chariot",
}

# Merge geographic features into concrete visual nouns
CONCRETE_VISUAL_NOUNS |= GEOGRAPHIC_FEATURES

MOVEMENT_KEYWORDS = {
    "flow", "flows", "flowed", "flowing",
    "run", "runs", "ran", "running",
    "move", "moves", "moved", "moving",
    "travel", "travels", "travelled", "traveling",
    "walk", "walks", "walked", "walking",
    "fly", "flies", "flew", "flying",
    "swim", "swims", "swam", "swimming",
    "drift", "drifts", "drifted", "drifting",
    "float", "floats", "floated", "floating",
    "sail", "sails", "sailed", "sailing",
    "ride", "rides", "rode", "riding",
    "crawl", "crawls", "crawled", "crawling",
    "climb", "climbs", "climbed", "climbing",
    "descend", "descends", "descended", "descending",
    "ascend", "ascends", "ascended", "ascending",
    "rise", "rises", "rose", "rising",
    "fall", "falls", "fell", "falling",
    "roll", "rolls", "rolled", "rolling",
    "slide", "slides", "slid", "sliding",
    "glide", "glides", "glided", "gliding",
    "soar", "soars", "soared", "soaring",
    "sweep", "sweeps", "swept", "sweeping",
    "rush", "rushes", "rushed", "rushing",
    "stream", "streams", "streamed", "streaming",
    "pour", "pours", "poured", "pouring",
    "spread", "spreads", "spreading",
    "expand", "expands", "expanded", "expanding",
    "contract", "contracts", "contracted", "contracting",
    "rotate", "rotates", "rotated", "rotating",
    "spin", "spins", "spun", "spinning",
    "orbit", "orbits", "orbited", "orbiting",
    "circulate", "circulates", "circulated", "circulating",
    "migrate", "migrates", "migrated", "migrating",
    "scatter", "scatters", "scattered", "scattering",
    "gather", "gathers", "gathered", "gathering",
    "collide", "collides", "collided", "colliding",
    "fold", "folds", "folded", "folding",
    "erupt", "erupts", "erupted", "erupting",
}

SENSORY_DETAIL_KEYWORDS = {
    "golden", "silver", "bright", "dark", "shadow", "light",
    "warm", "cool", "cold", "hot", "glowing", "shimmering",
    "sparkling", "glimmering", "shining", "radiant", "vibrant",
    "colorful", "pale", "deep", "rich", "intricate", "detailed",
    "ornate", "decorated", "carved", "painted", "woven",
    "loud", "quiet", "silent", "peaceful", "tranquil",
    "chaotic", "bustling", "lively", "serene", "calm",
    "smell", "scent", "aroma", "fragrance", "sound",
    "echo", "roar", "whisper", "chant", "song", "music",
}

EMOTION_KEYWORDS = {
    "awe", "wonder", "amazement", "astonishment", "reverence",
    "fear", "terror", "dread", "anxiety", "hope", "faith",
    "devotion", "worship", "prayer", "meditation", "peace",
    "sorrow", "grief", "sadness", "joy", "celebration",
    "triumph", "victory", "defeat", "struggle", "perseverance",
    "love", "hate", "anger", "fury", "compassion", "mercy",
    "gratitude", "thankfulness", "humility", "pride",
    "inspiring", "moving", "touching", "powerful",
}

# ── Abstract concepts ─────────────────────────────────────────────
ABSTRACT_KEYWORDS = {
    "concept", "idea", "belief", "faith", "philosophy",
    "ideology", "doctrine", "theory", "principle", "notion",
    "thought", "mind", "soul", "spirit", "consciousness",
    "divine", "sacred", "holy", "transcendent", "eternal",
    "infinite", "ultimate", "truth", "wisdom", "knowledge",
    "power", "authority", "justice", "righteousness",
    "good", "evil", "sin", "virtue", "morality", "ethics",
    "destiny", "fate", "karma", "dharma", "moksha",
    "enlightenment", "liberation", "freedom", "equality",
}

# ── Historical ────────────────────────────────────────────────────
HISTORICAL_KEYWORDS = {
    "history", "historical", "ancient", "medieval", "classical",
    "century", "era", "age", "period", "dynasty", "empire",
    "kingdom", "reign", "rule", "civilization", "culture",
    "tradition", "heritage", "legacy", "origin", "founded",
    "established", "built", "constructed", "created",
    "discovered", "explored", "conquered", "invaded",
    "BC", "AD", "BCE", "CE", "thousand years",
    "millennia", "centuries", "decades",
}

TIME_PERIOD_KEYWORDS = {
    "today", "now", "currently", "present day", "modern",
    "contemporary", "recent", "yesterday", "past", "future",
    "prehistoric", "ancestral", "early", "later",
    "morning", "afternoon", "evening", "night", "dawn",
    "dusk", "midnight", "noon", "spring", "summer",
    "autumn", "winter", "monsoon", "dry season", "wet season",
}

# ── Biological / Geological ───────────────────────────────────────
BIOLOGICAL_KEYWORDS = {
    "species", "animal", "plant", "tree", "flower", "bird",
    "fish", "insect", "mammal", "reptile", "amphibian",
    "organism", "cell", "dna", "gene", "evolution",
    "habitat", "ecosystem", "biodiversity", "extinct",
    "endangered", "survive", "adapt", "evolve", "breed",
    "migrate", "hibernate", "pollinate", "grow",
    "photosynthesis", "respiration", "digestion",
}

GEOLOGICAL_KEYWORDS = {
    "rock", "mineral", "crystal", "gem", "stone", "fossil",
    "sediment", "layer", "strata", "plate", "tectonic",
    "fault", "fold", "mountain", "volcano", "erosion",
    "deposit", "formation", "geological", "geology",
    "earth", "crust", "mantle", "core", "magma", "lava",
}

# ── Architecture / Culture ────────────────────────────────────────
ARCHITECTURAL_KEYWORDS = {
    "architecture", "building", "temple", "palace", "fort",
    "fortress", "castle", "monument", "memorial", "shrine",
    "mosque", "church", "cathedral", "stupa", "pagoda",
    "pillar", "column", "arch", "dome", "spire", "tower",
    "facade", "courtyard", "hall", "chamber", "sanctum",
    "gate", "entrance", "corridor", "staircase",
    "carving", "sculpture", "frieze", "mural", "fresco",
    "mosiac", "ornament", "decoration", "design",
    "structural", "engineering", "constructed", "built",
}

CULTURAL_KEYWORDS = {
    "culture", "tradition", "custom", "ritual", "ceremony",
    "festival", "celebration", "worship", "prayer", "offering",
    "pilgrimage", "procession", "dance", "music", "song",
    "art", "craft", "weaving", "pottery", "painting",
    "literature", "poetry", "epic", "myth", "legend",
    "folklore", "story", "narration", "oral", "ancestral",
    "community", "tribe", "clan", "family", "society",
}

CONTRAST_KEYWORDS = {
    "but", "however", "yet", "although", "though",
    "nevertheless", "nonetheless", "on the other hand",
    "in contrast", "conversely", "instead", "rather",
    "while", "whereas", "unlike", "despite", "in spite of",
}

SCALE_KEYWORDS = {
    "vast", "enormous", "massive", "gigantic", "colossal",
    "huge", "immense", "tiny", "minuscule", "microscopic",
    "tallest", "largest", "biggest", "smallest", "oldest",
    "highest", "deepest", "longest", "widest", "greatest",
    "millions", "billions", "thousands", "countless",
}


class SentenceAnalyzer:
    """Extract linguistic features from a single narration sentence."""

    def analyze(self, sentence: str) -> SentenceFeatures:
        text = sentence.strip()
        lower = text.lower()
        words = set(lower.split())
        tokens = lower.split()

        features = SentenceFeatures(text=text)

        # Noun / Verb / Adj extraction via simple POS heuristics
        features.key_nouns = self._extract_nouns(tokens, lower)
        features.key_verbs = self._extract_verbs(tokens, lower)
        features.key_adjectives = self._extract_adjectives(tokens, lower)

        # Location
        features.has_location = bool(
            words & LOCATION_KEYWORDS
            or any(self._word_in(place, lower) for place in NAMED_PLACES)
        )
        features.has_named_place = any(
            self._word_in(place, lower) for place in NAMED_PLACES
        )
        features.location_terms = [
            w for w in features.key_nouns
            if w.lower() in LOCATION_KEYWORDS or w.lower() in NAMED_PLACES
        ]

        # Direction
        features.has_direction = bool(words & DIRECTION_KEYWORDS)

        # Boundaries
        features.has_boundaries = bool(words & BOUNDARY_KEYWORDS)

        # Statistics
        features.has_statistics = any(
            p.search(text) for p in STATS_PATTERNS
        )
        features.has_comparison = bool(words & COMPARISON_KEYWORDS)
        numbers = NUMBER_PATTERN.findall(text)
        features.has_numbers = len(numbers) > 0
        features.numbers_found = numbers

        # Process
        features.has_process = bool(words & PROCESS_KEYWORDS)
        features.has_cause_effect = bool(words & CAUSE_EFFECT_KEYWORDS)
        features.has_steps = bool(words & STEPS_KEYWORDS)
        features.has_natural_phenomenon = bool(
            words & NATURAL_PHENOMENON_KEYWORDS
        )

        # Visual
        features.has_concrete_visual = bool(words & CONCRETE_VISUAL_NOUNS)
        features.has_movement = bool(words & MOVEMENT_KEYWORDS)
        features.has_sensory_detail = bool(words & SENSORY_DETAIL_KEYWORDS)
        features.has_emotion = bool(words & EMOTION_KEYWORDS)

        # Abstract
        features.has_abstract_concept = bool(words & ABSTRACT_KEYWORDS)

        # Temporal
        features.has_historical_ref = bool(words & HISTORICAL_KEYWORDS)
        features.has_time_period = bool(words & TIME_PERIOD_KEYWORDS)

        # Science
        features.has_biological_ref = bool(words & BIOLOGICAL_KEYWORDS)
        features.has_geological_ref = bool(words & GEOLOGICAL_KEYWORDS)

        # Culture
        features.has_architectural_ref = bool(words & ARCHITECTURAL_KEYWORDS)
        features.has_cultural_ref = bool(words & CULTURAL_KEYWORDS)

        # Rhetorical
        features.has_contrast = bool(words & CONTRAST_KEYWORDS)
        features.has_scale = bool(words & SCALE_KEYWORDS)

        return features

    def _extract_nouns(self, tokens: list[str], lower: str) -> list[str]:
        """Simple noun extraction: capitalized words, known place names, concrete nouns."""
        nouns = set()
        for token in tokens:
            clean = token.strip(".,;:!?\"'()[]{}")
            if not clean:
                continue
            # Keep proper nouns (capitalized in original)
            if clean[0].isupper() and len(clean) > 1:
                nouns.add(clean)
            # Known concrete nouns
            if clean.lower() in CONCRETE_VISUAL_NOUNS:
                nouns.add(clean)
            # Geographic features
            if clean.lower() in GEOGRAPHIC_FEATURES:
                nouns.add(clean)
        return list(nouns)

    def _extract_verbs(self, tokens: list[str], lower: str) -> list[str]:
        verbs = set()
        for token in tokens:
            clean = token.strip(".,;:!?\"'()[]{}").lower()
            if clean in MOVEMENT_KEYWORDS or clean in PROCESS_KEYWORDS or clean in CAUSE_EFFECT_KEYWORDS:
                verbs.add(clean)
        return list(verbs)

    def _extract_adjectives(self, tokens: list[str], lower: str) -> list[str]:
        adjs = set()
        for token in tokens:
            clean = token.strip(".,;:!?\"'()[]{}").lower()
            if clean in SENSORY_DETAIL_KEYWORDS or clean in SCALE_KEYWORDS or clean in EMOTION_KEYWORDS:
                adjs.add(clean)
        return list(adjs)

    @staticmethod
    def _word_in(phrase: str, text: str) -> bool:
        """Check if a multi-word phrase appears as whole words in text."""
        return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
