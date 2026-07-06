from fastapi import APIRouter, Request

from app.services.conversation_service import get_thread, list_threads

router = APIRouter()


@router.get("/{thread_id}", summary="Get conversation thread history")
async def get_conversation(thread_id: str, request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default")
    thread = await get_thread(tenant_id, thread_id)
    if not thread.messages:
        return {"thread_id": thread_id, "messages": []}
    return {
        "thread_id": thread.thread_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in thread.messages
        ],
    }


@router.get("", summary="List conversation threads for tenant")
async def list_conversation_threads(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default")
    thread_ids = await list_threads(tenant_id)
    return {"threads": thread_ids, "count": len(thread_ids)}
