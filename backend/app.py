"""Flask application factory."""
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from backend.core import audit_store
from backend.limiter import limiter
from backend.routes.audit_routes import audit_bp, get_audits_store
from backend.routes.qa_routes import qa_bp, init_qa_routes
from backend.routes.report_routes import report_bp, init_report_routes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Connect to Redis if configured; silently falls back to in-memory store
    audit_store.init()

    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Rate limit reached: 2 audits per day per IP. Try again tomorrow."), 429

    app.register_blueprint(audit_bp)

    store_proxy, lock = get_audits_store()
    init_qa_routes(store_proxy, lock)
    app.register_blueprint(qa_bp)

    init_report_routes(store_proxy, lock)
    app.register_blueprint(report_bp)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "version": "1.1.0",
            "async_engine": audit_store.USING_REDIS,
        }

    return app


if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
