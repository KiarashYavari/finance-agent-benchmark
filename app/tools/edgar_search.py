"""
Official SEC EDGAR Search Tool (Async)
Designed for AI Agent Tools (A2A/MCP-safe patterns)
Uses official SEC "search-index" API
"""

import aiohttp
import backoff
import json
import sys
from typing import List, Optional

# --- SEC Requirements ---
# SEC requires a descriptive User-Agent including:
# - Contact email
# - Company name / application name
# https://www.sec.gov/os/accessing-edgar-data
SEC_HEADERS = {
    "User-Agent": "KiarashAI/1.0 (kiarash996@yahoo.com)",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


# ------------ Rate Limit Helpers ------------

def is_rate_limit_error(exc):
    """
    SEC returns 429 when rate limits are hit.
    Also treat 503/504 as transient server load.
    """
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status in (429, 503, 504)
    return False


# ------------ Main Search Function ------------

@backoff.on_exception(
    backoff.expo,
    aiohttp.ClientResponseError,
    giveup=lambda e: not is_rate_limit_error(e),
    max_time=45,  # limit total backoff wait
    jitter=backoff.full_jitter,
)
async def edgar_search(
    query: str,
    forms: Optional[List[str]] = None,
    start: int = 0,
    size: int = 10,
) -> dict:
    """
    Async wrapper for the official SEC Full-Text Search API.

    Args:
        query: Free-text search term
        forms: Optional list of form types (["10-K", "10-Q"])
        start: Start offset
        size: Number of records to return (max ~250)
    Returns:
        dict: Parsed SEC JSON response OR {"error": "..."}
    """

    # normalize forms parameter
    if isinstance(forms, str):  # allow "[10-K, 10-Q]" coming from LLMs
        try:
            forms = json.loads(forms.replace("'", '"'))
        except json.JSONDecodeError:
            forms = [x.strip("\"' ") for x in forms.strip("[]").split(",")]

    payload = {
        "keys": query,
        "start": start,
        "from": start,   # SEC accepts both, but "start/from" must match
        "size": size,
    }

    if forms:
        payload["forms"] = forms

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SEARCH_URL,
                headers=SEC_HEADERS,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    except aiohttp.ClientResponseError as e:
        # structured agent-friendly error
        return {"error": f"SEC returned HTTP {e.status}: {e.message}"}

    except aiohttp.ClientConnectionError as e:
        return {"error": f"Connection error: {str(e)}"}

    except Exception as e:
        return {"error": f"Unknown error: {str(e)}"}
