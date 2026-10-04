"""Evaluation views owned by the frontend.

The backend eval API is JSON-only (D9); the run/progress HTML that used to
live in the backend is reconstructed here. The progress fragment self-replaces
on ``hx-trigger="every 2s"`` and, once it renders ``done``/``error``, drops the
trigger so polling halts. Completion emits ``HX-Trigger: evalDone`` so the
results and compare fragments refresh.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.frontend import templates
from app.frontend.deps import (
    get_backend_client,
    require_session,
    verify_session_csrf,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _detail(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, dict):
        return detail.get("message") or str(detail)
    if isinstance(detail, str) and detail:
        return detail
    return "The server could not complete the request."


def _eval_error(request: Request, resp: httpx.Response):
    logger.warning("eval_failed status=%s body=%s", resp.status_code, resp.text[:200])
    return templates.TemplateResponse(
        request=request,
        name="partials/error_banner.html",
        context={"title": "Evaluation failed:", "message": _detail(resp)},
        headers={"HX-Retarget": "#eval-error", "HX-Reswap": "innerHTML"},
    )


def _progress(request: Request, run_id: str, status: str, **extra):
    headers = {"HX-Trigger": "evalDone"} if status == "done" else None
    return templates.TemplateResponse(
        request=request,
        name="partials/eval_progress.html",
        context={"run_id": run_id, "status": status, **extra},
        headers=headers,
    )


@router.post("/ui/eval/run", response_class=HTMLResponse)
async def ui_eval_run(
    request: Request,
    from_huggingface: str | None = Form(None),
    dataset_name: str | None = Form(None),
    file_filter: str | None = Form(None),
    metric_names: str | None = Form(None),
    max_samples: int = Form(100),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)

    params = {
        "from_huggingface": from_huggingface,
        "dataset_name": dataset_name,
        "file_filter": file_filter,
        "metric_names": metric_names,
        "max_samples": max_samples,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}

    resp = await get_backend_client(request).post(
        "/api/v1/eval/run", params=params, api_key=session.api_key
    )
    if resp.status_code >= 400:
        return _eval_error(request, resp)

    data = resp.json()
    return _progress(
        request,
        run_id=data["run_id"],
        status="running",
        current=0,
        total=data.get("total", 0),
    )


@router.post("/ui/eval/run/file", response_class=HTMLResponse)
async def ui_eval_run_file(
    request: Request,
    file: UploadFile = File(...),
    file_filter: str | None = Form(None),
    metric_names: str | None = Form(None),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)
    if not file.filename:
        return templates.TemplateResponse(
            request=request,
            name="partials/error_banner.html",
            context={"title": "Evaluation failed:", "message": "Missing dataset file."},
            headers={"HX-Retarget": "#eval-error", "HX-Reswap": "innerHTML"},
        )

    data = await file.read()
    params = {
        k: v
        for k, v in {"file_filter": file_filter, "metric_names": metric_names}.items()
        if v
    }
    resp = await get_backend_client(request).post(
        "/api/v1/eval/run/file",
        params=params,
        files={"file": (file.filename, data, file.content_type or "application/json")},
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        return _eval_error(request, resp)

    payload = resp.json()
    return _progress(
        request,
        run_id=payload["run_id"],
        status="running",
        current=0,
        total=payload.get("total", 0),
    )


@router.post("/ui/eval/run/thread/{thread_id}", response_class=HTMLResponse)
async def ui_eval_run_thread(
    request: Request,
    thread_id: str,
    file_filter: str | None = Form(None),
    metric_names: str | None = Form(None),
    session=Depends(require_session),
):
    verify_session_csrf(request, session)
    params = {
        k: v
        for k, v in {"file_filter": file_filter, "metric_names": metric_names}.items()
        if v
    }
    resp = await get_backend_client(request).post(
        f"/api/v1/eval/run/thread/{thread_id}",
        params=params,
        api_key=session.api_key,
    )
    if resp.status_code >= 400:
        return _eval_error(request, resp)

    payload = resp.json()
    return _progress(
        request,
        run_id=payload["run_id"],
        status="running",
        current=0,
        total=payload.get("total", 0),
    )


@router.get("/ui/eval/progress/{run_id}", response_class=HTMLResponse)
async def ui_eval_progress(
    request: Request, run_id: str, session=Depends(require_session)
):
    resp = await get_backend_client(request).get(
        f"/api/v1/eval/progress/{run_id}", api_key=session.api_key
    )
    if resp.status_code >= 400:
        # Render into the polling element itself so its trigger is replaced and
        # the poll halts; do not retarget (that would leave the poll running).
        logger.warning("eval_progress_failed status=%s", resp.status_code)
        return _progress(request, run_id=run_id, status="error", error=_detail(resp))

    data = resp.json()
    status = data.get("status")
    if status == "error":
        return _progress(
            request, run_id=run_id, status="error", error=data.get("error")
        )
    if status == "running":
        return _progress(
            request,
            run_id=run_id,
            status="running",
            current=data.get("current", 0),
            total=data.get("total", 0),
        )
    # No status field means the raw EvalResult: the run is done.
    return _progress(
        request,
        run_id=run_id,
        status="done",
        num_samples=data.get("num_samples", 0),
        aggregated_scores=data.get("aggregated_scores", {}),
    )


async def _results_response(request: Request, session, client):
    resp = await client.get("/api/v1/eval/results", api_key=session.api_key)
    if resp.status_code >= 400:
        logger.warning("eval_results_failed status=%s", resp.status_code)
        return templates.TemplateResponse(
            request=request,
            name="partials/error_banner.html",
            context={
                "title": "Could not load results:",
                "message": _detail(resp),
            },
        )
    return templates.TemplateResponse(
        request=request,
        name="partials/eval_results.html",
        context={"results": resp.json()},
    )


@router.get("/ui/eval/results", response_class=HTMLResponse)
async def ui_eval_results(request: Request, session=Depends(require_session)):
    return await _results_response(request, session, get_backend_client(request))


@router.delete("/ui/eval/results/{result_id}", response_class=HTMLResponse)
async def ui_eval_delete_result(
    request: Request, result_id: str, session=Depends(require_session)
):
    verify_session_csrf(request, session)
    client = get_backend_client(request)
    resp = await client.delete(
        f"/api/v1/eval/results/{result_id}", api_key=session.api_key
    )
    if resp.status_code >= 400:
        return _eval_error(request, resp)
    return await _results_response(request, session, client)


@router.get("/ui/eval/compare", response_class=HTMLResponse)
async def ui_eval_compare(
    request: Request,
    id_a: str = "",
    id_b: str = "",
    session=Depends(require_session),
):
    client = get_backend_client(request)
    resp = await client.get("/api/v1/eval/results", api_key=session.api_key)
    if resp.status_code >= 400:
        logger.warning("eval_compare_list_failed status=%s", resp.status_code)
        return templates.TemplateResponse(
            request=request,
            name="partials/error_banner.html",
            context={"title": "Could not load results:", "message": _detail(resp)},
        )
    results = resp.json()

    comparison = None
    if id_a and id_b:
        cmp_resp = await client.post(
            "/api/v1/eval/compare",
            params={"id_a": id_a, "id_b": id_b},
            api_key=session.api_key,
        )
        if cmp_resp.status_code < 400:
            comparison = cmp_resp.json().get("comparison")

    return templates.TemplateResponse(
        request=request,
        name="partials/eval_compare.html",
        context={
            "results": results,
            "id_a": id_a,
            "id_b": id_b,
            "comparison": comparison,
        },
    )
