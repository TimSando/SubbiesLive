"""Simple in-process TTL cache utilities.

Uses an in-memory dict to store query results, keyed by function name and arguments.
Suitable for a single-container home server environment.
"""

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("uvicorn.error")

# Global cache store: {cache_key: (value, expiry_timestamp)}
_cache: dict[str, tuple[Any, float]] = {}


def ttl_cache(ttl_seconds: int = 300):
    """Decorator that caches an async function's return value for `ttl_seconds`.

    Builds a cache key from the function name and its stringified arguments
    (ignoring the first argument, which is typically the database session).
    """

    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            # Skip the first argument (usually the async db session)
            key_args = args[1:]

            # Create a string representation of arguments for the key
            arg_str = ",".join(str(a) for a in key_args)
            kwarg_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"{fn.__module__}.{fn.__name__}:{arg_str}:{kwarg_str}"

            now = time.monotonic()
            if cache_key in _cache:
                value, expiry = _cache[cache_key]
                if now < expiry:
                    logger.info(f"Cache hit: {cache_key}")
                    return value
                else:
                    logger.debug(f"Cache expired for: {cache_key}")

            # Call the underlying async function
            result = await fn(*args, **kwargs)

            # Cache the result
            _cache[cache_key] = (result, now + ttl_seconds)
            logger.info(f"Cache miss. Set cache for: {cache_key} (TTL: {ttl_seconds}s)")
            return result

        def invalidate():
            """Clear all cached entries starting with this function's key prefix."""
            prefix = f"{fn.__module__}.{fn.__name__}:"
            keys_to_remove = [k for k in _cache if k.startswith(prefix)]
            for k in keys_to_remove:
                _cache.pop(k, None)
            logger.info(
                f"Invalidated {len(keys_to_remove)} cache entries for function {fn.__name__}"
            )

        wrapper.invalidate = invalidate
        return wrapper

    return decorator
