import json
import os
from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class MetricScore(BaseModel):
    name: str
    value: float
    description: str = ""


class EvalResult(BaseModel):
    id: str = Field(default_factory=lambda: os.urandom(8).hex())
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    dataset_name: str
    num_samples: int
    metrics: List[MetricScore]
    aggregated_scores: dict[str, float] = Field(default_factory=dict)
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    thread_id: str | None = None
    thread_label: str | None = None

    def store(self, results_dir: str = "eval_results"):
        os.makedirs(results_dir, exist_ok=True)
        path = os.path.join(
            results_dir,
            f"eval_{self.id}_{self.timestamp.replace(':', '-')}.json",
        )
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def list_results(cls, results_dir: str = "eval_results") -> List["EvalResult"]:
        if not os.path.isdir(results_dir):
            return []
        results = []
        for fname in sorted(os.listdir(results_dir)):
            if fname.startswith("eval_") and fname.endswith(".json"):
                with open(os.path.join(results_dir, fname)) as f:
                    results.append(cls.model_validate(json.load(f)))
        return results

    @classmethod
    def compare(
        cls, id_a: str, id_b: str, results_dir: str = "eval_results"
    ) -> dict[str, dict[str, float]]:
        results = {r.id: r for r in cls.list_results(results_dir)}
        a = results.get(id_a)
        b = results.get(id_b)
        if not a or not b:
            raise ValueError("One or both result IDs not found")
        comparison = {}
        all_metric_names = set(a.aggregated_scores.keys()) | set(
            b.aggregated_scores.keys()
        )
        for name in all_metric_names:
            comparison[name] = {
                "a": a.aggregated_scores.get(name, 0),
                "b": b.aggregated_scores.get(name, 0),
                "delta": b.aggregated_scores.get(name, 0)
                - a.aggregated_scores.get(name, 0),
            }
        return comparison
