import logging
import json
from datetime import datetime

# In a real setup, request_id_context would be a ContextVar
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
            "service": "praxis-backend",
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_structured_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
