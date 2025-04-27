from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text
from flask_cors import CORS # Import CORS
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

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    # Initialize CORS - Basic setup allows all origins
    # CORS(app)
    # OR more specific setup:
    CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "https://*.vercel.app"]}})
    # Adjust origins:
    # - "http://localhost:5173" (or your Vue dev server port)
    # - "https://*.vercel.app" (allows any Vercel deployment - adjust if needed)
    # - Or your specific frontend production URL

    # --- Define Root Route ---
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

    # Import and register Blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp, url_prefix='/api')

    # --- CLI Commands ---
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