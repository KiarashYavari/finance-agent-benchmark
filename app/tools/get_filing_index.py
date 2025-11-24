"""
Official SEC EDGAR Filing Index Fetcher (Async)
A2A/MCP-safe: deterministic inputs/outputs, structured errors.
"""

import aiohttp
import backoff
import json
from typing import Optional

# Reuse the same SEC headers from your edgar_search tool
SEC_HEADERS = {
    "User-Agent": "KiarashAI/1.0 (kiarash@example.com)",
    "Accept": "application/json",
}


# ---------------- Rate-Limit Logic ----------------

def is_rate_limit_error(exc):
    """
    Handles SEC throttling behavior:
    - 429 Too Many Requests
    - 503/504 Server load
    """
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status in (429, 503, 504)
    return False


# ---------------- Main Function ----------------

@backoff.on_exception(
    backoff.expo,
    aiohttp.ClientResponseError,
    giveup=lambda e: not is_rate_limit_error(e),
    max_time=45,
    jitter=backoff.full_jitter,
)
async def get_filing_index(cik: str, accession: str) -> dict:
    """
    Fetch the SEC filing's index.json.
    Example:
      https://www.sec.gov/Archives/edgar/data/320193/000032019324000010/index.json
    
    Args:
        cik: Company CIK (e.g. "320193")
        accession: Raw accession number w/ dashes (e.g. "0000320193-24-000010")
                   SEC requires removing dashes for folder path.
    
    Returns:
        dict with SEC index metadata OR {"error": "..."}
    """

    # -------- Normalize inputs --------
    try:
        cik = str(int(cik))  # ensures numeric CIK; removes leading zeros
    except Exception:
        return {"error": f"Invalid CIK: {cik}"}

    if not isinstance(accession, str) or len(accession) < 10:
        return {"error": f"Invalid accession number: {accession}"}

    # remove dashes for SEC archive path
    accession_no_dash = accession.replace("-", "").strip()

    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik}/{accession_no_dash}/index.json"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=SEC_HEADERS) as resp:

                # handle common 404 for filings which have no index.json
                if resp.status == 404:
                    return {
                        "error": "Filing not found (404). "
                                 "This filing may be too old or not indexed."
                    }

                resp.raise_for_status()
                return await resp.json()

    except aiohttp.ClientResponseError as e:
        return {"error": f"SEC returned HTTP {e.status}: {e.message}"}

    except aiohttp.ClientConnectionError as e:
        return {"error": f"Network connection error: {str(e)}"}

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
