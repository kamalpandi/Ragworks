from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.evaluation.models import EvalResult
from app.ui import templates

router = APIRouter()


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
