"""Pricing table + plan-aware cost formatting."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, Union

from .db import connect


# Claude Code writes context-window and speed variants into the model field,
# e.g. "claude-opus-5[1m]", and the transcripts also carry dated snapshot ids
# such as "claude-haiku-4-5-20251001". Both bill at the base model's rate, so
# they are reduced to the base id before the table lookup rather than falling
# through to the coarser tier guess.
_VARIANT_SUFFIX = re.compile(r"\[[^\]]*\]$")
_DATE_SUFFIX = re.compile(r"-\d{8}$")

# Ordered longest-first so "fable" is tested before a shorter token could win.
_TIERS = ("fable", "mythos", "opus", "sonnet", "haiku")


def load_pricing(path: Union[str, Path]) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_model(model: str) -> str:
    """Reduce a model id to the entry the pricing table is keyed on.

    `claude-opus-5[1m]` and `claude-haiku-4-5-20251001` both price as their
    base model.
    """
    name = _VARIANT_SUFFIX.sub("", (model or "").strip())
    return _DATE_SUFFIX.sub("", name)


def _tier_from_name(model: str) -> Optional[str]:
    m = (model or "").lower()
    for tier in _TIERS:
        if tier in m:
            # Mythos is priced as Fable; the table has no separate mythos tier.
            return "fable" if tier == "mythos" else tier
    return None


def cost_for(model: str, usage: dict, pricing: dict) -> dict:
    """Return {usd, estimated, breakdown}. usd=None when no tier match."""
    name = normalize_model(model)
    rates = pricing["models"].get(name)
    estimated = False
    if rates is None:
        tier = _tier_from_name(name)
        if tier and tier in pricing["tier_fallback"]:
            rates = pricing["tier_fallback"][tier]
            estimated = True
        else:
            return {"usd": None, "estimated": True, "breakdown": {}}
    bd = {
        "input":           usage["input_tokens"]            * rates["input"]           / 1_000_000,
        "output":          usage["output_tokens"]           * rates["output"]          / 1_000_000,
        "cache_read":      usage["cache_read_tokens"]       * rates["cache_read"]      / 1_000_000,
        "cache_create_5m": usage["cache_create_5m_tokens"]  * rates["cache_create_5m"] / 1_000_000,
        "cache_create_1h": usage["cache_create_1h_tokens"]  * rates["cache_create_1h"] / 1_000_000,
    }
    return {"usd": round(sum(bd.values()), 6), "estimated": estimated, "breakdown": bd}


def rates_for_tier(tier: str, pricing: dict) -> Optional[dict]:
    """Per-tier rates, for callers comparing what a turn would cost elsewhere."""
    return pricing.get("tier_fallback", {}).get(tier)


def get_plan(db_path: Union[str, Path], default: str = "api") -> str:
    with connect(db_path) as c:
        row = c.execute("SELECT v FROM plan WHERE k='plan'").fetchone()
    return row["v"] if row else default


def set_plan(db_path: Union[str, Path], plan: str) -> None:
    with connect(db_path) as c:
        c.execute("INSERT OR REPLACE INTO plan (k, v) VALUES ('plan', ?)", (plan,))
        c.commit()


def format_for_user(api_cost_usd: float, plan: str, pricing: dict) -> dict:
    p = pricing["plans"].get(plan, pricing["plans"]["api"])
    if plan == "api" or p["monthly"] == 0:
        return {"display_usd": api_cost_usd, "subtitle": None, "subscription_usd": None}
    return {
        "display_usd":      api_cost_usd,
        "subtitle":         f"You pay ${p['monthly']}/mo on {p['label']}",
        "subscription_usd": p["monthly"],
    }
