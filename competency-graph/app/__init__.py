from flask import Flask
from pathlib import Path

def create_app():
    project_root = Path(__file__).resolve().parent.parent  # -> .../competency-graph
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )

    from .routes.graph_routes import main_bp
    from .routes.job_routes import jobs_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(jobs_bp)
    return app
