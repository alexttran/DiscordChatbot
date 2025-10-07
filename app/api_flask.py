# app/api_flask.py - Enhanced with Logging & Observability
from dotenv import load_dotenv
load_dotenv()


import os
import time
import uuid
import logging
from datetime import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from rag.rag import answer as rag_answer
from rag.rag import _get_retriever as get_retriever


# LOGGING SETUP - Structured logging with JSON format

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# METRICS COLLECTION - In-memory metrics (production would use Prometheus)

class Metrics:
    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.endpoint_stats = {}
        self.start_time = datetime.now()
    
    def record_request(self, endpoint, duration, status_code):
        self.total_requests += 1
        if status_code >= 400:
            self.total_errors += 1
        
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                'count': 0,
                'total_duration': 0,
                'errors': 0
            }
        
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_duration'] += duration
        if status_code >= 400:
            stats['errors'] += 1
    
    def get_stats(self):
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            'uptime_seconds': uptime,
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': self.total_errors / max(self.total_requests, 1),
            'endpoints': {
                ep: {
                    'count': stats['count'],
                    'avg_duration_ms': stats['total_duration'] / max(stats['count'], 1),
                    'errors': stats['errors'],
                    'error_rate': stats['errors'] / max(stats['count'], 1)
                }
                for ep, stats in self.endpoint_stats.items()
            }
        }


metrics = Metrics()


# FLASK APP SETUP

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)


# MIDDLEWARE - Request tracking and timing

@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{g.request_id}] {request.method} {request.path} - Request started")


@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = (time.time() - g.start_time) * 1000  # Convert to ms
        
        logger.info(
            f"[{g.request_id}] {request.method} {request.path} - "
            f"Status: {response.status_code} - Duration: {duration:.2f}ms"
        )
        
        # Record metrics
        metrics.record_request(request.path, duration, response.status_code)
        
        # Add headers for observability
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f"{duration:.2f}ms"
    
    return response



# ERROR HANDLERS

@app.errorhandler(Exception)
def handle_exc(e):
    request_id = getattr(g, 'request_id', 'unknown')
    
    if isinstance(e, HTTPException):
        logger.warning(f"[{request_id}] HTTP Exception: {e.code} - {e.description}")
        return jsonify({
            "error": e.description,
            "request_id": request_id
        }), e.code
    
    # Log full stack trace for unexpected errors
    logger.error(f"[{request_id}] Unhandled exception: {type(e).__name__}", exc_info=True)
    
    return jsonify({
        "error": str(e),
        "kind": type(e).__name__,
        "request_id": request_id
    }), 500



# ROOT ENDPOINT - Minimal API Landing Route

@app.route('/')
def index():
    return jsonify({
        "message": "API is running",
        "available_endpoints": [
            "/health",
            "/status",
            "/metrics",
            "/rag/answer",
            "/rag/search"
        ]
    })


# HEALTH & MONITORING ENDPOINTS

@app.get("/health")
def health():
    """Basic health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/status")
def status():
    """Detailed status with system information"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("FLASK_ENV", "production"),
        "metrics": metrics.get_stats()
    })


@app.get("/metrics")
def metrics_endpoint():
    """Prometheus-style metrics endpoint"""
    stats = metrics.get_stats()
    
    # Simple text format (real Prometheus would use proper format)
    lines = [
        f"# HELP http_requests_total Total number of HTTP requests",
        f"# TYPE http_requests_total counter",
        f"http_requests_total {stats['total_requests']}",
        f"",
        f"# HELP http_errors_total Total number of HTTP errors",
        f"# TYPE http_errors_total counter",
        f"http_errors_total {stats['total_errors']}",
        f"",
        f"# HELP app_uptime_seconds Application uptime in seconds",
        f"# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {stats['uptime_seconds']:.2f}",
    ]
    
    return "\n".join(lines), 200, {'Content-Type': 'text/plain'}


# RAG ENDPOINTS - Enhanced with detailed logging

@app.post("/rag/answer")
def rag_api():
    """Main RAG endpoint - retrieves context and generates answer"""
    request_id = g.request_id
    
    # Parse and validate input
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    provider = data.get("provider", "azure")
    
    if not query:
        logger.warning(f"[{request_id}] Missing query parameter")
        return jsonify({"error": "Missing 'query'"}), 400
    
    # Log the request details
    logger.info(f"[{request_id}] RAG Query: '{query[:100]}...' (k={k}, provider={provider})")
    
    try:
        # Time the RAG processing
        rag_start = time.time()
        result = rag_answer(query, k=k, provider=provider)
        rag_duration = (time.time() - rag_start) * 1000
        
        logger.info(f"[{request_id}] RAG processing completed in {rag_duration:.2f}ms")
        
        # Add metadata to response
        result['meta'] = result.get('meta', {})
        result['meta']['request_id'] = request_id
        result['meta']['processing_time_ms'] = rag_duration
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"[{request_id}] RAG processing failed: {str(e)}", exc_info=True)
        raise


@app.post("/rag/search")
def rag_search():
    """Search endpoint - retrieves relevant context chunks"""
    request_id = g.request_id
    
    # Parse and validate input
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    include_text = bool(data.get("include_text", False))
    
    if not query:
        logger.warning(f"[{request_id}] Missing query parameter")
        return jsonify({"error": "Missing 'query'"}), 400
    
    logger.info(f"[{request_id}] Search Query: '{query[:100]}...' (k={k})")
    
    try:
        # Time the retrieval
        retrieval_start = time.time()
        ctxs = get_retriever().search(query, k=k)
        retrieval_duration = (time.time() - retrieval_start) * 1000
        
        logger.info(
            f"[{request_id}] Retrieved {len(ctxs)} chunks in {retrieval_duration:.2f}ms"
        )
        
        if include_text:
            return jsonify(ctxs)
        
        # Hide chunk text in default response
        return jsonify([{k:v for k,v in c.items() if k != "text"} for c in ctxs])
    
    except Exception as e:
        logger.error(f"[{request_id}] Search failed: {str(e)}", exc_info=True)
        raise


# MAIN

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
# app/api_flask.py - Enhanced with Logging & Observability
from dotenv import load_dotenv
load_dotenv()


import os
import time
import uuid
import logging
from datetime import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from rag.rag import answer as rag_answer
from rag.rag import get_retriever


# LOGGING SETUP - Structured logging with JSON format

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# METRICS COLLECTION - In-memory metrics (production would use Prometheus)

class Metrics:
    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.endpoint_stats = {}
        self.start_time = datetime.now()
    
    def record_request(self, endpoint, duration, status_code):
        self.total_requests += 1
        if status_code >= 400:
            self.total_errors += 1
        
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                'count': 0,
                'total_duration': 0,
                'errors': 0
            }
        
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_duration'] += duration
        if status_code >= 400:
            stats['errors'] += 1
    
    def get_stats(self):
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            'uptime_seconds': uptime,
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': self.total_errors / max(self.total_requests, 1),
            'endpoints': {
                ep: {
                    'count': stats['count'],
                    'avg_duration_ms': stats['total_duration'] / max(stats['count'], 1),
                    'errors': stats['errors'],
                    'error_rate': stats['errors'] / max(stats['count'], 1)
                }
                for ep, stats in self.endpoint_stats.items()
            }
        }


metrics = Metrics()


# FLASK APP SETUP

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)



# MIDDLEWARE - Request tracking and timing

@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{g.request_id}] {request.method} {request.path} - Request started")


@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = (time.time() - g.start_time) * 1000  # Convert to ms
        
        logger.info(
            f"[{g.request_id}] {request.method} {request.path} - "
            f"Status: {response.status_code} - Duration: {duration:.2f}ms"
        )
        
        # Record metrics
        metrics.record_request(request.path, duration, response.status_code)
        
        # Add headers for observability
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f"{duration:.2f}ms"
    
    return response


# ERROR HANDLERS

@app.errorhandler(Exception)
def handle_exc(e):
    request_id = getattr(g, 'request_id', 'unknown')
    
    if isinstance(e, HTTPException):
        logger.warning(f"[{request_id}] HTTP Exception: {e.code} - {e.description}")
        return jsonify({
            "error": e.description,
            "request_id": request_id
        }), e.code
    
    # Log full stack trace for unexpected errors
    logger.error(f"[{request_id}] Unhandled exception: {type(e).__name__}", exc_info=True)
    
    return jsonify({
        "error": str(e),
        "kind": type(e).__name__,
        "request_id": request_id
    }), 500


# ROOT ENDPOINT - Minimal API Landing Route

@app.route('/')
def index():
    return jsonify({
        "message": "API is running",
        "available_endpoints": [
            "/health",
            "/status",
            "/metrics",
            "/rag/answer",
            "/rag/search"
        ]
    })



# HEALTH & MONITORING ENDPOINTS

@app.get("/health")
def health():
    """Basic health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/status")
def status():
    """Detailed status with system information"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("FLASK_ENV", "production"),
        "metrics": metrics.get_stats()
    })


@app.get("/metrics")
def metrics_endpoint():
    """Prometheus-style metrics endpoint"""
    stats = metrics.get_stats()
    
    # Simple text format (real Prometheus would use proper format)
    lines = [
        f"# HELP http_requests_total Total number of HTTP requests",
        f"# TYPE http_requests_total counter",
        f"http_requests_total {stats['total_requests']}",
        f"",
        f"# HELP http_errors_total Total number of HTTP errors",
        f"# TYPE http_errors_total counter",
        f"http_errors_total {stats['total_errors']}",
        f"",
        f"# HELP app_uptime_seconds Application uptime in seconds",
        f"# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {stats['uptime_seconds']:.2f}",
    ]
    
    return "\n".join(lines), 200, {'Content-Type': 'text/plain'}


# RAG ENDPOINTS - Enhanced with detailed logging

@app.post("/rag/answer")
def rag_api():
    """Main RAG endpoint - retrieves context and generates answer"""
    request_id = g.request_id
    
    # Parse and validate input
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    provider = data.get("provider", "azure")
    
    if not query:
        logger.warning(f"[{request_id}] Missing query parameter")
        return jsonify({"error": "Missing 'query'"}), 400
    
    # Log the request details
    logger.info(f"[{request_id}] RAG Query: '{query[:100]}...' (k={k}, provider={provider})")
    
    try:
        # Time the RAG processing
        rag_start = time.time()
        result = rag_answer(query, k=k, provider=provider)
        rag_duration = (time.time() - rag_start) * 1000
        
        logger.info(f"[{request_id}] RAG processing completed in {rag_duration:.2f}ms")
        
        # Add metadata to response
        result['meta'] = result.get('meta', {})
        result['meta']['request_id'] = request_id
        result['meta']['processing_time_ms'] = rag_duration
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"[{request_id}] RAG processing failed: {str(e)}", exc_info=True)
        raise


@app.post("/rag/search")
def rag_search():
    """Search endpoint - retrieves relevant context chunks"""
    request_id = g.request_id
    
    # Parse and validate input
    data = request.get_json(force=True, silent=False) or {}
    query = data.get("query", "")
    k = int(data.get("k", 4))
    include_text = bool(data.get("include_text", False))
    
    if not query:
        logger.warning(f"[{request_id}] Missing query parameter")
        return jsonify({"error": "Missing 'query'"}), 400
    
    logger.info(f"[{request_id}] Search Query: '{query[:100]}...' (k={k})")
    
    try:
        # Time the retrieval
        retrieval_start = time.time()
        ctxs = get_retriever().search(query, k=k)
        retrieval_duration = (time.time() - retrieval_start) * 1000
        
        logger.info(
            f"[{request_id}] Retrieved {len(ctxs)} chunks in {retrieval_duration:.2f}ms"
        )
        
        if include_text:
            return jsonify(ctxs)
        
        # Hide chunk text in default response
        return jsonify([{k:v for k,v in c.items() if k != "text"} for c in ctxs])
    
    except Exception as e:
        logger.error(f"[{request_id}] Search failed: {str(e)}", exc_info=True)
        raise


# MAIN

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
