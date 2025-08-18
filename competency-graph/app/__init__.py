from flask import Flask
from pathlib import Path

from routes.job_routes import jobs_bp
from routes.graph_routes import main_bp

def create_app():
    """
        Create and configure the Flask application.
    """
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(__name__,
                template_folder=str(base_dir / "templates"),
                static_folder=str(base_dir / "static"))

    app.register_blueprint(main_bp)
    app.register_blueprint(jobs_bp)

    return app