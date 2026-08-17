"""Shared LLM fallback helper for blog agents."""

import logging
import os

from google import genai as google_genai
from anthropic import Anthropic

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-flash-latest",
]

CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-latest",
]


def _gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    client = google_genai.Client(api_key=api_key)
    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("empty Gemini response")
            logger.info("[LLM] Gemini model used: %s", model_name)
            return text
        except Exception as exc:
            last_error = exc
            logger.warning("[LLM] Gemini unavailable (%s): %s", model_name, exc)
    raise RuntimeError(f"Gemini unavailable: {last_error}")


def _claude(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    client = Anthropic(api_key=api_key)
    last_error = None
    for model_name in CLAUDE_MODELS:
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=8192,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            text_parts = [
                block.text for block in message.content
                if getattr(block, "type", None) == "text"
            ]
            text = "\n".join(text_parts).strip()
            if not text:
                raise RuntimeError("empty Claude response")
            logger.info("[LLM] Claude model used: %s", model_name)
            return text
        except Exception as exc:
            last_error = exc
            logger.warning("[LLM] Claude unavailable (%s): %s", model_name, exc)
    raise RuntimeError(f"Claude unavailable: {last_error}")


def get_llm_response(prompt: str) -> str:
    """Try Gemini once, then immediately fail over to Claude."""
    errors = []
    try:
        return _gemini(prompt)
    except Exception as exc:
        errors.append(str(exc))
        logger.warning("[LLM] Switching Gemini -> Claude")

    try:
        return _claude(prompt)
    except Exception as exc:
        errors.append(str(exc))

    raise RuntimeError("All LLM providers failed: " + " | ".join(errors))
