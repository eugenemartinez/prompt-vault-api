from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
import os
import uuid
import datetime
import psycopg2 # Add this line for testing

# Load environment variables from .env file
load_dotenv() # Keep this for local development

app = Flask(__name__)

# --- Database Configuration ---
# Read from NEON_DATABASE_URL first (for Vercel), fall back to DATABASE_URL (for local .env)
DATABASE_CONNECTION_STRING = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_CONNECTION_STRING:
    raise ValueError("No NEON_DATABASE_URL or DATABASE_URL set for Flask application")

# Use the determined connection string
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_CONNECTION_STRING
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable modification tracking

db = SQLAlchemy(app)

# --- Database Model ---
class Prompt(db.Model):
    __tablename__ = 'prompts' # Optional: Define table name explicitly

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    text = db.Column(db.Text, nullable=False)
    modification_code = db.Column(db.String(8), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    read_only = db.Column(db.Boolean, default=False, nullable=False)
    # Add other fields as needed (e.g., category, tags)

    def to_dict(self):
        """Helper method to convert model instance to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            # Don't expose modification_code by default in GET requests
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_only": self.read_only
        }

# Helper function to generate a unique modification code (keep this)
def generate_modification_code():
    return str(uuid.uuid4())[:8]

# --- API Routes (Modified for Database) ---

@app.route('/prompts', methods=['GET'])
def get_prompts():
    """Retrieve all prompts."""
    all_prompts = Prompt.query.all()
    return jsonify([prompt.to_dict() for prompt in all_prompts])

@app.route('/prompts/<string:prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """Retrieve a specific prompt by ID."""
    prompt = Prompt.query.get(prompt_id)
    if prompt:
        return jsonify(prompt.to_dict())
    else:
        return jsonify({"error": "Prompt not found"}), 404

@app.route('/prompts', methods=['POST'])
def add_prompt():
    """Add a new prompt."""
    if not request.json or not 'title' in request.json or not 'text' in request.json:
        return jsonify({"error": "Missing title or text in request body"}), 400

    # Basic validation (can be expanded)
    title = request.json['title'].strip()
    text = request.json['text'].strip()
    if not title or not text:
        return jsonify({"error": "Title and text cannot be empty"}), 400

    modification_code = generate_modification_code()
    # Ensure modification code is unique (rare collision, but good practice)
    while Prompt.query.filter_by(modification_code=modification_code).first():
        modification_code = generate_modification_code()

    new_prompt = Prompt(
        title=title,
        text=text,
        modification_code=modification_code
        # 'id' and 'created_at' have defaults
    )
    try:
        db.session.add(new_prompt)
        db.session.commit()
        # Return the new prompt details *and* its modification code
        response_data = new_prompt.to_dict()
        response_data['modification_code'] = modification_code # Add code only for the creator
        return jsonify(response_data), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding prompt: {e}") # Log the error
        return jsonify({"error": "Failed to add prompt to database"}), 500


@app.route('/prompts/<string:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update an existing prompt using its modification code."""
    prompt = Prompt.query.get(prompt_id)
    if not prompt:
        return jsonify({"error": "Prompt not found"}), 404

    if prompt.read_only:
         return jsonify({"error": "Cannot modify a read-only prompt"}), 403

    if not request.json:
        return jsonify({"error": "Missing request body"}), 400

    provided_code = request.headers.get('X-Modification-Code')
    if not provided_code or provided_code != prompt.modification_code:
         return jsonify({"error": "Invalid or missing modification code"}), 403

    updated = False
    if 'title' in request.json:
        new_title = request.json['title'].strip()
        if new_title and new_title != prompt.title:
            prompt.title = new_title
            updated = True
    if 'text' in request.json:
        new_text = request.json['text'].strip()
        if new_text and new_text != prompt.text:
            prompt.text = new_text
            updated = True

    if updated:
        try:
            db.session.commit()
            return jsonify(prompt.to_dict())
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating prompt {prompt_id}: {e}")
            return jsonify({"error": "Failed to update prompt in database"}), 500
    else:
        # Nothing was actually updated
        return jsonify(prompt.to_dict())


@app.route('/prompts/<string:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt using its modification code."""
    prompt = Prompt.query.get(prompt_id)
    if not prompt:
        return jsonify({"error": "Prompt not found"}), 404

    if prompt.read_only:
         return jsonify({"error": "Cannot delete a read-only prompt"}), 403

    provided_code = request.headers.get('X-Modification-Code')
    if not provided_code or provided_code != prompt.modification_code:
         return jsonify({"error": "Invalid or missing modification code"}), 403

    try:
        db.session.delete(prompt)
        db.session.commit()
        return '', 204 # No Content
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting prompt {prompt_id}: {e}")
        return jsonify({"error": "Failed to delete prompt from database"}), 500


# Basic root route for testing
@app.route('/')
def index():
    # Simple check to see if DB connection works (optional)
    try:
        # Wrap the raw SQL string in text()
        db.session.execute(text('SELECT 1'))
        return "Prompt Vault API is running! Database connection successful."
    except Exception as e:
        # Log the actual error for debugging
        app.logger.error(f"Database connection check failed: {e}")
        # Return a more generic message to the user
        return "Prompt Vault API is running! Database connection failed.", 500

# --- Create Database Tables ---
# This function will create the tables based on your models if they don't exist.
# It needs the application context.
def create_tables():
    with app.app_context():
        print("Creating database tables if they don't exist...")
        db.create_all()
        print("Tables created (or already exist).")

if __name__ == '__main__':
    create_tables() # Create tables before running the app
    # Port 5328 is often used for development servers by convention
    app.run(debug=True, port=5328)