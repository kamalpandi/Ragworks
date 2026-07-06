from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.evaluation.models import EvalResult
from app.evaluation.metrics import list_available_metrics
from app.ui import templates

router = APIRouter()


@router.get("/eval", response_class=HTMLResponse)
def eval_page(request: Request):
    metrics = list_available_metrics()
    results = EvalResult.list_results(settings.EVAL_RESULTS_DIR)
    results_data = [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "dataset_name": r.dataset_name,
            "num_samples": r.num_samples,
            "aggregated_scores": r.aggregated_scores,
        }
        for r in results
    ]
    return templates.TemplateResponse(
        request=request,
        name="pages/eval.html",
        context={"metrics": metrics, "results": results_data},
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
        }
        for r in results
    ]
    return templates.TemplateResponse(
        request=request,
        name="partials/eval_results.html",
        context={"results": results_data},
    )
