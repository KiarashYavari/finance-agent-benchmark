"""
XBRL Parsing Tool using Arelle (Async Wrapper)
A2A/MCP-safe. Hardened subprocess execution.
"""

import json
import asyncio
import tempfile
import os


async def parse_xbrl(xbrl_text: str) -> dict:
    """
    Parse XBRL text using Arelle via subprocess.
    Safely handles temp files, timeouts, malformed XML, and missing executables.

    Returns:
        dict containing parsed JSON or {"error": "..."}
    """
    
    # ---------------- Validate Input ----------------
    if not isinstance(xbrl_text, str) or not xbrl_text.strip():
        return {"error": "Empty or invalid XBRL text input"}

    # ---------------- Verify Arelle Exists ----------------
    ARELLE_CMD = os.getenv("ARELLE_CMD")
    if not ARELLE_CMD:
        raise RuntimeError("ARELLE_CMD not set")

    if not os.path.exists(ARELLE_CMD):
        raise RuntimeError(f"Arelle command not found at {ARELLE_CMD}")

    # ---------------- Create Temp File ----------------
    try:
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(xbrl_text.encode("utf-8"))
            temp_path = f.name
    except Exception as e:
        return {"error": f"Failed to write temporary XBRL file: {str(e)}"}

    # Build Arelle command
    cmd = [arelle_path, "-f", temp_path, "--json"]

    try:
        # Subprocess with timeout to avoid hangs
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            ),
            timeout=3  # seconds to start process (not total parse time)
        )
    except asyncio.TimeoutError:
        os.remove(temp_path)
        return {"error": "Arelle failed to start (timeout)"}
    except Exception as e:
        os.remove(temp_path)
        return {"error": f"Failed to start Arelle: {str(e)}"}

    # -------- Wait for Arelle output (with timeout) --------
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    except asyncio.TimeoutError:
        proc.kill()
        os.remove(temp_path)
        return {"error": "Arelle took too long and was terminated (timeout)"}

    # Clean up
    os.remove(temp_path)

    # -------- Check Arelle Return Code --------
    if proc.returncode != 0:
        return {
            "error": (
                f"Arelle parsing failed (exit code {proc.returncode}). "
                f"stderr: {stderr.strip()}"
            )
        }

    # -------- Parse JSON Output --------
    if not stdout.strip():
        return {"error": "Arelle returned empty output"}

    try:
        return json.loads(stdout)
    except Exception:
        return {"error": "Arelle returned invalid JSON output"}
