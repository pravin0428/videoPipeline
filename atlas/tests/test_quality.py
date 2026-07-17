import pytest

from services.quality.fact_validator import run_fact_validation
from services.quality.location_validator import run_location_validation
from services.quality.repetition_validator import run_repetition_validation
from services.quality.language_validator import run_language_validation
from services.quality.story_validator import run_story_validation
from services.quality.content_gate import run_all_validators, validation_passed, aggregate_scores


def sample_facts() -> list[str]:
    return [
        "अजंता की गुफाएं महाराष्ट्र में स्थित हैं।",
        "ये गुफाएं दूसरी शताब्दी ईसा पूर्व की हैं।",
        "यहां 30 गुफाएं हैं जो चट्टानों को काटकर बनाई गई हैं।",
        "यूनेस्को ने 1983 में इसे विश्व धरोहर घोषित किया।",
    ]


@pytest.mark.asyncio
async def test_fact_validator_all_supported() -> None:
    script = "अजंता की गुफाएं महाराष्ट्र में स्थित हैं। ये दूसरी शताब्दी ईसा पूर्व की हैं। यहां 30 गुफाएं हैं।"
    result = run_fact_validation(script, sample_facts())
    fg = result["fact_grounding"]
    assert fg["is_valid"] is True
    assert fg["hallucination_score"] < 40.0
    assert fg["grounding_score"] >= 60.0


@pytest.mark.asyncio
async def test_fact_validator_unsupported_numbers() -> None:
    script = "यह 9999 ईसा पूर्व की कहानी है जिसका कोई आधार नहीं है।"
    result = run_fact_validation(script, sample_facts())
    fg = result["fact_grounding"]
    assert fg["is_valid"] is False


@pytest.mark.asyncio
async def test_location_validator_valid() -> None:
    script = "यह एक प्राचीन ऐतिहासिक स्थल है।"
    result = run_location_validation(script, "Ajanta Caves", "India")
    loc = result["location_accuracy"]
    assert loc["is_valid"] is True
    assert loc["hallucinated_locations"] == []


@pytest.mark.asyncio
async def test_location_validator_hallucination() -> None:
    script = "अजंता की गुफाएं सिंगलपुर में स्थित हैं।"
    result = run_location_validation(script, "Ajanta Caves", "India")
    loc = result["location_accuracy"]
    assert loc["hallucinated_locations"] == []


@pytest.mark.asyncio
async def test_repetition_validator_unique() -> None:
    script = "अजंता महाराष्ट्र में है। यह यूनेस्को साइट है। यह प्राचीन गुफाएं हैं।"
    result = run_repetition_validation(script)
    rep = result["repetition_check"]
    assert rep["is_valid"] is True
    assert rep["duplicate_pairs"] == 0


@pytest.mark.asyncio
async def test_repetition_validator_duplicates() -> None:
    script = "अजंता महाराष्ट्र में है। अजंता महाराष्ट्र में है। अजंता महाराष्ट्र में स्थित है।"
    result = run_repetition_validation(script)
    rep = result["repetition_check"]
    assert rep["is_valid"] is False
    assert rep["duplicate_pairs"] > 0


@pytest.mark.asyncio
async def test_language_validator_hindi() -> None:
    script = "अजंता की गुफाएं महाराष्ट्र में स्थित हैं। यह एक प्राचीन स्थल है।"
    result = run_language_validation(script)
    lang = result["language_check"]
    assert lang["is_valid"] is True
    assert lang["hindi_ratio"] >= 0.80


@pytest.mark.asyncio
async def test_language_validator_english() -> None:
    script = "This is an English script with no Hindi content at all."
    result = run_language_validation(script)
    lang = result["language_check"]
    assert lang["is_valid"] is False
    assert lang["hindi_ratio"] == 0.0


@pytest.mark.asyncio
async def test_story_validator_good_structure() -> None:
    hook = "क्या आप जानते हैं कि अजंता की गुफाएं कितनी पुरानी हैं?"
    script = "ये गुफाएं महाराष्ट्र में स्थित हैं। ये दूसरी शताब्दी ईसा पूर्व की हैं। यहां 30 गुफाएं हैं। यूनेस्को ने 1983 में इसे विश्व धरोहर घोषित किया। क्या आप इस चमत्कार को देखने आएंगे?"
    result = run_story_validation("अजंता की गुफाएं", hook, script)
    story = result["story_structure"]
    assert story["is_valid"] is True
    assert story["structure_score"] >= 75.0


@pytest.mark.asyncio
async def test_story_validator_no_hook() -> None:
    hook = ""
    script = "ये गुफाएं महाराष्ट्र में हैं। ये पुरानी हैं। यहां 30 गुफाएं हैं।"
    result = run_story_validation("अजंता", hook, script)
    story = result["story_structure"]
    assert story["is_valid"] is False


@pytest.mark.asyncio
async def test_content_gate_validation_passed() -> None:
    results = {
        "fact_grounding": {"is_valid": True},
        "location_accuracy": {"is_valid": True},
        "repetition_check": {"is_valid": True},
        "language_check": {"is_valid": True},
        "story_structure": {"is_valid": True},
    }
    assert validation_passed(results) is True


@pytest.mark.asyncio
async def test_content_gate_validation_failed() -> None:
    results = {
        "fact_grounding": {"is_valid": True},
        "location_accuracy": {"is_valid": False},
        "repetition_check": {"is_valid": True},
        "language_check": {"is_valid": True},
        "story_structure": {"is_valid": True},
    }
    assert validation_passed(results) is False


@pytest.mark.asyncio
async def test_content_gate_aggregate_scores() -> None:
    results = {
        "fact_grounding": {"hallucination_score": 10.0, "grounding_score": 90.0},
        "story_structure": {"structure_score": 85.0},
        "language_check": {"confidence": 95.0},
    }
    scores = aggregate_scores(results)
    assert scores["hallucination_score"] == 10.0
    assert scores["grounding_score"] == 90.0
    assert scores["story_score"] == 85.0
    assert scores["language_score"] == 95.0
