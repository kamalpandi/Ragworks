from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.components.loaders.pdf_loader import parse_pdf
from app.components.loaders.web_loader import parse_url
from app.core.dependencies import get_ingestion_service, get_vector_db
from app.models.api_requests import IngestRequest, UrlIngestRequest
from app.models.api_response import IngestResponse

router = APIRouter()


@router.post("/file", response_model=IngestResponse, summary="Ingest a PDF or TXT file")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service=Depends(get_ingestion_service),
):
    """
    Upload a PDF or TXT file to ingest.
    The processing happens asynchronously in the background.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing from the uploaded folder",
        )

    text = ""

    if file.filename.endswith(".pdf"):
        text = await parse_pdf(file)
    elif file.filename.endswith(".txt"):
        content = await file.read()
        text = content.decode("utf-8")
    else:
        return {"error": "Unsupported file type. Use .pdf or .txt"}

    background_tasks.add_task(
        service.ingest_texts,
        texts=[text],
        source_name=file.filename,
    )

    return IngestResponse(
        filename=file.filename,
        status="Ingestion started in background",
    )


@router.post("/url", response_model=IngestResponse, summary="Ingest content from a URL")
async def ingest_url(
    background_tasks: BackgroundTasks,
    request: UrlIngestRequest,
    service=Depends(get_ingestion_service),
):
    result = await parse_url(request.url, respect_robots=False)

    if not result.text:
        raise HTTPException(status_code=400, detail="Could not extract text from URL")

    background_tasks.add_task(
        service.ingest_texts,
        texts=[result.text],
        source_name=request.url,
    )

    return IngestResponse(
        url=result.url or request.url,
        filename=request.url,
        status="Processing started in background",
        count=None,
    )


@router.post(
    "/custom", response_model=IngestResponse, summary="Ingest custom text strings"
)
async def ingest_custom_text(
    request: IngestRequest, service=Depends(get_ingestion_service)
):
    """Ingest any list of strings directly as JSON."""
    await service.ingest_texts(request.texts, source_name="manual_upload")
    return IngestResponse(status="success", count=len(request.texts))


@router.get("/files", summary="List all ingested document source names")
async def list_ingested_files(vector_db=Depends(get_vector_db)):
    sources = await vector_db.get_distinct_sources()
    return {"sources": sources, "count": len(sources)}
