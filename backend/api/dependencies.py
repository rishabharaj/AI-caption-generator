"""
CapturaAI — API dependencies.

Provides dependency injection for API key extraction and optional validation.
"""

import logging
import os
from typing import Optional

from fastapi import Header

from backend.utils.validators import validate_api_key

logger = logging.getLogger(__name__)


async def get_api_key(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Optional[str]:
    """
    Extract and optionally validate the Fireworks API key from the Authorization header,
    with fallback to the FIREWORKS_API_KEY environment variable.

    The key is expected in the format: "Bearer fw_..."

    If no key is provided in header or env, returns None (falls back to MockAI).

    Args:
        authorization: The raw Authorization header value.

    Returns:
        The extracted API key string, or None if not provided.
    """
    key = None
    if authorization:
        # Strip "Bearer " prefix if present
        key = authorization
        if key.lower().startswith("bearer "):
            key = key[7:].strip()

    # Fallback to environment variable if header key is missing/empty
    if not key:
        key = os.environ.get("FIREWORKS_API_KEY", "").strip()

    if not key:
        logger.debug("No API key provided in header or environment — will use MockAI fallback")
        return None

    if validate_api_key(key):
        logger.debug("Valid Fireworks API key detected (length=%d)", len(key))
        return key

    logger.warning("Invalid API key format — falling back to MockAI")
    return None


async def require_api_key(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """
    Extract and validate the Fireworks API key from header or environment. Raises if missing.

    Args:
        authorization: The raw Authorization header value.

    Returns:
        The validated API key string.

    Raises:
        APIKeyError: If the key is missing or invalid.
    """
    from backend.api.exceptions import APIKeyError

    key = None
    if authorization:
        key = authorization
        if key.lower().startswith("bearer "):
            key = key[7:].strip()

    if not key:
        key = os.environ.get("FIREWORKS_API_KEY", "").strip()

    if not key:
        raise APIKeyError(
            "Missing API key. Provide your Fireworks API key in UI or set the FIREWORKS_API_KEY environment variable."
        )

    if not validate_api_key(key):
        raise APIKeyError(
            "Invalid API key format. Key must start with 'fw_' and be at least 32 characters."
        )

    return key
