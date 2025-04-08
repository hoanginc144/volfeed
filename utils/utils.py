""" Utility functions for the project. """
import time
import functools


def timer(func):
    """Print the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return result
    return wrapper


async def cleanup(*args):
    """a cleanup function that takes a list of objects or a single object
    and calls the close method on each object"""
    for arg in args:
        if isinstance(arg, list):
            for obj in arg:
                await obj.close()
        else:
            await arg.close()
