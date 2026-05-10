"""Flask application factory."""
import os
from flask import Flask
from flask_cors import CORS

from backend.routes.audit_routes import audit_bp, get_audits_store
from backend.routes.qa_routes import qa_bp, init_qa_routes
from backend.routes.report_routes import report_bp, init_report_routes


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(audit_bp)

    audits, lock = get_audits_store()
    init_qa_routes(audits, lock)
    app.register_blueprint(qa_bp)

    init_report_routes(audits, lock)
    app.register_blueprint(report_bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.3.0"}

    return app


if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
