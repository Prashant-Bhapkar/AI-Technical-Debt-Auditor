"""Flask application factory."""
import os
from flask import Flask
from flask_cors import CORS

from backend.routes.audit_routes import audit_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(audit_bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
