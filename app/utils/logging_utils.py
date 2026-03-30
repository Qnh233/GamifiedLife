import json
import logging
import os
import re
from datetime import datetime
from typing import Any


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _mask_text(text: str) -> str:
    if not text:
        return text
    # email
    text = re.sub(r"([A-Za-z0-9_.+-]+)@([A-Za-z0-9-]+\.[A-Za-z0-9-.]+)", "***@***", text)
    # phone (very rough)
    text = re.sub(r"\b1[3-9]\d{9}\b", "***********", text)
    return text


def preview_text(text: Any, max_len: int = 300) -> str | None:
    mode = os.getenv("LOG_CONTENT_MODE", "masked").lower()  # full | masked | none
    if mode == "none":
        return None

    s = str(text) if text is not None else ""
    if mode == "masked":
        s = _mask_text(s)

    if len(s) > max_len:
        return s[:max_len] + "...(truncated)"
    return s


def log_event(logger: logging.Logger, event: str, level: str = "info", preview: bool = True, **fields: Any) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": preview_text(event) if preview else event,
        **fields,
    }
    msg = json.dumps(payload, ensure_ascii=False, default=str)
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(msg)
