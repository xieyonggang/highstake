"""Manages pre-generated filler audio for agents."""

import glob
import logging
import os
import random
from typing import Optional

logger = logging.getLogger(__name__)


class FillerService:
    """Loads and serves pre-generated filler audio URLs."""

    def __init__(self):
        self._fillers: dict[str, list[str]] = {}
        self._load_fillers()

    def _load_fillers(self) -> None:
        """Scan resources/agent_fillers/ and build URL map."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fillers_dir = os.path.join(base_dir, "resources", "agent_fillers")

        if not os.path.isdir(fillers_dir):
            logger.info("No agent_fillers directory found — fillers disabled")
            return

        for agent_id in sorted(os.listdir(fillers_dir)):
            agent_dir = os.path.join(fillers_dir, agent_id)
            if not os.path.isdir(agent_dir):
                continue

            wavs = sorted(glob.glob(os.path.join(agent_dir, "*.wav")))
            if wavs:
                self._fillers[agent_id] = [
                    f"/api/resources/agent_fillers/{agent_id}/{os.path.basename(w)}"
                    for w in wavs
                ]
                logger.info(
                    f"Loaded {len(wavs)} filler(s) for {agent_id}"
                )

    def get_random_filler(self, agent_id: str) -> Optional[str]:
        """Return a random filler audio URL for the agent."""
        fillers = self._fillers.get(agent_id, [])
        return random.choice(fillers) if fillers else None

    def get_all_filler_urls(self) -> dict[str, list[str]]:
        """Return all filler URLs for frontend pre-fetching."""
        return dict(self._fillers)
