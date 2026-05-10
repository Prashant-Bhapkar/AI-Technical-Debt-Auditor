"""Entry point: python run_backend.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# Load .env before anything else so ANTHROPIC_API_KEY etc. are available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from backend.app import create_app

if __name__ == "__main__":
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    # use_reloader=False keeps the in-memory audit store alive across file saves
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
