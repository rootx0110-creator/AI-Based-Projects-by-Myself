"""Threat actor knowledge base and TTP-similarity matching."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .model import ActorMatch, TechniqueHit

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class ActorDb:
    """Loads actor profiles and scores them against detected techniques."""

    def __init__(self, path: Optional[str] = None):
        self.actors = self._load(path or os.path.join(DATA_DIR, "actor_profiles.json"))

    @staticmethod
    def _load(path: str) -> Dict[str, dict]:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def match(self, techniques: Dict[str, TechniqueHit]) -> List[ActorMatch]:
        """Score every actor against the detected technique set.

        score     = weighted overlap / total actor weight  (0..1)
        coverage  = percentage of the actor's profiled techniques observed
        """
        results: List[ActorMatch] = []
        for actor in self.actors.values():
            techs = actor.get("techniques", {})
            total_weight = 0.0
            overlap = 0.0
            matched_ids: List[str] = []
            for tid, w in techs.items():
                total_weight += w
                hit = techniques.get(tid)
                if not hit:
                    continue
                overlap += w * (hit.confidence / 100.0)
                matched_ids.append(tid)
            if total_weight <= 0:
                continue
            score = overlap / total_weight
            coverage = 100.0 * len(matched_ids) / len(techs) if techs else 0.0
            if score < 0.02:
                continue
            results.append(
                ActorMatch(
                    actor_id=actor["id"],
                    name=actor["name"],
                    aliases=actor.get("aliases", []),
                    origin=actor.get("origin", ""),
                    motivation=actor.get("motivation", ""),
                    first_seen=actor.get("first_seen", ""),
                    score=round(score, 3),
                    coverage=round(coverage, 1),
                    matched_techniques=sorted(matched_ids),
                    description=actor.get("description", ""),
                    tools=actor.get("tools", []),
                )
            )
        results.sort(key=lambda a: (-a.score, -a.coverage, a.name))
        return results

    def describe_actor(self, actor_id: str) -> Optional[dict]:
        return self.actors.get(actor_id)

    def all_actor_ids(self) -> List[str]:
        return list(self.actors.keys())