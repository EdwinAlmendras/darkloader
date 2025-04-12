import logging

def setup_logger(name: str, level: str = "DEBUG"):
    logging.basicConfig(level=level)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger