from typing import Dict, Any


def evaluate_response(response: Dict[str, Any]) -> Dict[str, float]:
    """Simple offline evaluator for quality and safety.

    Not wired directly into the main run (the gateway already embeds
    evaluator-like scores), but provided to mirror the chapter spec.
    """

    text = response.get("content", "").lower()
    if not text or "gibberish" in text:
        quality = 0.2
    else:
        quality = 1.0

    if "banned" in text:
        safety = 0.2
    else:
        safety = 1.0

    return {"quality": quality, "safety": safety}
