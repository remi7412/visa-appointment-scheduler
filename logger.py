import logging
import os
import queue
from datetime import datetime

log_queue = queue.Queue(maxsize=1000)

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Remove old logs if queue is full to prevent blocking
            if log_queue.full():
                try:
                    log_queue.get_nowait()
                except queue.Empty:
                    pass
            log_queue.put_nowait(msg)
        except Exception:
            self.handleError(record)

def setup_logger():
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('VisaBot')
    logger.setLevel(logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Create queue handler for web UI
    queue_handler = QueueHandler()
    queue_handler.setFormatter(formatter)
    
    # Create file handlers
    today = datetime.now().strftime('%Y-%m-%d')
    today_handler = logging.FileHandler(f'logs/{today}.log')
    today_handler.setFormatter(formatter)
    
    errors_handler = logging.FileHandler('logs/errors.log')
    errors_handler.setLevel(logging.ERROR)
    errors_handler.setFormatter(formatter)
    
    # Add handlers to logger
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(queue_handler)
        logger.addHandler(today_handler)
        logger.addHandler(errors_handler)
        
    return logger

log = setup_logger()
