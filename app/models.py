import uuid
import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Prompt(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(150), nullable=False)
    text = db.Column(db.Text, nullable=False)
    username = db.Column(db.String(80), nullable=True)
    response = db.Column(db.Text, nullable=True)
    modification_code = db.Column(db.String(8), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    read_only = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "username": self.username, # Include username
            "response": self.response, # Include response
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_only": self.read_only
            # Modification code is intentionally NOT returned here for security
        }