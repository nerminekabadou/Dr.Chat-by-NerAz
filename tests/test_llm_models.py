from llm_models import choose_model

AVAILABLE = [
    "models/gemini-2.5-flash-lite", "models/gemini-3.8-flash", "models/gemini-3.5-flash",
    "models/gemini-3.9-flash-preview", "models/gemini-3.8-pro", "models/text-embedding-004",
]


def test_picks_newest_stable_flash():
    assert choose_model(AVAILABLE) == "gemini-3.8-flash"


def test_configured_model_wins_when_available():
    assert choose_model(AVAILABLE, "gemini-3.5-flash") == "gemini-3.5-flash"


def test_retired_configured_model_is_ignored():
    assert choose_model(AVAILABLE, "gemini-2.5-flash") == "gemini-3.8-flash"


def test_demo_prefers_newest_flash_lite():
    assert choose_model(AVAILABLE + ["models/gemini-3.5-flash-lite"], prefer_lite=True) == "gemini-3.5-flash-lite"


def test_lite_preference_falls_back_to_flash():
    assert choose_model(["models/gemini-3.8-flash"], prefer_lite=True) == "gemini-3.8-flash"
