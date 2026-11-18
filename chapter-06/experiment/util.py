from __future__ import annotations

import json
import os
from typing import Iterable, Dict, Any

from .events import RCAEvent


def write_jsonl(path: str, events: Iterable[RCAEvent]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev.to_dict()) + "\n")


def read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
