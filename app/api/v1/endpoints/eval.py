import asyncio
import json
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.dependencies import get_rag_engine
from app.evaluation.dataset import DatasetEntry, DatasetLoader
from app.evaluation.models import EvalResult
from app.services.rag_engine import RAGEngine

router = APIRouter()

_eval_jobs: dict[str, dict] = {}


def _render_result_card(result: EvalResult) -> str:
    from jinja2 import Environment, BaseLoader

    env = Environment(loader=BaseLoader())
    template = env.from_string("""\
<article id="eval-run-result">
  <header>
    <strong>{{ dataset_name }}</strong>
    <small style="margin-left: 1rem;">{{ num_samples }} samples</small>
    <small style="color: var(--pico-muted-color); margin-left: 0.5rem;">{{ config.llm_model }} / {{ config.chunking_strategy }}</small>
  </header>
  <table>
    <thead><tr><th>Metric</th><th>Score</th></tr></thead>
    <tbody>
    {% for m in metrics %}
      <tr>
        <td>{{ m.name.replace('_', ' ') | title }}</td>
        <td>
          <strong>{{ "%.4f"|format(m.value) }}</strong>
          <progress value="{{ m.value }}" max="1" style="width: 100px; margin-left: 0.5rem;"></progress>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</article>
""")
    return template.render(
        dataset_name=result.dataset_name,
        num_samples=result.num_samples,
        metrics=result.metrics,
        config=result.config_snapshot,
    )


async def _run_eval_background(
    run_id: str,
    entries: list[DatasetEntry],
    dataset_name: str,
    metric_names: Optional[list[str]],
    file_filter: Optional[str],
    rag_engine: RAGEngine,
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
        _eval_jobs[run_id] = {
            "status": "done",
            "result": result,
        }
    except Exception as exc:
        _eval_jobs[run_id] = {
            "status": "error",
            "error": str(exc),
        }


@router.post("/run")
async def run_evaluation(
    request: Request,
    dataset_name: Optional[str] = None,
    file_filter: Optional[str] = None,
    metric_names: Optional[str] = None,
    from_huggingface: Optional[str] = None,
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

    if request.headers.get("HX-Request"):
        run_id = uuid.uuid4().hex[:12]
        _eval_jobs[run_id] = {"status": "starting", "current": 0, "total": len(entries)}
        asyncio.create_task(
            _run_eval_background(
                run_id=run_id,
                entries=entries,
                dataset_name=dataset_label,
                metric_names=metrics_list,
                file_filter=file_filter,
                rag_engine=rag_engine,
            )
        )
        from jinja2 import Environment, BaseLoader

        env = Environment(loader=BaseLoader())
        tmpl = env.from_string("""\
<div id="eval-run-area" hx-get="/api/v1/eval/progress/{{ run_id }}" hx-trigger="every 2s" hx-swap="outerHTML">
  <article>
    <header>Running Evaluation</header>
    <p>{{ dataset_name }} — {{ total }} samples</p>
    <progress id="eval-bar" value="0" max="{{ total }}" style="width: 100%;"></progress>
    <p id="eval-progress-text"><small>Starting...</small></p>
  </article>
</div>
""")
        return HTMLResponse(
            tmpl.render(run_id=run_id, dataset_name=dataset_label, total=len(entries))
        )

    from app.evaluation.runner import EvaluationRunner

    runner = EvaluationRunner(rag_engine=rag_engine, metric_names=metrics_list)
    result = await runner.run(
        entries=entries, dataset_name=dataset_label, file_filter=file_filter
    )
    return result.model_dump()


@router.get("/progress/{run_id}")
async def eval_progress(request: Request, run_id: str):
    job = _eval_jobs.get(run_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Run ID not found")

    if job["status"] == "done":
        result: EvalResult = job["result"]
        card_html = _render_result_card(result)
        if request.headers.get("HX-Request"):
            return HTMLResponse(card_html)
        return result.model_dump()

    if job["status"] == "error":
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                f'<article id="eval-run-area"><p style="color: var(--pico-del-color);">Error: {job["error"]}</p></article>'
            )
        return {"status": "error", "error": job["error"]}

    current = job.get("current", 0)
    total = job.get("total", 0)
    if request.headers.get("HX-Request"):
        from jinja2 import Environment, BaseLoader

        env = Environment(loader=BaseLoader())
        tmpl = env.from_string("""\
<div id="eval-run-area" hx-get="/api/v1/eval/progress/{{ run_id }}" hx-trigger="every 2s" hx-swap="outerHTML">
  <article>
    <header>Running Evaluation</header>
    <progress value="{{ current }}" max="{{ total }}" style="width: 100%;"></progress>
    <p><small>{{ current }}/{{ total }} samples completed</small></p>
  </article>
</div>
""")
        return HTMLResponse(tmpl.render(run_id=run_id, current=current, total=total))
    return {"status": "running", "current": current, "total": total}


@router.post("/run/file")
async def run_evaluation_from_file(
    request: Request,
    file: UploadFile = File(...),
    file_filter: Optional[str] = None,
    metric_names: Optional[str] = None,
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
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

    metrics_list = metric_names.split(",") if metric_names else None
    dataset_label = file.filename or "uploaded"

    if request.headers.get("HX-Request"):
        run_id = uuid.uuid4().hex[:12]
        _eval_jobs[run_id] = {"status": "starting", "current": 0, "total": len(entries)}
        asyncio.create_task(
            _run_eval_background(
                run_id=run_id,
                entries=entries,
                dataset_name=dataset_label,
                metric_names=metrics_list,
                file_filter=file_filter,
                rag_engine=rag_engine,
            )
        )
        from jinja2 import Environment, BaseLoader

        env = Environment(loader=BaseLoader())
        tmpl = env.from_string("""\
<div id="eval-run-area" hx-get="/api/v1/eval/progress/{{ run_id }}" hx-trigger="every 2s" hx-swap="outerHTML">
  <article>
    <header>Running Evaluation</header>
    <p>{{ dataset_name }} — {{ total }} samples</p>
    <progress value="0" max="{{ total }}" style="width: 100%;"></progress>
    <p><small>Starting...</small></p>
  </article>
</div>
""")
        return HTMLResponse(
            tmpl.render(run_id=run_id, dataset_name=dataset_label, total=len(entries))
        )

    from app.evaluation.runner import EvaluationRunner

    runner = EvaluationRunner(rag_engine=rag_engine, metric_names=metrics_list)
    result = await runner.run(
        entries=entries, dataset_name=dataset_label, file_filter=file_filter
    )
    return result.model_dump()


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


@router.get("/results/{result_id}/card", response_class=HTMLResponse)
async def get_result_card(result_id: str):
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    for r in results:
        if r.id == result_id:
            return HTMLResponse(_render_result_card(r))
    raise HTTPException(status_code=404, detail="Result not found")


@router.post("/compare")
async def compare_results(id_a: str, id_b: str):
    try:
        comparison = EvalResult.compare(id_a, id_b, settings.EVAL_RESULTS_DIR)
        return {"id_a": id_a, "id_b": id_b, "comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metrics")
async def list_metrics():
    from app.evaluation.metrics import list_available_metrics

    return {"metrics": list_available_metrics()}
