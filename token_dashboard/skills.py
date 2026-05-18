"""Skill catalog: locate SKILL.md files and map slugs to file sizes.

A skill on disk lives at one of:
  ~/.claude/skills/<name>/SKILL.md                     -> slug "<name>"
  ~/.claude/scheduled-tasks/<name>/SKILL.md            -> slug "<name>"
  ~/.claude/plugins/marketplaces/*/plugins/<plugin>/skills/<name>/SKILL.md
      -> registers TWO slugs: "<plugin>:<name>" and "<name>"
      (Claude Code accepts either form in the Skill tool.)
  <project>/.claude/skills/<name>/SKILL.md             -> slug "<name>" (project-local)
  <project>/skills/<name>/SKILL.md                     -> slug "<name>" (legacy layout)

Sizes are in chars; token estimate is chars // 4 (the same approximation
`scanner._extract_results` uses for tool-result tokens).
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

from .db import connect


_DEFAULT_ROOTS = [
    Path.home() / ".claude" / "skills",
    Path.home() / ".claude" / "scheduled-tasks",
    Path.home() / ".claude" / "plugins",
]


_VERSION_RE = re.compile(r"^\d+\.\d+")
_STRUCTURE_NAMES = {"skills", "plugins", "marketplaces", "cache", ".claude"}


def _slugs_for(skill_md: Path) -> list[str]:
    """Return the slug(s) a Skill tool invocation could use to load this file.

    Strategy: always register the bare skill name. Additionally, walk up from
    `skills/` and register `<ancestor>:<skill>` for every ancestor segment
    that plausibly names a plugin (not a structural/version/temp-dir token).
    Unused slugs are harmless - the user only invokes real ones.
    """
    parts = skill_md.parts
    if "SKILL.md" not in parts or skill_md.name != "SKILL.md":
        return []
    skill_name = skill_md.parent.name
    slugs = {skill_name}
    try:
        skills_idx = len(parts) - 1 - parts[::-1].index("skills")
    except ValueError:
        return list(slugs)
    for seg in parts[:skills_idx]:
        if not seg or seg in _STRUCTURE_NAMES:
            continue
        if _VERSION_RE.match(seg):
            continue
        if seg.startswith("temp_git_"):
            continue
        if seg.endswith(":") or ":" in seg:  # drive letters like "C:"
            continue
        slugs.add(f"{seg}:{skill_name}")
    return sorted(slugs)


def _scan_root(root: Path, catalog: Dict[str, dict]) -> None:
    """rglob a root for SKILL.md and merge entries into catalog.
    Keep the shallowest path when slugs collide (canonical install).
    """
    if not root.is_dir():
        return
    for md in root.rglob("SKILL.md"):
        try:
            chars = md.stat().st_size
        except OSError:
            continue
        entry = {"path": str(md), "chars": chars, "tokens": chars // 4}
        for slug in _slugs_for(md):
            prev = catalog.get(slug)
            if prev is None or len(md.parts) < len(Path(prev["path"]).parts):
                catalog[slug] = entry


def _project_skill_roots(db_path) -> list[Path]:
    """Walk distinct cwds recorded in the JSONL data and yield candidate
    directories that may contain project-local SKILL.md files.

    For each cwd, we check `<cwd>/.claude/skills/` and `<cwd>/skills/`.
    A non-existent path is harmless; rglob just returns nothing.
    """
    roots: list[Path] = []
    seen: set[str] = set()
    try:
        with connect(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT cwd FROM messages WHERE cwd IS NOT NULL AND cwd != ''"
            ).fetchall()
    except Exception:
        return roots
    for r in rows:
        cwd = (r[0] or "").strip()
        if not cwd:
            continue
        try:
            base = Path(cwd)
        except Exception:
            continue
        for sub in (".claude/skills", "skills"):
            cand = base / sub
            key = str(cand).lower()
            if key in seen:
                continue
            seen.add(key)
            roots.append(cand)
    return roots


def scan_catalog(roots: Optional[Iterable[Path]] = None, db_path=None) -> Dict[str, dict]:
    """Return {slug: {path, chars, tokens}} for every SKILL.md found.

    Default roots (~/.claude/skills, ~/.claude/scheduled-tasks, ~/.claude/plugins)
    are always scanned. When `db_path` is given we additionally walk the cwds
    recorded in JSONL data to discover project-local skills.
    """
    catalog: Dict[str, dict] = {}
    base = list(roots) if roots is not None else list(_DEFAULT_ROOTS)
    if db_path:
        base.extend(_project_skill_roots(db_path))
    for root in base:
        _scan_root(Path(root), catalog)
    return catalog


_cache: dict = {"at": 0.0, "data": {}, "key": None}
_TTL_SECONDS = 60.0


def cached_catalog(db_path=None) -> Dict[str, dict]:
    """scan_catalog() with a simple in-process TTL cache.
    Cache is keyed on db_path so different DBs don't share entries.
    """
    now = time.time()
    key = str(db_path) if db_path else "_default"
    if now - _cache["at"] > _TTL_SECONDS or _cache.get("key") != key:
        _cache["data"] = scan_catalog(db_path=db_path)
        _cache["at"] = now
        _cache["key"] = key
    return _cache["data"]


def tokens_for(slug: str, catalog: Optional[Dict[str, dict]] = None) -> Optional[int]:
    cat = catalog if catalog is not None else cached_catalog()
    info = cat.get(slug)
    return info["tokens"] if info else None
