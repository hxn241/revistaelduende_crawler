import datetime as dt
import logging
import os
from functools import wraps
import time


def retry(max_retries, wait_time=5):
    """
    Decorator to retry any functions 'max_retries' times.
    """
    def retry_decorator(func):
        @wraps(func)
        def retried_function(*args, **kwargs):
            for i in range(max_retries):
                try:
                    values = func(*args, **kwargs)
                    return values
                except Exception as e:
                    print(f"Retrying...Attempt number {i + 1} - {e}")
                    time.sleep(wait_time)
            func(*args, **kwargs)

        return retried_function

    return retry_decorator


def timer(func_name):
    """
    Decorator to compute function execution time
    """

    def timer_decorator(func):
        @wraps(func)
        def wrapper_timer(*args, **kwargs):
            tic = time.perf_counter()
            value = func(*args, **kwargs)
            toc = time.perf_counter()
            elapsed_time = (toc - tic) / 60
            print(f"Elapsed time to run {func_name}: {elapsed_time:0.2f} minutes")
            return value

        return wrapper_timer

    return timer_decorator


# SETUP LOGGER
def setup_logger(log_filename, src_path, level=logging.INFO):
    """
    Setup logger configuration:
        - FileHandler: Log into a file
        - StreamHandler: Log into command line
    """
    # noinspection PyArgumentList
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%H:%M:%S',
        level=level,
        handlers=[
            logging.FileHandler(os.path.join(src_path, "logs", log_filename)),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def parse_date_from_str(date_str):
    try:
        return dt.datetime.strptime(date_str.rsplit("+", 1)[0], "%Y-%m-%dT%H:%M:%S")
    except:
        return dt.datetime.now()


def is_current_period(date, period):
    try:
        return round((dt.datetime.now() - date).total_seconds() / 3600, 0) <= period
    except:
        return False
