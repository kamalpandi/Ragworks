from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.evaluation.models import EvalResult
from app.evaluation.metrics import list_available_metrics
from app.services.conversation_service import list_threads
from app.ui import templates

router = APIRouter()


@router.get("/eval", response_class=HTMLResponse)
async def eval_page(request: Request):
    metrics = list_available_metrics()
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    results_data = [
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
    tenant_id = getattr(request.state, "tenant_id", "default")
    threads = await list_threads(tenant_id)
    return templates.TemplateResponse(
        request=request,
        name="pages/eval.html",
        context={"metrics": metrics, "results": results_data, "threads": threads},
    )


@router.get("/ui/eval/results", response_class=HTMLResponse)
def htmx_eval_results(request: Request):
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    results_data = [
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
    return templates.TemplateResponse(
        request=request,
        name="partials/eval_results.html",
        context={"results": results_data},
    )


@router.get("/ui/eval/compare", response_class=HTMLResponse)
def htmx_compare_form(request: Request, id_a: str = "", id_b: str = ""):
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    results_data = [
        {"id": r.id, "dataset_name": r.dataset_name, "timestamp": r.timestamp}
        for r in results
    ]

    comparison = None
    if id_a and id_b:
        try:
            comparison = EvalResult.compare(id_a, id_b, settings.EVAL_RESULTS_DIR)
        except ValueError:
            pass

    return templates.TemplateResponse(
        request=request,
        name="partials/eval_compare.html",
        context={
            "results": results_data,
            "id_a": id_a,
            "id_b": id_b,
            "comparison": comparison,
        },
    )
