"""
Web interface for viewing logs stored in Valkey.
Provides a Flask web server with API endpoints and HTML interface.
"""
import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import structlog

from log_retriever import LogRetriever

# Configure logger
logger = structlog.get_logger()

# Create Flask app
app = Flask(__name__)

# Global variable to store the Valkey client
# This will be set when the app is initialized in the main service
valkey_client = None
log_retriever = None

def init_app(client):
    """
    Initialize the Flask app with a Valkey client.

    Args:
        client: Valkey client instance
    """
    global valkey_client, log_retriever
    valkey_client = client
    log_retriever = LogRetriever(valkey_client)
    logger.info("Log web interface initialized")

@app.route('/')
def index():
    """Main page with log viewer"""
    return render_template('index.html')

@app.route('/api/logs')
def get_logs():
    """API endpoint to get logs with filtering"""
    if not log_retriever:
        return jsonify({"error": "Log retriever not initialized"}), 500

    try:
        # Get query parameters
        start_time = request.args.get('start_time', None)
        end_time = request.args.get('end_time', None)
        level = request.args.get('level', None)
        service = request.args.get('service', None)
        limit = int(request.args.get('limit', 100))

        # Convert time strings to timestamps if provided
        if start_time:
            start_time = datetime.fromisoformat(start_time).timestamp() * 1000
        else:
            # Default to 24 hours ago
            start_time = (datetime.now() - timedelta(days=1)).timestamp() * 1000

        if end_time:
            end_time = datetime.fromisoformat(end_time).timestamp() * 1000
        else:
            end_time = datetime.now().timestamp() * 1000

        # Retrieve logs based on filters
        if level:
            logs = log_retriever.get_logs_by_level(level, limit)
        elif service:
            logs = log_retriever.get_logs_by_service(service, limit)
        else:
            logs = log_retriever.get_logs_by_timerange(start_time, end_time, limit)

        return jsonify(logs)
    except Exception as e:
        logger.error("Error retrieving logs", error=str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/log-levels')
def get_log_levels():
    """Get available log levels"""
    if not log_retriever:
        return jsonify(["info", "error", "warning", "debug"])

    try:
        levels = log_retriever.get_available_log_levels()
        return jsonify(levels)
    except Exception as e:
        logger.error("Error retrieving log levels", error=str(e))
        return jsonify(["info", "error", "warning", "debug"])

@app.route('/api/services')
def get_services():
    """Get available services"""
    if not log_retriever:
        return jsonify(["monarch"])

    try:
        services = log_retriever.get_available_services()
        return jsonify(services)
    except Exception as e:
        logger.error("Error retrieving services", error=str(e))
        return jsonify(["monarch"])

def start_web_interface(host='0.0.0.0', port=8081):
    """
    Start the Flask web interface.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    if not valkey_client:
        logger.error("Cannot start web interface: Valkey client not initialized")
        return

    logger.info("Starting log web interface", host=host, port=port)
    app.run(host=host, port=port, threaded=True)

if __name__ == '__main__':
    # This is for standalone testing only
    # In production, the app should be initialized and started from the main service
    from config import Settings
    import valkey

    settings = Settings()
    client = valkey.Valkey(
        host=settings.VALKEY_HOST,
        port=settings.VALKEY_PORT,
        db=settings.VALKEY_DB,
        decode_responses=False
    )

    init_app(client)
    start_web_interface()