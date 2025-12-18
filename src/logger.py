
import logging
import sys

def setup_logger(name=__name__, level=logging.INFO):
    """
    Sets up a logger with the specified name and level.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if handlers already exist to avoid duplicate logs
    if not logger.handlers:
        # Create console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(ch)

    return logger
