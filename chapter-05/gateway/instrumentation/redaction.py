import hashlib
from typing import Dict, Any


def load_redaction_config(path: str) -> Dict[str, Any]:
    """Load a very small subset of YAML syntax used in instrumentation.yaml.

    We avoid importing PyYAML and instead parse the tiny subset we use:
    - top-level key: value
    - no nesting other than booleans and strings
    """

    config: Dict[str, Any] = {
        "redact_content": True,
        "hash_ids": True,
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" not in line:
                    continue
                key, value = [p.strip() for p in line.split(":", 1)]
                if value.lower() in {"true", "false"}:
                    config[key] = value.lower() == "true"
                else:
                    config[key] = value
    except FileNotFoundError:
        # Fall back to defaults
        pass
    return config


class Redactor:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.redact_content = bool(config.get("redact_content", True))
        self.hash_ids_flag = bool(config.get("hash_ids", True))

    def hash_value(self, value: str) -> str:
        if not value or not self.hash_ids_flag:
            return ""
        h = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return h

    def redact_text(self, text: str) -> str:
        if not self.redact_content:
            return text
        if not text:
            return ""
        # Simple strategy: keep first 10 characters and length
        prefix = text[:10]
        return f"{prefix}...[len={len(text)}]"
