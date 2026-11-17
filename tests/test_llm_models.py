import llm_models
from llm_models import choose_model, generate_text, ranked_models

AVAILABLE = [
    "models/gemini-2.5-flash-lite", "models/gemini-3.8-flash", "models/gemini-3.5-flash",
    "models/gemini-3.9-flash-preview", "models/gemini-3.8-pro", "models/text-embedding-004",
]


def test_aliases_come_first_then_newest_versions():
    assert ranked_models(AVAILABLE)[:4] == [
        "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.5-flash"]


def test_demo_prefers_lite():
    assert ranked_models(AVAILABLE, prefer_lite=True)[:3] == [
        "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite"]


def test_configured_model_is_tried_first():
    assert ranked_models(AVAILABLE, "gemini-3.5-flash")[0] == "gemini-3.5-flash"


def test_choose_model_skips_models_missing_from_the_list():
    assert choose_model(AVAILABLE) == "gemini-3.8-flash"


class FakeGenAI:
    """Simulates an account where some listed models are not usable."""

    def __init__(self, usable):
        self.usable, self.calls = usable, []

    def list_models(self):
        class M:
            def __init__(self, name):
                self.name, self.supported_generation_methods = name, ["generateContent"]
        return [M(n) for n in AVAILABLE]

    def GenerativeModel(self, name):
        genai = self

        class Model:
            def generate_content(self, prompt, request_options=None):
                genai.calls.append(name)
                if name not in genai.usable:
                    raise RuntimeError(f"404 models/{name} is no longer available to new users")

                class R:
                    text = f"answer from {name}"
                return R()
        return Model()


def test_falls_through_unavailable_models_and_remembers_the_working_one(monkeypatch):
    monkeypatch.setattr(llm_models, "_working_model", None)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    fake = FakeGenAI(usable={"gemini-3.5-flash"})
    assert generate_text(fake, "hi") == "answer from gemini-3.5-flash"
    assert fake.calls == ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-3.5-flash"]
    fake.calls.clear()
    generate_text(fake, "again")
    assert fake.calls == ["gemini-3.5-flash"]


def test_other_errors_are_not_swallowed(monkeypatch):
    monkeypatch.setattr(llm_models, "_working_model", None)

    class QuotaGenAI(FakeGenAI):
        def GenerativeModel(self, name):
            class Model:
                def generate_content(self, prompt, request_options=None):
                    raise RuntimeError("429 quota exceeded")
            return Model()

    try:
        generate_text(QuotaGenAI(set()), "hi")
    except RuntimeError as error:
        assert "429" in str(error)
    else:
        raise AssertionError("expected the quota error to propagate")
