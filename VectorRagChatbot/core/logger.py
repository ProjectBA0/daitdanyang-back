import sys
import time
import uuid
import json
import logging
import hashlib
import base64
import os
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import numpy as np

# ContextVars
request_id_context = ContextVar("request_id", default="SYSTEM")
start_time_context = ContextVar("start_time", default=0.0)

# Numpy Converter Helper
def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    return obj

# Master Logging Schema for Nyang V6
def serialize_deep(record):
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "level": record["level"].name,
        "request_id": record["extra"].get("request_id", "SYSTEM"),
        "message": record["message"],
    }
    
    if "payload" in record["extra"]:
        payload = record["extra"]["payload"]
        safe_payload = convert_numpy(payload)
        for key, value in safe_payload.items():
            log_entry[key] = value
                
    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback
        }
    return json.dumps(log_entry, ensure_ascii=False) + "\n"

def deep_json_sink(message):
    record = message.record
    serialized = serialize_deep(record)
    # Use absolute path or relative to project root
    log_file = os.path.join(os.path.dirname(__file__), "logs", "nyang_blackbox.jsonl")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(serialized)

def request_id_filter(record):
    rid = request_id_context.get()
    if rid is None: rid = "SYSTEM"
    record["extra"]["request_id"] = rid
    return True

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]}</cyan> | <level>{message}</level>", filter=request_id_filter, level="INFO", enqueue=True)
    logger.add(deep_json_sink, filter=request_id_filter, level="DEBUG", enqueue=True)
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = str(uuid.uuid4())[:8]
        token_id = request_id_context.set(rid)
        st = time.time()
        try:
            response = await call_next(request)
            duration = (time.time() - st) * 1000
            if request.url.path.startswith("/stream"):
                logger.bind(payload={"type": "METRIC", "path": request.url.path, "latency_ms": round(duration, 2), "status": response.status_code}).info("Request Processed")
            return response
        finally:
            request_id_context.reset(token_id)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try: level = logger.level(record.levelname).name
        except ValueError: level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

