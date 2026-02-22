import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Configures the root logger to write to stdout.
    This allows the output to be captured by the run_monitor.sh script.
    """
    # Create a custom formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create a stream handler (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates if called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)

    # Quiet down some noisy libraries
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger
