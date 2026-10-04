import asyncio
import json
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.core.config import settings
from app.core.dependencies import get_rag_engine
from app.evaluation.dataset import DatasetEntry, DatasetLoader
from app.evaluation.models import EvalResult
from app.services.conversation_service import get_thread
from app.services.rag_engine import RAGEngine

router = APIRouter()

_eval_jobs: dict[str, dict] = {}


async def _run_eval_background(
    run_id: str,
    entries: list[DatasetEntry],
    dataset_name: str,
    metric_names: list[str] | None,
    file_filter: str | None,
    rag_engine: RAGEngine,
    thread_id: str | None = None,
    thread_label: str | None = None,
):
    from app.evaluation.runner import EvaluationRunner

    runner = EvaluationRunner(
        rag_engine=rag_engine,
        metric_names=metric_names,
        progress_callback=lambda current, total: _eval_jobs.update(
            {run_id: {"status": "running", "current": current, "total": total}}
        ),
    )
    try:
        result = await runner.run(
            entries=entries,
            dataset_name=dataset_name,
            file_filter=file_filter,
        )
        if thread_id:
            result.thread_id = thread_id
        if thread_label:
            result.thread_label = thread_label
        result.store(settings.EVAL_RESULTS_DIR)
        _eval_jobs[run_id] = {"status": "done", "result": result}
    except Exception as exc:
        _eval_jobs[run_id] = {"status": "error", "error": str(exc)}


def _start_eval_job(
    entries: list[DatasetEntry],
    dataset_name: str,
    metric_names: list[str] | None,
    file_filter: str | None,
    rag_engine: RAGEngine,
    thread_id: str | None = None,
    thread_label: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:12]
    _eval_jobs[run_id] = {"status": "starting", "current": 0, "total": len(entries)}
    asyncio.create_task(
        _run_eval_background(
            run_id=run_id,
            entries=entries,
            dataset_name=dataset_name,
            metric_names=metric_names,
            file_filter=file_filter,
            rag_engine=rag_engine,
            thread_id=thread_id,
            thread_label=thread_label,
        )
    )
    return {"run_id": run_id, "status": "starting", "total": len(entries)}


@router.post("/run")
async def run_evaluation(
    dataset_name: str | None = None,
    file_filter: str | None = None,
    metric_names: str | None = None,
    from_huggingface: str | None = None,
    max_samples: int = 100,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    metrics_list = metric_names.split(",") if metric_names else None

    if from_huggingface:
        entries = DatasetLoader.from_huggingface(
            dataset_name=from_huggingface, max_samples=max_samples
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide from_huggingface dataset name or upload a JSON file.",
        )

    dataset_label = dataset_name or from_huggingface or "custom"
    return _start_eval_job(
        entries, dataset_label, metrics_list, file_filter, rag_engine
    )


@router.get("/progress/{run_id}")
async def eval_progress(run_id: str):
    job = _eval_jobs.get(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Run ID not found")

    if job["status"] == "done":
        result: EvalResult = job["result"]
        return result.model_dump()

    if job["status"] == "error":
        return {"status": "error", "error": job["error"]}

    return {
        "status": "running",
        "current": job.get("current", 0),
        "total": job.get("total", 0),
    }


@router.post("/run/file")
async def run_evaluation_from_file(
    file: UploadFile = File(...),
    file_filter: str | None = None,
    metric_names: str | None = None,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    content = await file.read()
    data = json.loads(content)

    entries = [
        DatasetEntry(
            query=item.get("question", item.get("query", "")),
            ground_truth=item.get("answer", item.get("ground_truth")),
            contexts=item.get("contexts"),
        )
        for item in data
    ]

    metrics_list = metric_names.split(",") if metric_names else None
    dataset_label = file.filename or "uploaded"
    return _start_eval_job(
        entries, dataset_label, metrics_list, file_filter, rag_engine
    )


@router.post("/run/thread/{thread_id}")
async def run_evaluation_from_thread(
    thread_id: str,
    request: Request,
    file_filter: str | None = None,
    metric_names: str | None = None,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    tenant_id = getattr(request.state, "tenant_id", "default")
    try:
        thread = await get_thread(tenant_id, thread_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Thread not found") from exc

    entries = []
    for i in range(0, len(thread.messages) - 1, 2):
        user_msg = thread.messages[i]
        asst_msg = thread.messages[i + 1] if i + 1 < len(thread.messages) else None
        if user_msg.role == "user" and asst_msg and asst_msg.role == "assistant":
            entries.append(
                DatasetEntry(query=user_msg.content, ground_truth=asst_msg.content)
            )

    if not entries:
        raise HTTPException(
            status_code=400,
            detail="Thread has no Q&A pairs to evaluate. Ask at least one question in the thread.",
        )

    first = thread.messages[0].content[:60] + (
        "..." if len(thread.messages[0].content) > 60 else ""
    )
    thread_label = (
        f'"{first}" — {len(entries)} pairs' if first else f"{len(entries)} pairs"
    )
    dataset_label = f"Thread: {thread_label}"

    metrics_list = metric_names.split(",") if metric_names else None
    return _start_eval_job(
        entries,
        dataset_label,
        metrics_list,
        file_filter,
        rag_engine,
        thread_id=thread_id,
        thread_label=thread_label,
    )


@router.get("/results")
async def list_results():
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "dataset_name": r.dataset_name,
            "num_samples": r.num_samples,
            "aggregated_scores": r.aggregated_scores,
            "thread_label": r.thread_label,
        }
        for r in results
    ]


@router.get("/results/{result_id}")
async def get_result(result_id: str):
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    for r in results:
        if r.id == result_id:
            return r.model_dump()
    raise HTTPException(status_code=404, detail="Result not found")


@router.delete("/results/{result_id}")
async def delete_result(result_id: str):
    result_path = None
    for fname in os.listdir(settings.EVAL_RESULTS_DIR):
        if fname.startswith(f"eval_{result_id}_") and fname.endswith(".json"):
            result_path = os.path.join(settings.EVAL_RESULTS_DIR, fname)
            break
    if result_path is None:
        raise HTTPException(status_code=404, detail="Result not found")
    os.remove(result_path)
    return {"status": "deleted", "id": result_id}


@router.post("/compare")
async def compare_results(id_a: str, id_b: str):
    try:
        comparison = EvalResult.compare(id_a, id_b, settings.EVAL_RESULTS_DIR)
        return {"id_a": id_a, "id_b": id_b, "comparison": comparison}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/metrics")
async def list_metrics():
    from app.evaluation.metrics import list_available_metrics

    return {"metrics": list_available_metrics()}
