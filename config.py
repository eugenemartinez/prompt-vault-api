import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-change-this' # Add a secret key for Flask sessions/security
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False # Set to True in development for debugging SQL

    # Database URL Logic
    NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL") # Expects postgresql+psycopg2://
    DATABASE_URL = os.getenv("DATABASE_URL")           # Expects postgresql://

    # Use NEON_DATABASE_URL if available (Vercel), otherwise use DATABASE_URL (local)
    SQLALCHEMY_DATABASE_URI = NEON_DATABASE_URL or DATABASE_URL

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("Database connection string not found in environment variables (NEON_DATABASE_URL or DATABASE_URL).")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True # Show SQL queries in development

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Add any production-specific settings here

# Select configuration based on environment (optional, defaults to Development for now)
# You could use an environment variable like FLASK_ENV=production later
config = DevelopmentConfig()