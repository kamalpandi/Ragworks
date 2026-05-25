import re
from urllib.parse import urlparse

from app.components.query_translation.base import BaseQueryTranslator

# ── Intent detection ───────────────────────────────────────────────────────────
INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"\b(summarize|summary|overview|tldr|tl;dr|recap)\b", re.I),
        "summarize",
    ),
    (
        re.compile(r"\b(explain|what is|what are|describe|clarify|elaborate)\b", re.I),
        "explain",
    ),
    (re.compile(r"\b(list|enumerate|what are the|give me all)\b", re.I), "list"),
    (re.compile(r"\b(compare|difference|vs|versus|contrast)\b", re.I), "compare"),
    (re.compile(r"\b(how|steps|process|guide|tutorial|implement)\b", re.I), "howto"),
    (re.compile(r"\b(why|reason|cause|motivation|purpose)\b", re.I), "why"),
    (re.compile(r"\b(find|search|look for|locate|show me)\b", re.I), "find"),
]

INTENT_PREFIXES: dict[str, str] = {
    "summarize": "Provide a comprehensive summary of the main points, arguments, and conclusions in",
    "explain": "Explain the key concepts, definitions, and technical details discussed in",
    "list": "List all the key items, features, points, or examples mentioned in",
    "compare": "Identify and compare the different approaches, options, or viewpoints presented in",
    "howto": "Describe the steps, process, and implementation details covered in",
    "why": "Explain the reasoning, motivations, and justifications presented in",
    "find": "Find and extract the specific information requested from",
    "default": "Answer the question using content from",
}

_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "is",
    "it",
    "its",
}

_PLACEHOLDER_RE = re.compile(
    r"\b(this|it|that|the article|the document|the file|the page|the content|above|same)\b",
    re.I,
)


def _extract_topic(file_name: str) -> str:
    parsed = urlparse(file_name)
    if parsed.scheme in ("http", "https"):
        segments = [s for s in parsed.path.split("/") if s]
        raw = segments[-1] if segments else parsed.netloc
    else:
        raw = file_name.rsplit(".", 1)[0]

    words = re.split(r"[-_\s]+", raw)
    meaningful = [
        w.upper() if re.match(r"^[a-z]{1,3}\d+$", w, re.I) else w.title()
        for w in words
        if w.lower() not in _STOPWORDS and len(w) > 1
    ]
    return " ".join(meaningful) if meaningful else file_name


def _detect_intent(message: str) -> str:
    for pattern, intent in INTENT_PATTERNS:
        if pattern.search(message):
            return intent
    return "default"


def _is_vague(message: str) -> bool:
    lower = message.lower().strip()
    return len(lower.split()) <= 6 or bool(_PLACEHOLDER_RE.search(lower))


def enrich_query(message: str, file_name: str | None) -> str:
    """
    Public interface — only this function is imported elsewhere.
    Rewrites vague queries into retrieval-friendly ones using intent + topic context.
    """
    if not file_name:
        return message

    topic = _extract_topic(file_name)
    intent = _detect_intent(message)
    prefix = INTENT_PREFIXES[intent]

    if _is_vague(message):
        return f"{prefix} {topic}. User's request: '{message}'. Source: {file_name}"
    return f"{message} (from: {topic}) Source: {file_name}"


class QueryEnricher(BaseQueryTranslator):
    """
    Pre-retrieval query enrichment.
    Rewrites vague queries into retrieval-friendly ones using
    intent detection + topic extraction from the source file/URL.

    Sits at the start of the translation pipeline — runs before
    multi_query, hyde, or decomposition strategies.
    """

    async def translate(self, query: str) -> list[str]:
        # file_name isn't available here — enrichment happens at the router level
        # translate() just returns the query as-is wrapped in a list
        return [query]
