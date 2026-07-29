"""Function execution timing utilities."""

import functools
import time

from cahier_doleances.extraction.settings import logger


def timed(_func=None):
    """Decorator that logs how long a function call took.

    Can be used with or without arguments::

        @timed
        def foo(): ...

    Only logs at ``INFO`` level via the module-level logger.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            result = func(*args, **kwargs)
            dt = time.perf_counter() - t0
            logger.info("%s took %.2fs", func.__name__, dt)
            return result
        return wrapper

    return decorator if _func is None else decorator(_func)
