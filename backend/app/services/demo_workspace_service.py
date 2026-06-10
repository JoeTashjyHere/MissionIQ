"""Demo workspace loader — safe, idempotent showcase environment."""
from __future__ import annotations

from seeds.apex.seed import load_apex_workspace


async def load_demo_workspace(*, if_empty: bool = False) -> dict[str, str]:
    """Load the Apex Federal showcase workspace. No external integrations required."""
    return await load_apex_workspace(if_empty=if_empty)
