"""
research.py — Per-app research pipeline for the Composio product research agent.

Composio SDK strategy
---------------------
We target Composio v3 (packages: ``composio`` + ``composio-client``):
  - AsyncComposio from composio-client for native async execute()
  - Fall back to legacy ComposioToolSet (composio-core) wrapped in
    asyncio.to_thread() if composio-client is not installed.

Architecture
------------
Phase 1  Web fetch  (parallel, 4 queries)
         PRIMARY:   Composio SERP / EXA action (dogfoods the product)
         SECONDARY: Gemini built-in grounding  (independent cross-check)

         Two independent sources that both cite a claim → confidence "High".
         Only one source → "Medium".  Neither → "Low".

         NOTE: google-genai does NOT allow response_schema + google_search in
         the same request, so grounding and extraction are always separate calls.

Phase 2  Structured LLM extraction
         Default:    RESEARCH_MODEL_FLASH   (gemini-3.7-flash by default)
         Escalation: RESEARCH_MODEL_PRO     (gemini-3.1-pro)
         Escalation triggers: confidence=="Low" OR any validation contradiction
         on the first pass. The pro call re-uses the already-fetched snippets.

Phase 3  Pydantic parse → cross-field validators in schema.py auto-fire.

Retry    Exponential back-off, up to _MAX_RETRIES=3 attempts, on any
         transient error (rate-limit, network, JSON decode failure).

Known limitations
-----------------
* If COMPOSIO_API_KEY is absent or no SERP-class action is available/connected,
  the pipeline silently falls back to Gemini grounding as the sole source and
  records `composio_available=False` in the snippet bundle.  This degrades
  confidence (fewer independent sources) and is documented in README.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv()

# ── Schema import: absolute path with relative fallback ───────────────────────
# research.py may be loaded either as `src.research` (via batch.py sys.path
# injection) or as a relative package module.  Support both.
try:
    from src.schema import AppResearch, EvidenceEntry  # absolute (batch.py path)
except ModuleNotFoundError:
    from .schema import AppResearch, EvidenceEntry  # relative (package import)  # type: ignore[no-redef]

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Multi-model cascade ───────────────────────────────────────────────────────
# Models are tried in priority order; when one hits its DAILY quota limit
# (HTTP 429 with GenerateRequestsPerDayPerProjectPerModel in the body),
# it is marked exhausted for the lifetime of this process and the next model
# in the list is tried automatically.  Quality is preserved by ordering from
# best to next-best instruction-following models.
#
# Confirmed available + JSON-mode capable via probe on 2026-08-18:
#   gemini-3.7-flash    -> 20 req/day free-tier  (currently exhausted)
#   gemini-3.6-flash    -> separate quota bucket  (wraps output in markdown)
#   gemini-3.5-flash    -> separate quota bucket  (wraps output in markdown)
#   gemini-3.5-flash-lite -> OK, clean JSON
#   gemini-3.1-flash-lite -> OK, clean JSON
#
# Override the starting model via RESEARCH_MODEL_FLASH env var.
# Skip escalation entirely via RESEARCH_SKIP_ESCALATION=true.

_MODEL_FLASH_CASCADE: list[str] = [
    os.getenv("RESEARCH_MODEL_FLASH", "models/gemini-3.7-flash"),
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
    "models/gemini-3.5-flash-lite",
    "models/gemini-3.1-flash-lite",
]
# Deduplicate while preserving order (in case env var is already in the list)
_seen: set[str] = set()
_MODEL_FLASH_CASCADE = [
    m for m in _MODEL_FLASH_CASCADE
    if m not in _seen and not _seen.add(m)  # type: ignore[func-returns-value]
]

# Legacy alias — used as the first model in the cascade for grounding calls
_MODEL_FLASH: str = _MODEL_FLASH_CASCADE[0]
_MODEL_PRO: str = os.getenv("RESEARCH_MODEL_PRO", "models/gemini-3.1-pro-preview")

# -- Escalation flag --
# Set RESEARCH_SKIP_ESCALATION=true to disable pro-model re-runs.
_SKIP_ESCALATION: bool = os.getenv("RESEARCH_SKIP_ESCALATION", "").lower() in ("1", "true", "yes")

# -- Per-process daily-quota tracking: exhausted model IDs --
# Protected by an asyncio.Lock; shared across all concurrent research tasks.
_EXHAUSTED_MODELS: set[str] = set()
_EXHAUSTED_LOCK: asyncio.Lock | None = None


def _exhausted_lock() -> asyncio.Lock:
    """Lazy lock factory — safe inside a running event loop."""
    global _EXHAUSTED_LOCK
    if _EXHAUSTED_LOCK is None:
        _EXHAUSTED_LOCK = asyncio.Lock()
    return _EXHAUSTED_LOCK


def _is_daily_quota_error(exc: BaseException) -> bool:
    """True when the exception is specifically a per-day quota exhaustion."""
    msg = str(exc)
    return (
        "429" in msg
        and (
            "GenerateRequestsPerDayPerProjectPerModel" in msg
            or "per_day" in msg.lower()
            or "daily" in msg.lower()
        )
    )


async def _get_active_flash_model() -> str:
    """
    Return the highest-priority flash model that has NOT been marked exhausted.
    Raises RuntimeError if all cascade models are exhausted.
    """
    async with _exhausted_lock():
        for m in _MODEL_FLASH_CASCADE:
            if m not in _EXHAUSTED_MODELS:
                return m
    raise RuntimeError(
        "All flash models in the cascade have hit their daily quota.\n"
        f"Exhausted: {sorted(_EXHAUSTED_MODELS)}\n"
        "Wait until midnight Pacific Time for quotas to reset, or add a paid key."
    )


async def _mark_model_exhausted(model_id: str) -> None:
    """Mark a model as daily-quota-exhausted and log the cascade step."""
    async with _exhausted_lock():
        if model_id not in _EXHAUSTED_MODELS:
            _EXHAUSTED_MODELS.add(model_id)
            remaining = [m for m in _MODEL_FLASH_CASCADE if m not in _EXHAUSTED_MODELS]
            short = model_id.replace("models/", "")
            if remaining:
                nxt = remaining[0].replace("models/", "")
                logger.warning(
                    "Daily quota exhausted for %s — cascading to %s", short, nxt
                )
            else:
                logger.error(
                    "Daily quota exhausted for %s — NO more cascade models available!", short
                )


# -- Gemini API global rate limiter --
# Free tier: 5 RPM per model.  A semaphore of 1 + sequential grounding queries
# keeps us well under that.  Raise via GEMINI_API_CONCURRENCY for paid keys.
_GEMINI_API_CONCURRENCY: int = int(os.getenv("GEMINI_API_CONCURRENCY", "3"))
_GEMINI_API_SEM: asyncio.Semaphore | None = None


def _gemini_sem() -> asyncio.Semaphore:
    """Lazy semaphore factory — safe to call from inside a running event loop."""
    global _GEMINI_API_SEM
    if _GEMINI_API_SEM is None:
        _GEMINI_API_SEM = asyncio.Semaphore(_GEMINI_API_CONCURRENCY)
    return _GEMINI_API_SEM


# ── MCP registry search templates ────────────────────────────────────────────
# Search all three major MCP registries in a single SERP query
_MCP_QUERY_TMPL = (
    "{app} MCP server site:glama.ai OR site:mcp.so OR site:smithery.ai"
)

# ── Retry config ──────────────────────────────────────────────────────────────
_MAX_RETRIES: int = 3
_RETRY_BASE_SEC: float = 2.0

# ── Composio: ordered list of SERP-class action slugs to try ────────────────
# Tried in order; the first one the account has connected wins.
# NOTE: Tavily's slug is "TAVILY_TAVILY_SEARCH" (doubled), not "TAVILY_SEARCH".
_COMPOSIO_SERP_ACTIONS: list[str] = [
    "SERPAPI_SEARCH",
    "EXA_SEARCH",
    "TAVILY_TAVILY_SEARCH",
    "GOOGLESEARCH_SEARCH",
]

# ── Lazy Composio imports: v3 async preferred, v2 legacy as fallback ─────────
_COMPOSIO_SDK_PRESENT = False
_COMPOSIO_ASYNC_CLIENT = None   # composio-client AsyncComposio class
_ComposioToolSet        = None   # composio-core / composio ComposioToolSet

try:
    from composio_client import AsyncComposio as _AsyncComposio  # type: ignore
    _COMPOSIO_ASYNC_CLIENT = _AsyncComposio
    _COMPOSIO_SDK_PRESENT  = True
except ImportError:
    _AsyncComposio = None  # type: ignore

if not _COMPOSIO_SDK_PRESENT:
    # Fall back to synchronous legacy SDK
    try:
        from composio import ComposioToolSet as _ComposioToolSet  # type: ignore
        _COMPOSIO_SDK_PRESENT = True
    except ImportError:
        try:
            from composio_core import ComposioToolSet as _ComposioToolSet  # type: ignore
            _COMPOSIO_SDK_PRESENT = True
        except ImportError:
            pass

_COMPOSIO_ENABLED: bool = _COMPOSIO_SDK_PRESENT and bool(os.getenv("COMPOSIO_API_KEY"))


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SnippetBundle:
    """
    Raw text and URL evidence gathered in Phase 1 before the LLM sees it.
    Keeping Composio and Gemini results separate lets the extraction prompt
    explicitly flag cross-source agreement, which drives the confidence field.
    """

    app_name: str
    composio_snippets: list[str] = field(default_factory=list)
    composio_urls: list[str] = field(default_factory=list)
    gemini_snippets: list[str] = field(default_factory=list)
    gemini_urls: list[str] = field(default_factory=list)
    composio_available: bool = False  # False = fell back to Gemini-only

    def has_dual_source(self) -> bool:
        """True when both Composio and Gemini returned at least one snippet."""
        return self.composio_available and bool(self.composio_snippets)

    def all_snippets(self) -> list[str]:
        return self.composio_snippets + self.gemini_snippets

    def all_urls(self) -> list[str]:
        return self.composio_urls + self.gemini_urls


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class ResearchError(Exception):
    """Raised when a per-app research run fails unrecoverably."""

    REASONS = frozenset(
        {"llm_parse_failure", "validation_failure", "rate_limit", "unknown"}
    )

    def __init__(
        self,
        app_name: str,
        reason: str,
        raw_response: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        assert reason in self.REASONS, f"Unknown ResearchError reason: {reason!r}"
        self.app_name = app_name
        self.reason = reason
        self.raw_response = raw_response
        self.cause = cause
        super().__init__(f"[{app_name}] Research failed: {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# Retry decorator
# ─────────────────────────────────────────────────────────────────────────────

def _is_retryable(exc: BaseException) -> bool:
    """Heuristic: treat rate-limit / transient network errors as retryable."""
    msg = str(exc).lower()
    return any(kw in msg for kw in ("429", "503", "rate", "quota", "timeout", "connect"))


def _parse_retry_after(exc: Exception) -> float:
    """
    Extract the server-recommended retry delay from a 429 error body.
    The Gemini API embeds it as 'retryDelay: "Xs"' in the JSON details.
    Returns 0.0 if not found (caller falls back to exponential backoff).
    """
    import re
    m = re.search(r'retry[^\d]*(\d+\.?\d*)s', str(exc), re.IGNORECASE)
    return float(m.group(1)) + 1.5 if m else 0.0  # +1.5s safety buffer


async def _with_retry(coro_factory, *, app_name: str, label: str) -> Any:
    """
    Call `coro_factory()` -> awaitable up to _MAX_RETRIES times.
    Uses the server's retryDelay from 429 bodies when available;
    falls back to exponential back-off otherwise.
    """
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES:
                raise
            server_delay = _parse_retry_after(exc)
            expo_delay   = _RETRY_BASE_SEC * (2 ** (attempt - 1))
            delay        = max(server_delay, expo_delay)
            logger.warning(
                "[%s] %s attempt %d/%d failed (%s); retrying in %.1fs",
                app_name, label, attempt, _MAX_RETRIES, exc, delay,
            )
            await asyncio.sleep(delay)
    # Should not reach here, but satisfy type-checker
    raise ResearchError(app_name, "unknown", cause=last_exc)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1a — Composio SERP (primary web source)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_composio_result(raw: Any) -> tuple[list[str], list[str]]:
    """
    Extract (snippets, urls) from a Composio execute / execute_action response.
    The response shape varies by action (SerpAPI vs Exa vs Tavily); we try
    the most common key patterns in order.
    """
    snippets: list[str] = []
    urls: list[str] = []

    # v3 SDK returns a ToolExecutionResponse object; normalise to dict
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    elif hasattr(raw, "__dict__"):
        raw = raw.__dict__

    data: Any = (
        raw.get("data")
        or raw.get("response_data")
        or raw.get("output")
        or raw
    )
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            snippets.append(data[:2000])
            return snippets, urls

    # SerpAPI shape: {organic_results: [{snippet, link}, ...]}
    for item in (
        data.get("organic_results")
        or data.get("results")
        or data.get("items")
        or []
    ):
        if not isinstance(item, dict):
            continue
        snip = (
            item.get("snippet")
            or item.get("text")
            or item.get("content")
            or item.get("highlights", [""])[0]
            or ""
        )
        url = (
            item.get("link")
            or item.get("url")
            or item.get("source_url")
            or ""
        )
        if snip:
            snippets.append(str(snip)[:1000])
        if url:
            urls.append(str(url))

    # Tavily shape: {results: [{content, url}, ...]}
    if not snippets:
        for item in data.get("results") or []:
            if isinstance(item, dict):
                snip = item.get("content") or item.get("text") or ""
                url  = item.get("url") or ""
                if snip:
                    snippets.append(str(snip)[:1000])
                if url:
                    urls.append(str(url))

    return snippets, urls


async def _fetch_via_composio(
    app_name: str,
    queries: list[str],
) -> tuple[list[str], list[str]]:
    """
    Run all queries through Composio SERP in parallel.

    Strategy
    --------
    1. Prefer v3 AsyncComposio (composio-client) — native async, no threads.
    2. Fall back to legacy ComposioToolSet wrapped in asyncio.to_thread().

    We try SERP action slugs in _COMPOSIO_SERP_ACTIONS order; the first one
    that doesn't raise is used for all remaining queries.
    """
    api_key = os.getenv("COMPOSIO_API_KEY")

    # ── v3 async path ─────────────────────────────────────────────────────
    if _COMPOSIO_ASYNC_CLIENT is not None:
        async def _one_v3(q: str, slug: str, client: Any) -> tuple[list[str], list[str]]:
            result = await client.tools.execute(
                slug=slug,
                arguments={"query": q, "num_results": 5},
            )
            return _parse_composio_result(result)

        async with _COMPOSIO_ASYNC_CLIENT(api_key=api_key) as ac:
            # Find first working action slug
            working_slug = _COMPOSIO_SERP_ACTIONS[0]   # optimistic default
            for slug in _COMPOSIO_SERP_ACTIONS:
                try:
                    test = await ac.tools.execute(
                        slug=slug, arguments={"query": app_name}
                    )
                    _parse_composio_result(test)         # raises if malformed
                    working_slug = slug
                    break
                except Exception:
                    continue

            results = await asyncio.gather(
                *[_one_v3(q, working_slug, ac) for q in queries],
                return_exceptions=True,
            )

        snippets, urls = [], []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("[%s] Composio v3 search error: %s", app_name, r)
            else:
                s, u = r
                snippets.extend(s)
                urls.extend(u)
        return snippets, urls

    # ── Legacy sync path (asyncio.to_thread wrapper) ──────────────────────
    if _ComposioToolSet is not None:
        toolset = _ComposioToolSet(api_key=api_key)

        def _sync_search(q: str, action_name: str) -> dict:
            return toolset.execute_action(
                action=action_name,
                params={"query": q, "num_results": 5},
            )

        # Find working action for legacy SDK
        working_action = _COMPOSIO_SERP_ACTIONS[0]
        for act in _COMPOSIO_SERP_ACTIONS:
            try:
                raw = await asyncio.to_thread(_sync_search, app_name, act)
                _parse_composio_result(raw)
                working_action = act
                break
            except Exception:
                continue

        results = await asyncio.gather(
            *[
                asyncio.to_thread(_sync_search, q, working_action)
                for q in queries
            ],
            return_exceptions=True,
        )

        snippets, urls = [], []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("[%s] Composio legacy search error: %s", app_name, r)
            else:
                s, u = _parse_composio_result(r)
                snippets.extend(s)
                urls.extend(u)
        return snippets, urls

    raise RuntimeError("No Composio SDK available")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1b — Gemini grounding (secondary cross-check)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_via_gemini_grounding(
    app_name: str,
    queries: list[str],
    client,  # genai.Client
) -> tuple[list[str], list[str]]:
    """
    Run each query through Gemini with Google Search grounding enabled.
    Returns (text_snippets, source_urls).

    NOTE: grounding and response_schema cannot coexist in one request.
    This function is purely for raw snippet gathering (Phase 1).
    """
    from google.genai import types as _types  # local import to keep top clean

    google_search_tool = _types.Tool(google_search=_types.GoogleSearch())

    async def _one(q: str) -> tuple[str, list[str]]:
        # Use the active cascade model for grounding too
        try:
            grounding_model = await _get_active_flash_model()
        except RuntimeError:
            grounding_model = _MODEL_FLASH  # fallback if all exhausted
        async with _gemini_sem():          # global rate cap
            resp = await client.aio.models.generate_content(
                model=grounding_model,
                contents=(
                    f"Summarise what you find about the following in 3-5 sentences, "
                    f"citing facts: {q}"
                ),
                config=_types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
        text = resp.text or ""
        urls: list[str] = []
        if resp.candidates:
            meta = resp.candidates[0].grounding_metadata
            if meta and meta.grounding_chunks:
                for chunk in meta.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        urls.append(chunk.web.uri)
        return text, urls

    # !! SEQUENTIAL — not asyncio.gather — to avoid 429 burst on free-tier keys.
    # Each grounding call counts against the per-minute quota; firing 4 at once
    # for every app would exhaust a 5 RPM limit instantly.
    snippets, urls = [], []
    for q in queries:
        try:
            t, u = await _one(q)
            if t:
                snippets.append(t)
            urls.extend(u)
        except Exception as exc:
            logger.warning("[%s] Gemini grounding error: %s", app_name, exc)

    return snippets, urls


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 orchestrator — build SnippetBundle
# ─────────────────────────────────────────────────────────────────────────────

def _build_queries(app_name: str) -> list[str]:
    """Four focused search queries that cover auth, API surface, access, MCP."""
    a = app_name
    return [
        f"{a} developer API documentation",
        f"{a} API authentication OAuth API key pricing developer access self-serve",
        _MCP_QUERY_TMPL.format(app=a),
        f"site:composio.dev {a}",
    ]


async def _fetch_snippets(app_name: str, client) -> SnippetBundle:
    """
    Phase 1: parallel fetch via Composio (primary) + Gemini grounding (secondary).
    Falls back gracefully if Composio is unavailable.
    """
    queries = _build_queries(app_name)
    bundle  = SnippetBundle(app_name=app_name)

    # ── Primary: Composio SERP ─────────────────────────────────────────────
    if _COMPOSIO_ENABLED:
        try:
            c_snips, c_urls = await _fetch_via_composio(app_name, queries)
            bundle.composio_snippets = c_snips
            bundle.composio_urls     = c_urls
            bundle.composio_available = bool(c_snips)
            if not c_snips:
                logger.warning(
                    "[%s] Composio returned no results; falling back to Gemini-only.",
                    app_name,
                )
        except Exception as exc:
            logger.warning(
                "[%s] Composio fetch failed (%s); falling back to Gemini-only.",
                app_name, exc,
            )
    else:
        logger.info(
            "[%s] Composio not configured; using Gemini grounding as primary.",
            app_name,
        )

    # ── Secondary: Gemini grounding ────────────────────────────────────────
    try:
        g_snips, g_urls = await _fetch_via_gemini_grounding(app_name, queries, client)
        bundle.gemini_snippets = g_snips
        bundle.gemini_urls     = g_urls
    except Exception as exc:
        logger.warning("[%s] Gemini grounding failed: %s", app_name, exc)

    if not bundle.all_snippets():
        logger.warning(
            "[%s] Both fetch paths returned no snippets; extraction will rely on "
            "LLM parametric knowledge only — confidence will be Low.",
            app_name,
        )

    return bundle


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

_FEW_SHOT_EXAMPLE = """\
{
  "app_name": "Stripe",
  "category": "Payments",
  "description": "Payment processing platform with comprehensive REST APIs for accepting and managing online payments.",
  "auth_methods": ["API key"],
  "credential_acquisition": "Create a free account at dashboard.stripe.com; secret and publishable API keys are available immediately under Developers > API keys — no approval required.",
  "self_serve_status": "Self-serve",
  "api_type": ["REST"],
  "api_breadth": "Very broad",
  "api_documentation_url": "https://stripe.com/docs/api",
  "mcp_available": "No evidence found",
  "mcp_official": "N/A",
  "mcp_url": null,
  "buildability_verdict": "Easy",
  "primary_blocker": null,
  "evidence": [
    {"claim": "api_type: REST API documented at stripe.com/docs/api", "url": "https://stripe.com/docs/api", "source_tier": 1},
    {"claim": "auth_methods: API key provided immediately after sign-up", "url": "https://dashboard.stripe.com", "source_tier": 1},
    {"claim": "self_serve_status: free account, no gating", "url": "https://stripe.com/docs/keys", "source_tier": 1},
    {"claim": "mcp_available: no MCP server found on glama.ai, mcp.so, smithery.ai", "url": "https://glama.ai/mcp/servers?q=stripe", "source_tier": 3},
    {"claim": "buildability_verdict: easy — full REST docs, instant self-serve key, no blockers", "url": "https://stripe.com/docs", "source_tier": 1}
  ],
  "confidence": "High",
  "human_review_required": false,
  "human_review_notes": null
}"""


def _format_snippets_for_prompt(bundle: SnippetBundle) -> str:
    """Render the SnippetBundle into a readable prompt section."""
    sections: list[str] = []

    if bundle.composio_snippets:
        sections.append("### Sources retrieved via Composio SERP (PRIMARY)")
        for i, s in enumerate(bundle.composio_snippets[:6], 1):
            sections.append(f"[C{i}] {s[:800]}")
        if bundle.composio_urls:
            sections.append("Composio source URLs: " + ", ".join(bundle.composio_urls[:8]))
    else:
        sections.append(
            "### Composio SERP: no results (fell back to Gemini grounding as primary)"
        )

    if bundle.gemini_snippets:
        sections.append("\n### Sources retrieved via Gemini Grounding (SECONDARY CROSS-CHECK)")
        for i, s in enumerate(bundle.gemini_snippets[:6], 1):
            sections.append(f"[G{i}] {s[:800]}")
        if bundle.gemini_urls:
            sections.append("Grounding source URLs: " + ", ".join(bundle.gemini_urls[:8]))
    else:
        sections.append("\n### Gemini Grounding: no results")

    return "\n".join(sections)


def _build_prompt(app_name: str, category: str, bundle: SnippetBundle) -> str:
    """
    Build the single structured-extraction prompt.

    Confidence rules injected into the prompt mirror schema.py's validators so
    the LLM pre-sets them correctly before Pydantic validates:
      - Two independent sources (Composio + Gemini) agree → "High"
      - Only one source confirms → "Medium"
      - Neither source confirms → "Low"
    """
    dual = bundle.has_dual_source()
    source_note = (
        "BOTH Composio and Gemini sources are present. "
        "If they independently confirm the same claim, set confidence='High'. "
        "If only one confirms, set confidence='Medium'."
        if dual
        else
        "Only ONE source path returned results. "
        "Cap confidence at 'Medium' unless the claim is from tier-1 official docs."
    )

    snippets_block = _format_snippets_for_prompt(bundle)

    return f"""\
You are a technical researcher evaluating third-party API integrations for a
developer platform called Composio. Your job is to fill in the JSON schema
below for the app "{app_name}" (category: {category}).

## Source evidence
{snippets_block}

## Confidence rule (IMPORTANT)
{source_note}

## Field instructions

| Field | Guidance |
|---|---|
| description | One neutral sentence, no marketing. |
| auth_methods | List every auth type the developer must use. |
| credential_acquisition | HOW a developer gets credentials — step by step, 1-2 sentences. |
| self_serve_status | MUST be exactly one of: "Self-serve", "Self-serve with restrictions", "Trial", "Paid plan required", "Admin approval", "Partner approval", "Contact sales", "Enterprise only", "Unknown". Do NOT use "Gated", "Enterprise", or any other value. |
| api_type | ["REST"], ["GraphQL"], ["REST","GraphQL"], or ["None found"]. |
| api_breadth | MUST be exactly one of: "Narrow", "Moderate", "Broad", "Very broad", "Unknown". No other values. |
| mcp_available | MUST be exactly one of: "Yes", "No evidence found", "Unknown". NOT "No" or "None". |
| mcp_official | MUST be exactly one of: "Official", "Third-party", "Community", "N/A", "Unknown". |
| buildability_verdict | MUST be exactly one of: "Easy", "Possible", "Difficult", "Blocked", "Unknown". |
| confidence | MUST be exactly one of: "High", "Medium", "Low". |
| evidence | One entry PER KEY CLAIM. claim text must name the field (e.g. "auth_methods: ..."). source_tier: 1=official docs, 2=official blog, 3=reputable 3rd party, 4=community, 5=inferred. |
| human_review_required | Set true if confidence=="Low" or any field lacks evidence. |

## Few-shot example (Stripe)
```json
{_FEW_SHOT_EXAMPLE}
```

## Task
Return ONLY a single valid JSON object matching the schema for **{app_name}**.
No markdown fences, no commentary — raw JSON only.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Structured LLM extraction
# ─────────────────────────────────────────────────────────────────────────────

def _strip_json_from_response(text: str) -> str:
    """
    Some models (3.6, 3.5) wrap JSON in markdown fences or add preamble text.
    This strips any leading/trailing markdown and returns the raw JSON substring.
    """
    import re
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if fence_match:
        return fence_match.group(1).strip()
    # Find the first { and last } — handles preamble like "Here is the JSON:"
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


async def _call_llm_structured(
    prompt: str,
    model: str,
    client,
    app_name: str,
) -> dict:
    """
    Call Gemini with JSON-mode output and return the parsed dict.

    Implements the model cascade: if the chosen model hits its daily quota,
    it is marked exhausted and the next model in _MODEL_FLASH_CASCADE is used.

    We deliberately use json.loads(response.text) rather than response.parsed
    so that our Pydantic model_validators run in full during Phase 3.
    """
    from google.genai import types as _types  # local import

    active_model = model  # may be overridden by cascade below

    async def _do_call():
        nonlocal active_model
        async with _gemini_sem():
            resp = await client.aio.models.generate_content(
                model=active_model,
                contents=prompt,
                config=_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=None,
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )
        text = _strip_json_from_response(resp.text or "")
        if not text:
            raise ValueError("LLM returned empty response")
        return json.loads(text)

    # Cascade loop: try each model in order until one succeeds or all exhausted
    last_exc: Exception | None = None
    attempted: set[str] = set()
    while True:
        try:
            active_model = await _get_active_flash_model()
            if active_model in attempted:
                # We've tried every remaining model
                break
            attempted.add(active_model)
            short = active_model.replace("models/", "")
            if active_model != model:
                logger.info("[%s] Using cascade model: %s", app_name, short)
            return await _with_retry(lambda: _do_call(), app_name=app_name, label=f"LLM({short})")
        except json.JSONDecodeError as exc:
            raise ResearchError(app_name, "llm_parse_failure", cause=exc)
        except RuntimeError as exc:
            # All cascade models exhausted
            raise ResearchError(app_name, "rate_limit", cause=exc)
        except Exception as exc:
            last_exc = exc
            if _is_daily_quota_error(exc):
                await _mark_model_exhausted(active_model)
                continue  # retry with next cascade model
            if _is_retryable(exc):
                raise ResearchError(app_name, "rate_limit", cause=exc)
            raise ResearchError(app_name, "llm_parse_failure", cause=exc)

    raise ResearchError(app_name, "rate_limit", cause=last_exc)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Pydantic parse
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_enums(raw: dict) -> dict:
    """
    Coerce common LLM-invented values to the exact enum strings Pydantic expects.
    Smaller cascade models (3.5-lite, 3.1-lite) sometimes output informal names.
    """
    # ── self_serve_status ────────────────────────────────────────────────────
    _SS_MAP = {
        "gated": "Contact sales",
        "enterprise": "Enterprise only",
        "enterprise only": "Enterprise only",
        "invite only": "Enterprise only",
        "invite-only": "Enterprise only",
        "restricted": "Self-serve with restrictions",
        "restricted access": "Self-serve with restrictions",
        "self-serve": "Self-serve",
        "self serve": "Self-serve",
        "self-serve with restrictions": "Self-serve with restrictions",
        "freemium": "Self-serve",
        "free tier": "Self-serve",
        "free": "Self-serve",
        "signup required": "Self-serve",
        "open": "Self-serve",
        "public": "Self-serve",
        "contact sales": "Contact sales",
        "sales": "Contact sales",
        "sales-gated": "Contact sales",
        "partner": "Partner approval",
        "partner approval": "Partner approval",
        "admin approval": "Admin approval",
        "approval required": "Admin approval",
        "trial": "Trial",
        "paid": "Paid plan required",
        "paid plan": "Paid plan required",
        "paid plan required": "Paid plan required",
        "subscription required": "Paid plan required",
        "unknown": "Unknown",
    }
    ss = raw.get("self_serve_status", "")
    if isinstance(ss, str):
        raw["self_serve_status"] = _SS_MAP.get(ss.strip().lower(), ss)

    # ── buildability_verdict ─────────────────────────────────────────────────
    _BV_MAP = {
        "easy": "Easy",
        "simple": "Easy",
        "straightforward": "Easy",
        "possible": "Possible",
        "feasible": "Possible",
        "moderate": "Possible",
        "difficult": "Difficult",
        "hard": "Difficult",
        "challenging": "Difficult",
        "blocked": "Blocked",
        "not possible": "Blocked",
        "impossible": "Blocked",
        "unknown": "Unknown",
    }
    bv = raw.get("buildability_verdict", "")
    if isinstance(bv, str):
        raw["buildability_verdict"] = _BV_MAP.get(bv.strip().lower(), bv)

    # ── mcp_available ────────────────────────────────────────────────────────
    _MCP_MAP = {
        "yes": "Yes",
        "no": "No evidence found",
        "no evidence found": "No evidence found",
        "none": "No evidence found",
        "none found": "No evidence found",
        "not found": "No evidence found",
        "not available": "No evidence found",
        "unknown": "Unknown",
    }
    mcp = raw.get("mcp_available", "")
    if isinstance(mcp, str):
        raw["mcp_available"] = _MCP_MAP.get(mcp.strip().lower(), mcp)

    # ── mcp_official ─────────────────────────────────────────────────────────
    _MCPO_MAP = {
        "official": "Official",
        "third-party": "Third-party",
        "third party": "Third-party",
        "community": "Community",
        "n/a": "N/A",
        "na": "N/A",
        "none": "N/A",
        "not applicable": "N/A",
        "unknown": "Unknown",
    }
    mcpo = raw.get("mcp_official", "")
    if isinstance(mcpo, str):
        raw["mcp_official"] = _MCPO_MAP.get(mcpo.strip().lower(), mcpo)

    # ── api_breadth ──────────────────────────────────────────────────────────
    _AB_MAP = {
        "narrow": "Narrow",
        "small": "Narrow",
        "limited": "Narrow",
        "minimal": "Narrow",
        "moderate": "Moderate",
        "medium": "Moderate",
        "mid": "Moderate",
        "broad": "Broad",
        "wide": "Broad",
        "large": "Broad",
        "very broad": "Very broad",
        "extensive": "Very broad",
        "comprehensive": "Very broad",
        "unknown": "Unknown",
    }
    ab = raw.get("api_breadth", "")
    if isinstance(ab, str):
        raw["api_breadth"] = _AB_MAP.get(ab.strip().lower(), ab)

    # ── confidence ───────────────────────────────────────────────────────────
    _CONF_MAP = {
        "high": "High",
        "medium": "Medium",
        "med": "Medium",
        "moderate": "Medium",
        "low": "Low",
    }
    conf = raw.get("confidence", "")
    if isinstance(conf, str):
        raw["confidence"] = _CONF_MAP.get(conf.strip().lower(), conf)

    return raw


def _parse_result(raw: dict, app_name: str) -> AppResearch:
    """
    Wrap raw LLM dict in AppResearch.  All schema.py validators run here,
    including cross-field rules (confidence/review flags, MCP URL check, etc.).
    """
    # Ensure list fields are always lists (LLM sometimes returns a string)
    for list_field in ("auth_methods", "api_type", "evidence"):
        val = raw.get(list_field)
        if isinstance(val, str):
            raw[list_field] = [val]
        elif val is None:
            raw[list_field] = [] if list_field == "evidence" else ["Unknown"]
        # Defensive: if it's an empty list for auth_methods/api_type, fill with Unknown
        elif isinstance(val, list) and len(val) == 0 and list_field != "evidence":
            raw[list_field] = ["Unknown"]

    # Sanitize evidence URLs — some models output 'N/A', 'unknown', '' as URL
    _INVALID_URL_SENTINELS = {"n/a", "na", "unknown", "none", "", "null", "undefined"}
    _FALLBACK_URL = "https://example.com/inferred"
    evidence = raw.get("evidence", [])
    if isinstance(evidence, list):
        for entry in evidence:
            if isinstance(entry, dict):
                url = str(entry.get("url") or "").strip()
                if url.lower() in _INVALID_URL_SENTINELS or not url.startswith("http"):
                    entry["url"] = _FALLBACK_URL

    # Coerce LLM-variant enum values to exact schema strings
    raw = _normalize_enums(raw)

    try:
        return AppResearch(**raw)
    except ValidationError as exc:
        raise ResearchError(app_name, "validation_failure", raw_response=str(raw), cause=exc)


# ─────────────────────────────────────────────────────────────────────────────
# Escalation check
# ─────────────────────────────────────────────────────────────────────────────

def _needs_escalation(result: AppResearch) -> bool:
    """
    Returns True if the first-pass result should be retried with the pro model.
    Criteria:
      - confidence is Low, OR
      - human_review_required triggered by a validation contradiction
        (notes contain >1 distinct flag, not just the confidence flag).
    """
    if result.confidence == "Low":
        return True
    notes = result.human_review_notes or ""
    # Count distinct flag lines (blank lines or single "Auto-flagged" don't count)
    real_flags = [
        ln for ln in notes.splitlines()
        if ln.strip() and "Auto-flagged: confidence is Low" not in ln
    ]
    return len(real_flags) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def research_app(app_name: str, category: str) -> AppResearch:
    """
    Full per-app research pipeline.  Returns a validated AppResearch object.
    Raises ResearchError if the pipeline fails unrecoverably after retries.

    Flow
    ----
    1. Fetch snippets (Composio primary + Gemini grounding secondary)
    2. Extract with flash model → parse → validate
    3. If needs_escalation: re-extract with pro model using same snippets
    4. Return the better result (pro pass if escalated, flash pass otherwise)

    Usage
    -----
    >>> import asyncio
    >>> result = asyncio.run(research_app("Stripe", "Payments"))
    >>> print(result.model_dump_json(indent=2))
    """
    from google import genai as _genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in environment/.env")

    client = _genai.Client(api_key=api_key)

    logger.info("[%s] Starting research (category: %s)", app_name, category)
    t0 = time.monotonic()

    # ── Phase 1: Fetch ────────────────────────────────────────────────────────
    bundle = await _fetch_snippets(app_name, client)
    logger.debug(
        "[%s] Snippets: %d Composio + %d Gemini",
        app_name,
        len(bundle.composio_snippets),
        len(bundle.gemini_snippets),
    )

    # ── Phase 2 + 3: Flash extraction (cascade-aware) ─────────────────────────
    prompt = _build_prompt(app_name, category, bundle)
    active_flash = await _get_active_flash_model()
    raw    = await _call_llm_structured(prompt, active_flash, client, app_name)
    result = _parse_result(raw, app_name)

    logger.debug(
        "[%s] Flash pass: verdict=%s confidence=%s review=%s",
        app_name,
        result.buildability_verdict,
        result.confidence,
        result.human_review_required,
    )

    # ── Step 4: Escalation to pro model (skipped if RESEARCH_SKIP_ESCALATION=true) ──
    if not _SKIP_ESCALATION and _needs_escalation(result):
        logger.info(
            "[%s] Escalating to pro model (confidence=%s, flags=%r)",
            app_name,
            result.confidence,
            result.human_review_notes,
        )
        escalation_prompt = (
            prompt
            + "\n\n## ESCALATION NOTE\n"
            + "The previous extraction pass flagged issues. "
            + "Please be more thorough and precise. "
            + "If information is genuinely not available in the sources above, "
            + "use 'Unknown' rather than guessing.\n"
            + f"Previous issues: {result.human_review_notes or 'Low confidence'}"
        )
        try:
            raw_pro    = await _call_llm_structured(
                escalation_prompt, _MODEL_PRO, client, app_name
            )
            result_pro = _parse_result(raw_pro, app_name)
            # Prefer pro result unless it somehow became worse
            if result_pro.confidence != "Low" or result.confidence == "Low":
                result = result_pro
                logger.info("[%s] Pro pass accepted (confidence=%s)", app_name, result.confidence)
            else:
                logger.warning("[%s] Pro pass also Low; keeping flash result", app_name)
        except ResearchError as exc:
            logger.warning(
                "[%s] Pro escalation failed (%s); returning flash result", app_name, exc
            )

    elapsed = time.monotonic() - t0
    logger.info(
        "[%s] Done in %.1fs | verdict=%s confidence=%s review=%s",
        app_name,
        elapsed,
        result.buildability_verdict,
        result.confidence,
        result.human_review_required,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke-test  (python -m src.research <AppName> <Category>)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python -m src.research <AppName> <Category>")
        sys.exit(1)

    _app, _cat = sys.argv[1], sys.argv[2]
    _result = asyncio.run(research_app(_app, _cat))
    print(_result.model_dump_json(indent=2))
