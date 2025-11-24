"""
Official SEC XBRL Company Facts Fetcher (Async)
A2A/MCP-safe: deterministic IO, structured errors, proper rate limiting.
"""

import aiohttp
import backoff
from typing import Optional

SEC_HEADERS = {
    "User-Agent": "KiarashAI/1.0 (kiarash996@yahoo.com)",
    "Accept": "application/json",
}

BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


# ---------------- Rate-Limit Helper ----------------

def is_rate_limit_error(exc):
    """
    SEC throttles aggressively on /api/xbrl/ endpoints.
    Retry only on:
      - 429 Too Many Requests
      - 503/504 (server overload)
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
async def get_company_facts(cik: str) -> dict:
    """
    Fetch SEC XBRL company facts for a company.
    Example:
      https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

    Args:
        cik: Raw CIK (numeric string). Leading zeros are required.

    Returns:
        dict: Parsed JSON response OR {"error": "…"}.
    """

    # -------- Normalize CIK --------
    try:
        cik_clean = str(int(cik))     # ensures it's numeric
    except Exception:
        return {"error": f"Invalid CIK: {cik}"}

    cik_padded = cik_clean.zfill(10)

    url = BASE_URL.format(cik=cik_padded)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=SEC_HEADERS) as resp:

                # SEC responds with 404 when company facts do not exist
                # (very common for small companies or very old CIKs)
                if resp.status == 404:
                    return {
                        "error": (
                            "Company facts not found (404). "
                            "This company may not have XBRL filings."
                        )
                    }

                resp.raise_for_status()

                # Sometimes SEC returns empty body on 200 — handle gracefully
                try:
                    return await resp.json()
                except Exception:
                    return {"error": "Malformed JSON from SEC (empty or invalid body)"}

    except aiohttp.ClientResponseError as e:
        return {"error": f"SEC returned HTTP {e.status}: {e.message}"}

    except aiohttp.ClientConnectionError as e:
        return {"error": f"Network connection error: {str(e)}"}

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
