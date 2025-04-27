from flask import Flask, jsonify # Import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text # <-- Import text here
from config import config
from .models import db

# Initialize limiter (without app object yet)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"] # Apply default limits if desired
)

def create_app():
    """Application Factory Function"""
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    limiter.init_app(app)

    # --- Define Root Route Directly on App ---
    @app.route('/')
    def index():
        try:
            db.session.execute(text('SELECT 1'))
            # Return JSON for success too, for consistency? Optional.
            return jsonify({"status": "running", "database_connection": "successful"})
        except Exception as e:
            app.logger.error(f"Database connection check failed: {e}", exc_info=True)
            # Return JSON error response
            return jsonify({"status": "running", "database_connection": "failed", "error": str(e)}), 500
    # --- End Root Route Definition ---

    # Import and register Blueprints with prefix
    from .routes import bp as main_bp
    app.register_blueprint(main_bp, url_prefix='/api')

    # Optional: Add a command to create tables
    @app.cli.command("create-db")
    def create_db_command():
        """Creates the database tables."""
        with app.app_context(): # Ensure we have app context
            try:
                db.create_all()
                print("Database tables created successfully.")
            except Exception as e:
                print(f"Error creating database tables: {e}")

    return app