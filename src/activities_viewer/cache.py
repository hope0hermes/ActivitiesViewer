"""
Persistent cache for ActivitiesViewer.

Manages a ``~/.activitiesviewer/`` directory for storing data that should
survive across Streamlit sessions (chat history, geocoding cache, etc.).
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".activitiesviewer"
CHAT_HISTORY_FILE = CACHE_DIR / "chat_history.json"
MEMORY_SUMMARIES_FILE = CACHE_DIR / "memory_summaries.json"
GEOCODE_CACHE_FILE = CACHE_DIR / "geocode_cache.json"

# Limits
MAX_CHAT_EXCHANGES = 50  # consolidate after this many raw exchanges
MAX_MEMORY_SUMMARIES = 20  # keep last N consolidated summaries


def _ensure_cache_dir() -> Path:
    """Create the cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


# ── Chat history ─────────────────────────────────────────────────────────


def load_chat_history() -> list[dict]:
    """
    Load saved chat exchanges from disk.

    Returns a list of exchange dicts::

        [
            {
                "timestamp": "2026-02-07T10:30:00Z",
                "user": "How is my FTP trending?",
                "assistant": "Your FTP has increased …"
            },
            …
        ]
    """
    if not CHAT_HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-MAX_CHAT_EXCHANGES:]
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load chat history: %s", exc)
        return []


def save_chat_exchange(user_msg: str, assistant_msg: str) -> None:
    """Append a single question/answer pair and persist to disk."""
    _ensure_cache_dir()
    history = load_chat_history()
    history.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "user": user_msg,
            "assistant": assistant_msg,
        }
    )
    try:
        CHAT_HISTORY_FILE.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to save chat history: %s", exc)


def needs_consolidation() -> bool:
    """Check whether the raw chat history has reached the consolidation threshold."""
    return len(load_chat_history()) >= MAX_CHAT_EXCHANGES


def build_history_context(max_exchanges: int = 10) -> str:
    """
    Build a text block summarising recent past conversations for the LLM.

    Only the last *max_exchanges* are included to respect token budgets.
    """
    history = load_chat_history()
    if not history:
        return ""

    recent = history[-max_exchanges:]
    lines = ["=== PREVIOUS CONVERSATION HISTORY ==="]
    lines.append(
        f"({len(recent)} of {len(history)} past exchanges shown)\n"
    )
    for exchange in recent:
        ts = exchange.get("timestamp", "")
        date_str = ts[:10] if ts else "unknown"
        lines.append(f"[{date_str}] User: {exchange['user']}")
        # Truncate very long responses to a summary length
        answer = exchange.get("assistant", "")
        if len(answer) > 500:
            answer = answer[:500] + "… [truncated]"
        lines.append(f"Assistant: {answer}\n")

    return "\n".join(lines)

# ── Memory summaries (long-term consolidated knowledge) ─────────────────


def load_memory_summaries() -> list[dict]:
    """
    Load consolidated memory summaries from disk.

    Each summary is::

        {
            "timestamp": "2026-02-07T12:00:00Z",
            "period": "2026-01-15 to 2026-02-07",
            "exchanges_consolidated": 50,
            "summary": "Key insights: athlete’s FTP rose from …"
        }
    """
    if not MEMORY_SUMMARIES_FILE.exists():
        return []

    try:
        data = json.loads(MEMORY_SUMMARIES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-MAX_MEMORY_SUMMARIES:]
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load memory summaries: %s", exc)
        return []


def save_memory_summary(summary_text: str, exchanges: list[dict]) -> None:
    """
    Persist a new consolidated summary and clear the raw exchanges.

    Args:
        summary_text: The LLM-generated summary of the conversation batch.
        exchanges: The raw exchanges that were summarised (for metadata).
    """
    _ensure_cache_dir()
    summaries = load_memory_summaries()

    # Derive the time period covered
    timestamps = [e.get("timestamp", "") for e in exchanges if e.get("timestamp")]
    period_start = timestamps[0][:10] if timestamps else "unknown"
    period_end = timestamps[-1][:10] if timestamps else "unknown"

    summaries.append(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "period": f"{period_start} to {period_end}",
            "exchanges_consolidated": len(exchanges),
            "summary": summary_text,
        }
    )
    summaries = summaries[-MAX_MEMORY_SUMMARIES:]

    try:
        MEMORY_SUMMARIES_FILE.write_text(
            json.dumps(summaries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to save memory summary: %s", exc)

    # Clear the raw exchanges now that they’re consolidated
    try:
        CHAT_HISTORY_FILE.write_text("[]", encoding="utf-8")
        logger.info(
            "Consolidated %d exchanges into memory summary (period: %s to %s)",
            len(exchanges),
            period_start,
            period_end,
        )
    except OSError as exc:
        logger.warning("Failed to clear raw history after consolidation: %s", exc)


def build_consolidation_prompt(exchanges: list[dict]) -> str:
    """
    Build the prompt that asks the LLM to summarise a batch of exchanges.

    The summary should capture:
    - Key athlete insights (strengths, weaknesses, injury history)
    - Advice given and whether it was followed
    - FTP/fitness trajectory observations
    - Recurring themes or concerns
    - Any goals, targets, or deadlines mentioned
    """
    lines = []
    for ex in exchanges:
        ts = ex.get("timestamp", "")[:10]
        lines.append(f"[{ts}] Athlete: {ex['user']}")
        lines.append(f"Coach: {ex['assistant']}\n")
    conversation_text = "\n".join(lines)

    return f"""You are consolidating a coaching conversation history into a durable memory summary.

Below are {len(exchanges)} exchanges between an athlete and their AI cycling coach.
Your task is to produce a **concise, structured summary** that preserves the most valuable
information for future coaching sessions. This summary will be the ONLY record of these
conversations going forward.

## What to capture:
1. **Athlete profile updates** — any new info about FTP, weight, W/kg, injuries, equipment, schedule
2. **Key insights** — strengths, weaknesses, limiters identified during analysis
3. **Advice given** — specific training recommendations, workout prescriptions, recovery guidance
4. **Progress tracking** — did the athlete follow earlier advice? What improved or regressed?
5. **Goals & deadlines** — target events, W/kg goals, FTP targets, timeline
6. **Recurring themes** — patterns in questions (e.g., always asking about recovery, concerned about overtraining)
7. **Data observations** — notable trends in CTL, FTP evolution, efficiency factor, TID

## Format:
Use clear sections with bullet points. Be specific with numbers and dates.
Keep it under 800 words — this must fit within a token budget alongside fresh data.

## Conversation to summarise:
{conversation_text}"""


def build_memory_context() -> str:
    """
    Build a text block from all stored memory summaries for LLM injection.

    Returns an empty string if no summaries exist.
    """
    summaries = load_memory_summaries()
    if not summaries:
        return ""

    lines = ["=== LONG-TERM COACHING MEMORY ==="]
    lines.append(
        f"({len(summaries)} consolidated memory blocks spanning your coaching history)\n"
    )
    for i, s in enumerate(summaries, 1):
        lines.append(
            f"--- Memory block {i} (period: {s['period']}, "
            f"{s['exchanges_consolidated']} exchanges) ---"
        )
        lines.append(s["summary"])
        lines.append("")

    return "\n".join(lines)

# ── Geocoding cache ──────────────────────────────────────────────────────


def load_geocode_cache() -> dict[str, str]:
    """Load the persistent geocoding cache."""
    if not GEOCODE_CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(GEOCODE_CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load geocode cache: %s", exc)
        return {}


def save_geocode_cache(cache: dict[str, str]) -> None:
    """Persist the geocoding cache to disk."""
    _ensure_cache_dir()
    try:
        GEOCODE_CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to save geocode cache: %s", exc)


# ── Cache management ─────────────────────────────────────────────────────


def get_cache_size() -> dict[str, str]:
    """Return human-readable sizes of cached data."""
    info: dict[str, str] = {}
    if CHAT_HISTORY_FILE.exists():
        history = load_chat_history()
        size_kb = CHAT_HISTORY_FILE.stat().st_size / 1024
        info["Chat history"] = f"{len(history)} exchanges ({size_kb:.1f} KB)"
    if MEMORY_SUMMARIES_FILE.exists():
        summaries = load_memory_summaries()
        size_kb = MEMORY_SUMMARIES_FILE.stat().st_size / 1024
        total_exchanges = sum(s.get("exchanges_consolidated", 0) for s in summaries)
        info["Long-term memory"] = (
            f"{len(summaries)} summaries from {total_exchanges} exchanges ({size_kb:.1f} KB)"
        )
    if GEOCODE_CACHE_FILE.exists():
        geocache = load_geocode_cache()
        size_kb = GEOCODE_CACHE_FILE.stat().st_size / 1024
        info["Geocode cache"] = f"{len(geocache)} locations ({size_kb:.1f} KB)"
    if not info:
        info["Status"] = "Cache is empty"
    return info


def clear_cache() -> None:
    """Delete the entire ``~/.activitiesviewer/`` directory."""
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        logger.info("Cache cleared: %s", CACHE_DIR)


def clear_chat_history() -> None:
    """Delete only the chat history file."""
    if CHAT_HISTORY_FILE.exists():
        CHAT_HISTORY_FILE.unlink()
        logger.info("Chat history cleared")


def clear_memory() -> None:
    """Delete memory summaries and chat history (full conversation reset)."""
    clear_chat_history()
    if MEMORY_SUMMARIES_FILE.exists():
        MEMORY_SUMMARIES_FILE.unlink()
        logger.info("Memory summaries cleared")
