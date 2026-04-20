"""
Shared TA generation + DB lookup for Flask and offline benchmark.
Environment (optional):
  TA_MYSQL_HOST, TA_MYSQL_PORT, TA_MYSQL_USER, TA_MYSQL_PASSWORD, TA_MYSQL_DATABASE
  GOOGLE_API_KEY (or OPENAI_API_KEY) — Google AI Studio key for Gemini
  OPENAI_BASE_URL, OPENAI_MODEL — override endpoint / model id (defaults: Gemini OpenAI-compat + 2.5 Flash-Lite)
  Local LM Studio again: set OPENAI_BASE_URL=http://127.0.0.1:1234/v1, OPENAI_MODEL=..., OPENAI_API_KEY=not-needed, and do not set GOOGLE_API_KEY.
"""
from __future__ import annotations

import os
from typing import Any

import mysql.connector
from mysql.connector import Error
from openai import OpenAI

# Defaults match previous GeminiT2.py; override via env for deployment.
_DEFAULT_MYSQL = {
    "host": os.getenv("TA_MYSQL_HOST", "hopper.proxy.rlwy.net"),
    "port": int(os.getenv("TA_MYSQL_PORT", "53147")),
    "user": os.getenv("TA_MYSQL_USER", "root"),
    "password": os.getenv("TA_MYSQL_PASSWORD", "mkZkHWFzNbCYOdGEBBZpOwbqRQfQnWhx"),
    "database": os.getenv("TA_MYSQL_DATABASE", "railway"),
}


def get_db_connection():
    try:
        return mysql.connector.connect(**_DEFAULT_MYSQL)
    except Error as e:
        raise Exception(f"Database connection failed: {e}") from e


# Google Gemini via OpenAI-compatible REST (see ai.google.dev gemini-api docs / openai).
_GEMINI_OPENAI_BASE_DEFAULT = "https://generativelanguage.googleapis.com/v1beta/openai/"
_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
# Prefer env in production; fallback matches benchmark/models.json "gemini" entry for local runs.
_DEFAULT_GOOGLE_API_KEY = "AIzaSyAjA0bEES0GLrR8vPcXX5HgzpAPe4RruaM"


def default_model_config() -> dict[str, str]:
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or _DEFAULT_GOOGLE_API_KEY
    )
    return {
        "api_key": api_key,
        "base_url": os.getenv("OPENAI_BASE_URL", _GEMINI_OPENAI_BASE_DEFAULT),
        "model": os.getenv("OPENAI_MODEL", _DEFAULT_GEMINI_MODEL),
    }


def make_client(model_config: dict[str, str] | None) -> OpenAI:
    cfg = model_config or default_model_config()
    base = (cfg.get("base_url") or "").strip() or _GEMINI_OPENAI_BASE_DEFAULT
    key = (cfg.get("api_key") or "").strip() or _DEFAULT_GOOGLE_API_KEY
    return OpenAI(api_key=key, base_url=base)


def _fetch_solution_text(pdf_id: int | str | None) -> str:
    if pdf_id is None:
        return ""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT solution_text FROM exercises WHERE id = %s", (pdf_id,))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        if row and row.get("solution_text"):
            return row["solution_text"]
    except Error as e:
        print(f"Database read failed: {e}")
    return ""


def generate_gemini_response(
    user_input: str,
    pdf_id: int | str | None = None,
    remaining_time: int = 0,
    reference_solution: str | None = None,
    model_config: dict[str, str] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """
    reference_solution: if set, used instead of DB for this call (benchmark / offline).
    model_config: {"api_key","base_url","model"}; None -> env / LM Studio defaults.
    """
    if not user_input:
        raise ValueError("Input cannot be empty")

    solution_text = (reference_solution or "").strip()
    if not solution_text and pdf_id is not None:
        solution_text = _fetch_solution_text(pdf_id)

    grading_keywords = [
        "score my answer",
        "my answer is",
        "grade my answer",
        "the answer is",
        "grade",
        "grade my answer",
        "please score",
        "bewerte",
        "bewerte meine Antwort",
    ]

    if any(keyword in user_input for keyword in grading_keywords):
        system = (
            "You are a strict but fair teaching assistant. "
            "Score strictly according to the rubric and output ONLY valid JSON in this format: "
            '{"score":x,"max_score":y,"reasoning":"...","items":[{"sub":"1","score":...}]}'
        )
        prompt_to_use = (
            f"Question & reference solution:\n{solution_text}\n\n"
            f"Student answer:\n{user_input}\n\n"
            f"Return only JSON."
        )
    else:
        if remaining_time > 0:
            system = (
                "You are a teaching assistant. The timer is still running. "
                "Do NOT reveal final answers. Only provide hints, scaffolding questions, and high-level reasoning. "
                "Respond in English or German depending on the user's language."
            )
        else:
            system = (
                "You are a teaching assistant. The time is over. "
                "Provide a full step-by-step explanation and the final answer. "
                "Respond in English or German depending on the user's language."
            )
        prompt_to_use = (
            f"(Optional reference solution — do not leak final answer before time is over):\n{solution_text}\n\n"
            f"User query:\n{user_input}"
        )

    cfg = model_config or default_model_config()
    model_id = cfg.get("model") or default_model_config()["model"]
    client = make_client(cfg)
    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_to_use},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        raise Exception(f"LLM request failed: {e}") from e
