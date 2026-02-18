"""Loads and caches agent template files from app/agents/templates/."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level cache: {agent_id: {filename_stem: content}}
_template_cache: dict[str, dict[str, str]] = {}

# Path to templates directory (server/app/agents/templates)
_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "agents" / "templates"


def load_templates(templates_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """Read all .md files under app/agents/templates/<agent_id>/ and cache them.

    Returns dict like:
        {"skeptic": {"persona": "...", "domain-knowledge": "..."}, ...}
    """
    global _template_cache

    if _template_cache:
        return _template_cache

    base = templates_dir or _TEMPLATES_DIR
    if not base.is_dir():
        logger.warning(f"Templates directory not found: {base}")
        return {}

    cache: dict[str, dict[str, str]] = {}
    for agent_dir in sorted(base.iterdir()):
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        cache[agent_id] = {}
        for md_file in sorted(agent_dir.glob("*.md")):
            stem = md_file.stem  # e.g. "persona", "domain-knowledge"
            try:
                content = md_file.read_text(encoding="utf-8")
                cache[agent_id][stem] = content
                logger.debug(f"Loaded template: {agent_id}/{stem} ({len(content)} chars)")
            except Exception as e:
                logger.error(f"Failed to read template {md_file}: {e}")

    _template_cache = cache
    logger.info(
        f"Loaded templates for {len(cache)} agents: "
        f"{', '.join(cache.keys())}"
    )
    return _template_cache


def get_template(agent_id: str, template_name: str) -> str | None:
    """Get a specific template for an agent. Loads cache if needed."""
    templates = load_templates()
    agent_templates = templates.get(agent_id, {})
    return agent_templates.get(template_name)


def get_agent_templates(agent_id: str) -> dict[str, str]:
    """Get all templates for an agent."""
    templates = load_templates()
    return templates.get(agent_id, {})


def clear_cache() -> None:
    """Clear the template cache (useful for testing)."""
    global _template_cache
    _template_cache = {}
