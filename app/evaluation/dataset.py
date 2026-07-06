import json
from typing import AsyncIterator, Dict, List, Optional

from datasets import load_dataset


class DatasetEntry:
    def __init__(
        self,
        query: str,
        ground_truth: Optional[str] = None,
        contexts: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ):
        self.query = query
        self.ground_truth = ground_truth
        self.contexts = contexts or []
        self.metadata = metadata or {}


class DatasetLoader:
    """Load evaluation datasets from various sources.

    Supported formats:
    - JSON (list of {question, answer, contexts?})
    - CSV (columns: question, answer, contexts?)
    - HuggingFace datasets (using the 'datasets' library)
    """

    @staticmethod
    def from_json(filepath: str) -> List[DatasetEntry]:
        with open(filepath) as f:
            data = json.load(f)
        entries = []
        for item in data:
            entries.append(
                DatasetEntry(
                    query=item.get("question", item.get("query", "")),
                    ground_truth=item.get("answer", item.get("ground_truth")),
                    contexts=item.get("contexts"),
                    metadata=item.get("metadata"),
                )
            )
        return entries

    @staticmethod
    def from_csv(filepath: str) -> List[DatasetEntry]:
        import csv

        entries = []
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(
                    DatasetEntry(
                        query=row.get("question", row.get("query", "")),
                        ground_truth=row.get("answer", row.get("ground_truth")),
                        contexts=json.loads(row["contexts"])
                        if row.get("contexts")
                        else None,
                    )
                )
        return entries

    @staticmethod
    def from_huggingface(
        dataset_name: str,
        split: str = "test",
        question_field: str = "question",
        answer_field: str = "answer",
        contexts_field: Optional[str] = "contexts",
        max_samples: int = 100,
    ) -> List[DatasetEntry]:
        ds = load_dataset(dataset_name, split=split)
        entries = []
        for i, row in enumerate(ds):
            if i >= max_samples:
                break
            entries.append(
                DatasetEntry(
                    query=row[question_field],
                    ground_truth=row.get(answer_field),
                    contexts=(
                        list(row[contexts_field])
                        if contexts_field and contexts_field in row
                        else None
                    ),
                )
            )
        return entries

    @staticmethod
    async def iterate(
        entries: List[DatasetEntry],
    ) -> AsyncIterator[DatasetEntry]:
        for entry in entries:
            yield entry
