"""Retry logic with exponential backoff for LLM API calls.

Provides decorators and utility functions for handling transient failures
in LLM API calls with configurable retry attempts and delays.
"""

import time
import logging
from typing import Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def exponential_backoff_retry(
    max_attempts: int = 3,
    delays: list[int] = None,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Decorator for exponential backoff retry logic.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delays: List of delay seconds for each retry [1, 2, 4] (default)
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @exponential_backoff_retry(max_attempts=3, delays=[1, 2, 4])
        def call_llm_api():
            # API call that may fail transiently
            pass
    """
    if delays is None:
        delays = [1, 2, 4]  # Default exponential backoff: 1s, 2s, 4s

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        delay = delays[min(attempt, len(delays) - 1)]
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )

            # If all attempts failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    delays: list[int] = None,
    exceptions: tuple = (Exception,),
    *args,
    **kwargs
) -> T:
    """Execute a function with exponential backoff retry logic.

    Functional alternative to the decorator pattern.

    Args:
        func: Function to execute with retry logic
        max_attempts: Maximum number of retry attempts
        delays: List of delay seconds for each retry
        exceptions: Tuple of exception types to catch and retry
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of successful function execution

    Raises:
        Last exception if all attempts fail

    Example:
        result = retry_with_backoff(
            call_llm_api,
            max_attempts=3,
            delays=[1, 2, 4],
            exceptions=(APIError, TimeoutError),
            prompt="Extract core idea"
        )
    """
    if delays is None:
        delays = [1, 2, 4]

    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)

        except exceptions as e:
            last_exception = e

            if attempt < max_attempts - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed: {str(e)}")

    raise last_exception
