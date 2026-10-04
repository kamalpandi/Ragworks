from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.components.loaders.pdf_loader import parse_pdf
from app.core.dependencies import get_ingestion_service

router = APIRouter()


# --- HTMX Form Handlers ---
@router.post("/ui/ingest/file", response_class=HTMLResponse)
async def ui_ingest_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service=Depends(get_ingestion_service),
):
    if not file.filename:
        return "<span style='color: var(--pico-del-color);'>Missing filename.</span>"

    text = ""
    if file.filename.endswith(".pdf"):
        text = await parse_pdf(file)
    elif file.filename.endswith(".txt"):
        content = await file.read()
        text = content.decode("utf-8")
    else:
        return (
            "<span style='color: var(--pico-del-color);'>Unsupported file type.</span>"
        )

    tenant_id = getattr(request.state, "tenant_id", "default")

    background_tasks.add_task(
        service.ingest_texts,
        texts=[text],
        source_name=file.filename,
        tenant_id=tenant_id,
    )
    return f"<span style='color: var(--pico-ins-color);'>'{file.filename}' queued for background processing!</span>"
