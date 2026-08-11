from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.prompt_loader import (
    delete_prompt,
    get_available_prompts,
    load_prompt,
    save_prompt,
)

router = APIRouter()


class PromptSaveRequest(BaseModel):
    category: str = Field(..., description="'system' or 'user'")
    content: str = Field(..., description="Markdown content of the prompt")


@router.get("", summary="List all discoverable system and user prompts")
async def list_prompts():
    return {
        "system_prompts": get_available_prompts("system"),
        "user_prompts": get_available_prompts("user"),
    }


@router.get("/{name}", summary="Get a single prompt with its content")
async def get_prompt(name: str, category: str = "system"):
    content = load_prompt(name, category)
    if not content:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return {"name": name, "category": category, "content": content}


@router.put("/{name}", summary="Create or update a prompt")
async def upsert_prompt(name: str, body: PromptSaveRequest):
    if name == "default" and body.category == "system":
        raise HTTPException(
            status_code=403, detail="Cannot overwrite the default system prompt"
        )
    save_prompt(name, body.content, body.category)
    return {"name": name, "category": body.category, "status": "saved"}


@router.delete("/{name}", summary="Delete a prompt")
async def remove_prompt(name: str, category: str = "system"):
    if name == "default" and category == "system":
        raise HTTPException(
            status_code=403, detail="Cannot delete the default system prompt"
        )
    deleted = delete_prompt(name, category)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return {"name": name, "category": category, "status": "deleted"}
