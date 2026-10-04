"""Render-only frontend package.

Owns pages, fragments, templates, and static assets. Reaches the backend
exclusively through ``app.frontend.api_client``.
"""

from fastapi.templating import Jinja2Templates

from app.core.csrf import csrf_context

templates = Jinja2Templates(
    directory="app/frontend/templates", context_processors=[csrf_context]
)
