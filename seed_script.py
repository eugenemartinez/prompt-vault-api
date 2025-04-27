import json
import os
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

# --- Adjust path to import config and models ---
# Get the absolute path of the project root (one level up from 'server')
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_root)) # Add the directory containing 'server' to path
sys.path.insert(0, project_root) # Add the 'server' directory itself to path

try:
    from config import config # Import the config object directly
    from app.models import Prompt, db # Import Prompt model (db object needed for table metadata)
except ImportError as e:
    print(f"Error importing modules. Make sure config.py and app/models.py exist and paths are correct: {e}")
    sys.exit(1)
# --- End Path Adjustment ---

# --- Database Setup ---
DATABASE_URI = config.SQLALCHEMY_DATABASE_URI
if not DATABASE_URI:
    print("Error: SQLALCHEMY_DATABASE_URI not found in config.")
    sys.exit(1)

try:
    engine = create_engine(DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Test connection
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection successful.")
except OperationalError as e:
    print(f"Database connection failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during database setup: {e}")
    sys.exit(1)
# --- End Database Setup ---

# --- Seeding Logic ---
def generate_unique_code(session):
    """Generates a unique 8-char code using the provided session."""
    while True:
        code = str(uuid.uuid4())[:8]
        # Check uniqueness using the provided session
        if not session.query(Prompt).filter_by(modification_code=code).first():
            return code

def seed_database():
    session = SessionLocal()
    try:
        # Load data from JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'seed_data.json')
        with open(json_path, 'r') as f:
            core_prompts_data = json.load(f)

        existing_titles = {prompt.title for prompt in session.query(Prompt).filter_by(read_only=True).all()}
        prompts_added_count = 0

        for data in core_prompts_data:
            if data["title"] not in existing_titles:
                mod_code = generate_unique_code(session)

                new_prompt = Prompt(
                    title=data["title"],
                    text=data["text"],
                    username=data.get("username"),
                    modification_code=mod_code,
                    read_only=True # Set the read-only flag
                )
                session.add(new_prompt)
                existing_titles.add(data["title"]) # Avoid duplicates within this run
                prompts_added_count += 1
                print(f"Adding: {data['title']}")
            else:
                print(f"Skipping (already exists): {data['title']}")

        if prompts_added_count > 0:
            session.commit()
            print(f"\nSuccessfully seeded {prompts_added_count} new read-only prompts.")
        else:
            print("\nNo new read-only prompts to seed.")

    except FileNotFoundError:
        print(f"Error: seed_data.json not found at {json_path}")
        session.rollback()
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from seed_data.json.")
        session.rollback()
    except IntegrityError as e:
         print(f"Database integrity error during seeding (maybe a modification code collision?): {e}")
         session.rollback()
    except Exception as e:
        print(f"An error occurred during seeding: {e}")
        session.rollback()
    finally:
        session.close()
        print("Database session closed.")
# --- End Seeding Logic ---

if __name__ == "__main__":
    print("Starting database seeding process...")
    # Ensure tables exist before seeding (optional but good practice)
    try:
         print("Ensuring tables exist...")
         # This uses the metadata from the imported db object
         db.metadata.create_all(bind=engine)
         print("Tables checked/created.")
    except Exception as e:
         print(f"Error checking/creating tables: {e}")
         # Decide if you want to exit or continue
         # sys.exit(1)

    seed_database()
    print("Seeding process finished.")