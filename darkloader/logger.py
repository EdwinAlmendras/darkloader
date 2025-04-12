import logging

def setup_logger(name="DarkLoader", level=logging.DEBUG):
    # Crear un logger
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level) 
        # Crear un manejador de consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level) 
        
        # Usar el ColoredFormatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger