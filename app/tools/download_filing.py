"""
Official SEC Filing Document Downloader (Async)
Rate-limit aware, A2A/MCP-safe, structured error outputs.
"""

import aiohttp
import backoff
from typing import Union, Dict

SEC_HEADERS = {
    "User-Agent": "KiarashAI/1.0 (kiarash@example.com)",
    "Accept": "*/*",
}


# ---------------- Rate-Limit Helper ----------------

def is_rate_limit_error(exc):
    """
    Retry on SEC rate limiting or overload conditions.
    """
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status in (429, 503, 504)
    return False


# ---------------- Download Function ----------------

@backoff.on_exception(
    backoff.expo,
    aiohttp.ClientResponseError,
    giveup=lambda e: not is_rate_limit_error(e),
    max_time=45,
    jitter=backoff.full_jitter,
)
async def download_filing_document(
    cik: str,
    accession: str,
    file_name: str,
) -> Union[str, bytes, Dict[str, str]]:
    """
    Download any SEC EDGAR filing document (HTML, TXT, XML, JSON, PDF, etc.)
    
    Args:
        cik: Company CIK (numeric string)
        accession: Accession number with or without dashes
        file_name: Document file name (e.g. '10-K.htm', 'R1.htm', 'full-submission.txt')

    Returns:
        str (text), bytes (binary), or {"error": "..."}
    """

    # -------- Normalize CIK --------
    try:
        cik_clean = str(int(cik))
    except Exception:
        return {"error": f"Invalid CIK: {cik}"}

    # -------- Normalize accession --------
    if not accession or not isinstance(accession, str):
        return {"error": f"Invalid accession number: {accession}"}

    accession_no_dash = accession.replace("-", "").strip()

    # -------- Validate file_name --------
    if not file_name or "/" in file_name or "\\" in file_name:
        return {"error": f"Invalid file name: {file_name}"}

    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_clean}/{accession_no_dash}/{file_name}"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=SEC_HEADERS) as resp:

                # Typical: older filings may not have certain files
                if resp.status == 404:
                    return {
                        "error": f"Document not found (404): {file_name}. "
                                 "This file may not exist for this filing."
                    }

                resp.raise_for_status()

                # Detect content type for text vs binary
                content_type = resp.headers.get("Content-Type", "").lower()

                if any(t in content_type for t in ["text", "json", "xml", "html"]):
                    return await resp.text()

                # For PDFs, images, zips, and unknown types → return raw bytes
                return await resp.read()

    except aiohttp.ClientResponseError as e:
        return {"error": f"SEC returned HTTP {e.status}: {e.message}"}

    except aiohttp.ClientConnectionError as e:
        return {"error": f"Network connection error: {str(e)}"}

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
