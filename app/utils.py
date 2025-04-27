import uuid
from .models import db, Prompt # Import db and Prompt from models

def generate_modification_code():
    """Generates a unique 8-character modification code."""
    while True:
        code = str(uuid.uuid4())[:8]
        # Use db.session within the application context (routes will have it)
        if not Prompt.query.filter_by(modification_code=code).first():
            return code