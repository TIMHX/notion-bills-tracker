import logging


def setup_logger(name: str, log_level_str: str = "WARNING") -> logging.Logger:
    """
    Sets up a logger with a configurable log level.

    Args:
        name: The name of the logger (usually __name__).
        log_level_str: The desired log level as a string (e.g., "DEBUG", "INFO", "WARNING").
                       Defaults to "WARNING".

    Returns:
        A configured logging.Logger object.
    """
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = log_level_map.get(log_level_str.upper(), logging.WARNING)

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        # If handlers already exist, ensure the level is set correctly
        logger.setLevel(log_level)
        # Optionally, update formatter if needed, but usually not necessary if it's a shared handler
        for handler in logger.handlers:
            handler.setFormatter(formatter)  # Re-apply formatter in case it was changed

    return logger


# Example of how to use it in a module:
# logger = setup_logger(__name__, os.getenv("LOG_LEVEL", "WARNING"))
# logger.debug("This is a debug message")
# logger.info("This is an info message")
# logger.warning("This is a warning message")
# logger.error("This is an error message")
# logger.critical("This is a critical message")
