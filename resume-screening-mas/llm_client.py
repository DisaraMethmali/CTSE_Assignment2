"""
llm_client.py — Hugging Face Inference API client.
Replaces ollama for all agents. Zero local model storage needed.
"""
from __future__ import annotations
import os
import requests
from pathlib import Path


def _load_token() -> str:
    """
    Load HuggingFace API token from .env file or environment variable.

    Returns:
        API token string.

    Raises:
        ValueError: If token is not found anywhere.
    """
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("HF_TOKEN="):
                    token = line.split("=", 1)[1].strip()
    if not token:
        raise ValueError("HF_TOKEN not found. Add it to your .env file.")
    return token


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama3.2:1b",
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> str:
    """
    Send a prompt to a HuggingFace model via the free Inference API.

    Args:
        system_prompt: The agent system instructions.
        user_prompt:   The task and data to process.
        model:         HuggingFace model repo ID.
        max_tokens:    Maximum tokens to generate.
        temperature:   Sampling temperature. Lower is more deterministic.

    Returns:
        Generated text response as a string.

    Raises:
        RuntimeError: If the API call fails.
    """
    token   = _load_token()
    api_url = (
        f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "stream":      False,
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        raise RuntimeError("HuggingFace API timed out. Try again.")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"HuggingFace API error: {exc} — {response.text}")
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected API response: {exc}")


def clean_json_response(raw: str) -> str:
    """
    Remove markdown fences from LLM output if model added them.

    Args:
        raw: Raw string output from the LLM.

    Returns:
        Clean JSON string with no markdown fences.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()