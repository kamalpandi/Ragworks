import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.dependencies import get_rag_engine
from app.evaluation.dataset import DatasetEntry, DatasetLoader
from app.evaluation.models import EvalResult
from app.services.rag_engine import RAGEngine

router = APIRouter()


@router.post("/run")
async def run_evaluation(
    dataset_name: Optional[str] = None,
    file_filter: Optional[str] = None,
    metric_names: Optional[str] = None,
    from_huggingface: Optional[str] = None,
    max_samples: int = 100,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    """Run evaluation on a dataset.

    Supports:
    - Custom JSON dataset uploaded via POST body
    - HuggingFace dataset (set from_huggingface param)
    """
    from app.evaluation.runner import EvaluationRunner

    metrics = metric_names.split(",") if metric_names else None
    runner = EvaluationRunner(rag_engine=rag_engine, metric_names=metrics)

    if from_huggingface:
        entries = DatasetLoader.from_huggingface(
            dataset_name=from_huggingface, max_samples=max_samples
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide from_huggingface dataset name or upload a JSON file.",
        )

    result = await runner.run(
        entries=entries,
        dataset_name=dataset_name or from_huggingface or "custom",
        file_filter=file_filter,
    )
    return result.model_dump()


@router.post("/run/file")
async def run_evaluation_from_file(
    file: UploadFile = File(...),
    file_filter: Optional[str] = None,
    metric_names: Optional[str] = None,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    """Run evaluation using an uploaded JSON dataset file.

    Expected JSON format: [{"question": "...", "answer": "...", "contexts": [...]}, ...]
    """
    from app.evaluation.runner import EvaluationRunner

    content = await file.read()
    data = json.loads(content)

    entries = []
    for item in data:
        entries.append(
            DatasetEntry(
                query=item.get("question", item.get("query", "")),
                ground_truth=item.get("answer", item.get("ground_truth")),
                contexts=item.get("contexts"),
            )
        )

    metrics = metric_names.split(",") if metric_names else None
    runner = EvaluationRunner(rag_engine=rag_engine, metric_names=metrics)
    result = await runner.run(
        entries=entries,
        dataset_name=file.filename or "uploaded",
        file_filter=file_filter,
    )
    return result.model_dump()


@router.get("/results")
async def list_results():
    """List all historical evaluation results."""
    from app.core.config import settings

    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "dataset_name": r.dataset_name,
            "num_samples": r.num_samples,
            "aggregated_scores": r.aggregated_scores,
        }
        for r in results
    ]


@router.get("/results/{result_id}")
async def get_result(result_id: str):
    """Get a specific evaluation result by ID."""
    from app.core.config import settings

    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    for r in results:
        if r.id == result_id:
            return r.model_dump()
    raise HTTPException(status_code=404, detail="Result not found")


@router.post("/compare")
async def compare_results(
    id_a: str,
    id_b: str,
):
    """Compare two evaluation results side-by-side."""
    from app.core.config import settings

    try:
        comparison = EvalResult.compare(id_a, id_b, settings.EVAL_RESULTS_DIR)
        return {"id_a": id_a, "id_b": id_b, "comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics")
async def list_metrics():
    """List all available evaluation metrics."""
    from app.evaluation.metrics import list_available_metrics

    return {"metrics": list_available_metrics()}
