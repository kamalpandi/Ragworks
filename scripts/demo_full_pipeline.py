"""
demo_full_pipeline.py
─────────────────────────────────────────────────────────────────────────────
End-to-end demo that exercises ALL four routes in one narrative:

  /ingest/custom  ──── seed a company policy knowledge base
  /ingest/url     ──── pull OSHA guidelines from the web
  /ingest/file    ──── upload an internal safety PDF (if present)
  /query          ──── a safety officer asks compliance questions using
                       different translation strategies

Run this as a single script to verify the whole RAG stack works together.
─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import os
import time
from typing import TypedDict

import httpx

BASE_URL = "http://localhost:8000/api/v1"
QUERY_EP = f"{BASE_URL}/query"
INGEST_CUSTOM_EP = f"{BASE_URL}/ingest/custom"
INGEST_URL_EP = f"{BASE_URL}/ingest/url"
INGEST_FILE_EP = f"{BASE_URL}/ingest/file"

# ── (optional) drop a real PDF here to test the file route ──────────────────
SAFETY_PDF_PATH = "workplace_safety_policy.pdf"

# ── Custom text blobs ────────────────────────────────────────────────────────
POLICY_SNIPPETS = [
    "All employees must complete safety induction training within their first week. "
    "Refresher training is mandatory every 12 months.",
    "Personal Protective Equipment (PPE) — including hard hats, high-visibility "
    "vests, and steel-toed boots — is required on all active construction sites.",
    "Incidents must be reported to the site supervisor within 1 hour of occurrence. "
    "A formal written report must be filed within 24 hours using Form HS-01.",
    "Chemical storage areas require bilingual hazard labels (English and Spanish) "
    "and must be inspected weekly. SDS binders must be kept within 10 metres of "
    "any chemical storage zone.",
    "Emergency muster points are marked with green-and-white assembly signs. "
    "All personnel must participate in at least two fire drills per calendar year.",
]

# ── External web source ──────────────────────────────────────────────────────
OSHA_URL = "https://www.osha.gov/workers/file-complaint"  # real OSHA page


# FIX 1: Create a rigid schema definitions contract for the linter
class QueryQuestion(TypedDict):
    text: str
    filter: str | None
    strategy: str | None


# FIX 2: Explicitly type-hint the list to enforce the string guarantee on "text"
QUESTIONS: list[QueryQuestion] = [
    {
        "text": "How soon after a workplace incident must a written report be filed?",
        "filter": None,
        "strategy": None,
    },
    {
        "text": "What PPE is mandatory on construction sites according to company policy?",
        "filter": None,
        "strategy": "multi_query",
    },
    {
        "text": "How does OSHA's complaint process work for workers?",
        "filter": OSHA_URL,
        "strategy": "hyde",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


async def run_ingest_custom(texts: list[str]) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(INGEST_CUSTOM_EP, json={"texts": texts})
    r.raise_for_status()
    d = r.json()
    print(f"    ✓ Custom ingest — {d['count']} snippets  [{d['status']}]")


async def run_ingest_url(url: str) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(INGEST_URL_EP, json={"url": url})
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        print(f"    ✗ URL ingest error: {d['error']}")
    else:
        print(f"    ✓ URL ingest started — {d['url']}")


async def run_ingest_file(path: str) -> str | None:
    if not os.path.exists(path):
        print(f"    ⚠  {path} not found — skipping file ingest.")
        return None
    filename = os.path.basename(path)
    mime = "application/pdf" if filename.endswith(".pdf") else "text/plain"
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(path, "rb") as fh:
            r = await client.post(INGEST_FILE_EP, files={"file": (filename, fh, mime)})
    r.raise_for_status()
    d = r.json()
    print(f"    ✓ File ingest started — {d['filename']}  [{d['status']}]")
    return filename


async def run_query(
    question: str, file_filter: str | None, strategy: str | None
) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            QUERY_EP,
            json={
                "message": question,
                "file_name": file_filter,
                "translation_strategy": strategy,
            },
        )
    r.raise_for_status()
    return r.json().get("answer", "(no answer)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("\n" + "=" * 70)
    print("  FULL PIPELINE DEMO — Workplace Safety Compliance Bot")
    print("=" * 70)

    # ── Phase 1: ingest from three different sources ─────────────────────────
    print("\n── Phase 1: Knowledge Base Ingestion ──────────────────────────────\n")

    print("  [A] Custom text (company policy snippets) …")
    await run_ingest_custom(POLICY_SNIPPETS)

    print("\n  [B] URL — OSHA worker complaint page …")
    await run_ingest_url(OSHA_URL)

    print(f"\n  [C] File — {SAFETY_PDF_PATH} …")
    await run_ingest_file(SAFETY_PDF_PATH)

    print("\n  Waiting 8 s for background ingestion tasks to finish …")
    time.sleep(8)

    # ── Phase 2: compliance Q&A ───────────────────────────────────────────────
    print("\n── Phase 2: Safety Officer Q&A Session ────────────────────────────\n")

    for i, q in enumerate(QUESTIONS, 1):
        scope = f"[filter: {q['filter']}]" if q["filter"] else "[global search]"
        strat = q["strategy"] or "default"
        print(f"  Q{i} ({strat}, {scope})")
        print(f"     {q['text']}")
        answer = await run_query(q["text"], q["filter"], q["strategy"])
        print(f"  ➜  {answer}\n")
        print("  " + "─" * 66 + "\n")

    print("[✓] Full pipeline demo complete.\n")


if __name__ == "__main__":
    asyncio.run(main())
