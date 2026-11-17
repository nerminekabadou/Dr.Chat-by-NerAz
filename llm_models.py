"""Pick a Gemini model that the API key can actually use.

Google retires model versions and new keys lose access to older ones, so a
hard-coded name eventually breaks. GEMINI_MODEL is used when it is available;
otherwise the newest stable "flash" model that supports generateContent.
"""

import os
import re

_EXCLUDED = ("preview", "exp", "image", "tts", "live", "audio", "embedding", "thinking", "lite")
_VERSION = re.compile(r"gemini-(\d+(?:\.\d+)?)-flash")


def choose_model(available, preferred=None):
    """Return the model to use from a list of model ids (with or without 'models/')."""
    names = [m.split("/", 1)[-1] for m in available]
    if preferred and preferred.split("/", 1)[-1] in names:
        return preferred.split("/", 1)[-1]
    candidates = []
    for name in names:
        match = _VERSION.fullmatch(name)
        if match and not any(word in name for word in _EXCLUDED):
            candidates.append((float(match.group(1)), name))
    if candidates:
        return max(candidates)[1]
    flash = [n for n in names if "flash" in n]
    return (flash or names or [preferred or "gemini-flash-latest"])[0]


_resolved = None


def resolve_gemini_model(genai):
    """Resolve once per process, using the configured google.generativeai module."""
    global _resolved
    if _resolved is None:
        preferred = os.getenv("GEMINI_MODEL")
        try:
            available = [m.name for m in genai.list_models()
                         if "generateContent" in getattr(m, "supported_generation_methods", [])]
        except Exception:
            return preferred or "gemini-flash-latest"
        _resolved = choose_model(available, preferred)
    return _resolved
