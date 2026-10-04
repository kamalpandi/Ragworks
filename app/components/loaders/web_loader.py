import asyncio
import random
import re
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup, Tag

from app.models.web_loader import ScrapeResult
from app.observability.logger import get_logger

logger = get_logger(__name__)

# ── Rotate through realistic browser fingerprints ──────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# Tags that are never useful content
JUNK_TAGS = [
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "button",
    "svg",
    "img",
    "iframe",
    "ads",
    "advertisement",
    "cookie-banner",
    "popup",
]

# ── robots.txt cache (per-domain, per-session) ─────────────────────────────────
_robots_cache: dict[str, RobotFileParser] = {}


def _build_headers(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # "Accept-Encoding" removed — let httpx manage this transparently
        "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def _is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """Check robots.txt. Returns True (allow) if robots.txt is unreachable."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        try:
            rp.read()
        except Exception:
            return True  # Assume allowed if we can't fetch robots.txt
        _robots_cache[base] = rp
    return _robots_cache[base].can_fetch(user_agent, url)


def _extract_main_content(soup: BeautifulSoup) -> Tag:
    """
    Prioritise semantic content containers before falling back to <body>.
    Tries: <main>, <article>, role="main", common CMS div IDs.
    """
    # Priority order for content discovery
    candidates = [
        soup.find("main"),
        soup.find("article"),
        soup.find(attrs={"role": "main"}),
        soup.find(id=re.compile(r"(content|main|article|post|body)", re.IGNORECASE)),
        soup.find(
            class_=re.compile(r"(content|main|article|post|body)", re.IGNORECASE)
        ),
        soup.body,
    ]
    result = next((c for c in candidates if c), soup)
    if result is None:
        return soup
    return result


def _clean_text(raw: str) -> str:
    """Collapse whitespace, remove zero-width chars, deduplicate blank lines."""
    # Strip NUL bytes — PostgreSQL text fields reject \x00 entirely
    raw = raw.replace("\x00", "")
    # Strip zero-width / invisible unicode characters
    raw = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0]", " ", raw)
    # Collapse runs of spaces / tabs within a line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
    # Remove duplicate consecutive blank lines
    cleaned, prev_blank = [], False
    for line in lines:
        is_blank = line == ""
        if not (is_blank and prev_blank):
            cleaned.append(line)
        prev_blank = is_blank
    return "\n".join(cleaned).strip()


def _extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    """Pull title, description, OG tags — useful context for downstream consumers."""
    meta = {}
    if soup.title:
        meta["title"] = soup.title.get_text(strip=True)
    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property") or ""
        content = tag.get("content", "")
        if not isinstance(name, str) or not isinstance(content, str):
            continue
        if name in ("description", "og:description", "og:title", "og:type"):
            meta[name.replace("og:", "")] = content
    return meta


async def parse_url(
    url: str,
    *,
    timeout: float = 20.0,
    max_retries: int = 3,
    retry_delay: float = 1.5,
    respect_robots: bool = True,
    proxy: str | None = None,
    cookies: dict | None = None,
    junk_tags: list[str] = JUNK_TAGS,
) -> ScrapeResult:
    empty = ScrapeResult(text="", url=url)

    if respect_robots and not _is_allowed_by_robots(url):
        logger.info("robots_blocked", url=url)
        return empty

    client_kwargs: dict = {
        "timeout": httpx.Timeout(timeout),
        "follow_redirects": True,
        "headers": _build_headers(url),
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    if cookies:
        client_kwargs["cookies"] = cookies

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.get(url)
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            encoding = response.encoding or "utf-8"

            if not any(t in content_type for t in ("html", "xml", "text")):
                logger.info("non_text_content_type", url=url, content_type=content_type)
                return empty

            soup = BeautifulSoup(response.text, "html.parser", from_encoding=encoding)

            for tag in soup(junk_tags):
                tag.decompose()

            content_node = _extract_main_content(soup)
            clean = _clean_text(content_node.get_text(separator="\n"))

            return ScrapeResult(
                text=clean,
                meta=_extract_metadata(soup),
                url=str(response.url),
            )

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status != 429 and 400 <= status < 500:
                logger.warning("client_error_no_retry", url=url, status=status)
                break
            last_error = e
            logger.warning(
                "retry_attempt",
                url=url,
                attempt=attempt,
                max_retries=max_retries,
                status=status,
            )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            logger.warning(
                "network_retry",
                url=url,
                attempt=attempt,
                max_retries=max_retries,
                error=str(e),
            )

        except Exception as e:
            last_error = e
            logger.error("unexpected_scrape_error", url=url, error=str(e))
            break

        if attempt < max_retries:
            delay = retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)

    logger.warning("scrape_gave_up", url=url, last_error=str(last_error))
    return empty
