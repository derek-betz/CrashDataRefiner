"""Orchestrator registration helper for CrashDataRefiner."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

HUB_URL = os.getenv("ROADSCRIPT_HUB_URL", "http://127.0.0.1:9000").rstrip("/")
AGENT_NAME = os.getenv("AGENT_NAME", "CrashDataRefiner")
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:9005")


def register_agent(capabilities: list[str] | None = None) -> None:
    payload = {
        "name": AGENT_NAME,
        "base_url": AGENT_BASE_URL,
        "capabilities": capabilities or ["crash-data", "kmz", "reports"],
        "metadata": {},
    }
    try:
        requests.post(f"{HUB_URL}/registry/register", json=payload, timeout=5)
        logger.info("Registered %s with orchestrator", AGENT_NAME)
    except Exception as exc:  # pragma: no cover
        logger.warning("Unable to register with orchestrator: %s", exc)


def publish_knowledge(item: dict[str, Any]) -> None:
    try:
        requests.post(f"{HUB_URL}/knowledge/ingest", json=item, timeout=5)
    except Exception as exc:  # pragma: no cover
        logger.warning("Unable to publish knowledge: %s", exc)


def fetch_knowledge(
    *,
    source: str | None = None,
    topic: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    params = {"limit": limit}
    if source:
        params["source"] = source
    if topic:
        params["topic"] = topic
    if tag:
        params["tag"] = tag
    response = requests.get(f"{HUB_URL}/knowledge/query", params=params, timeout=5)
    response.raise_for_status()
    return response.json()
