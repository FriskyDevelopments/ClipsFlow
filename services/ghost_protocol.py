import os
import httpx
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Defaults to the Azure Container App routing if both are in the same environment, or localhost for dev.
GHOST_API_URL = os.environ.get("GHOST_API_URL", "http://localhost:8080")

async def get_cached_ghost_pointer(url: str) -> Optional[Dict]:
    """Retrieve the cached Telegram File ID and metadata from the Ghost Vault."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GHOST_API_URL}/api/ghost/retrieve", params={"url": url}, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    return {
                        "file_id": data.get("file_id"),
                        "file_size": data.get("file_size")
                    }
    except httpx.ConnectError:
        logger.warning("Ghost API not reachable. Skipping cache lookup.")
    except Exception as e:
        logger.warning(f"Failed to lookup ghost pointer: {e}")
    return None

async def store_ghost_pointer(url: str, file_id: str, file_size: Optional[int] = None, uploaded_by: Optional[str] = None) -> None:
    """Securely vault a File ID after successfully uploading to Telegram."""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "url": url,
                "file_id": file_id,
                "file_size": file_size,
                "uploaded_by": uploaded_by
            }
            resp = await client.post(f"{GHOST_API_URL}/api/ghost/store", json=payload, timeout=3.0)
            if resp.status_code != 201:
                logger.warning(f"Failed to securely vault ghost pointer: {resp.text}")
    except httpx.ConnectError:
        logger.warning("Ghost API not reachable. Skipping cache vault.")
    except Exception as e:
        logger.warning(f"Failed to securely vault ghost pointer: {e}")
