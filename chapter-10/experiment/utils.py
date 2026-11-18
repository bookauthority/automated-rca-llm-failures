from __future__ import annotations

import platform
from typing import Dict


def get_environment_info() -> Dict[str, str]:
    """Return a small descriptor of the runtime environment.

    This is used purely for evidence metadata, not for metrics.
    """

    return {
        "os": platform.system(),
        "python": platform.python_version(),
    }
