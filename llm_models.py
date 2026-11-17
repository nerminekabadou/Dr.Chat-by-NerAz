"""Call a Gemini model that the API key can actually use.

Google retires model versions, and new keys lose access to older ones even
while those models still appear in the model list. Hard-coding a name breaks
sooner or later, so candidates are tried in order and the first model that
answers is remembered:

  1. GEMINI_MODEL, if set;
  2. Google's maintained aliases (gemini-flash-latest / gemini-flash-lite-latest);
  3. versioned Flash models from the account's model list, newest first.

With prefer_lite (the public demo), Flash-Lite comes first: it has much higher
free-tier rate limits.
"""

import os
import re

_EXCLUDED = ("preview", "exp", "image", "tts", "live", "audio", "embedding", "thinking")
_VERSION = re.compile(r"gemini-(\d+(?:\.\d+)?)-flash(-lite)?")


def ranked_models(available, preferred=None, prefer_lite=False):
    """Order candidate model ids (with or without 'models/') from best to worst."""
    names = [m.split("/", 1)[-1] for m in available]
    aliases = ["gemini-flash-lite-latest", "gemini-flash-latest"]
    if not prefer_lite:
        aliases.reverse()
    versioned = []
    for name in names:
        match = _VERSION.fullmatch(name)
        if match and not any(word in name for word in _EXCLUDED):
            is_lite = bool(match.group(2))
            versioned.append((is_lite == prefer_lite, float(match.group(1)), name))
    ordered = [preferred.split("/", 1)[-1]] if preferred else []
    ordered += aliases + [name for *_, name in sorted(versioned, reverse=True)]
    return list(dict.fromkeys(ordered))  # de-duplicate, keep order


def choose_model(available, preferred=None, prefer_lite=False):
    """Best candidate that appears in the model list (used for display and tests)."""
    names = {m.split("/", 1)[-1] for m in available}
    ranked = ranked_models(available, preferred, prefer_lite)
    return next((m for m in ranked if m in names), ranked[0])


def _is_unavailable(error):
    text = str(error).lower()
    return type(error).__name__ in ("NotFound", "PermissionDenied") or "404" in text \
        or "not found" in text or "no longer available" in text


_working_model = None


def generate_text(genai, prompt, request_options=None):
    """Generate with the first candidate model that is available to this key."""
    global _working_model
    if _working_model:
        candidates = [_working_model]
    else:
        try:
            available = [m.name for m in genai.list_models()
                         if "generateContent" in getattr(m, "supported_generation_methods", [])]
        except Exception:
            available = []
        candidates = ranked_models(available, os.getenv("GEMINI_MODEL"),
                                   prefer_lite=bool(os.getenv("DEMO_MODE")))
    last_error = None
    for name in candidates:
        try:
            text = genai.GenerativeModel(name).generate_content(
                prompt, request_options=request_options or {}).text
            _working_model = name
            return text
        except Exception as error:
            if not _is_unavailable(error):
                raise
            last_error = error
    if _working_model:  # the remembered model was retired: search again once
        _working_model = None
        return generate_text(genai, prompt, request_options)
    raise last_error
