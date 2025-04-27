from flask import Blueprint, request, jsonify, current_app # Import current_app
from sqlalchemy import text, func, desc, asc
from .models import db, Prompt
from .utils import generate_modification_code
from . import limiter

bp = Blueprint('main', __name__)

@bp.route('/prompts', methods=['GET'])
def get_prompts():
    try:
        # Start with a base query
        query = Prompt.query

        # --- Filtering ---
        filter_title = request.args.get('filter_title', type=str)
        if filter_title:
            # Use ilike for case-insensitive partial matching
            query = query.filter(Prompt.title.ilike(f"%{filter_title}%"))

        # Add more filters here based on request.args if needed (e.g., filter by text)

        # --- Sorting ---
        sort_by = request.args.get('sort', default='created_at', type=str)
        sort_order = request.args.get('order', default='desc', type=str).lower()

        sort_column = getattr(Prompt, sort_by, Prompt.created_at) # Default to created_at if invalid column
        if sort_order == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            # Default to descending order
            query = query.order_by(desc(sort_column))

        # Execute the query
        all_prompts = query.all()
        return jsonify([prompt.to_dict() for prompt in all_prompts])
    except AttributeError:
        return jsonify({"error": f"Invalid sort column specified: {sort_by}"}), 400
    except Exception as e:
        # Use current_app.logger
        current_app.logger.error(f"Error getting prompts: {e}", exc_info=True) # Add exc_info for traceback
        return jsonify({"error": "Failed to retrieve prompts"}), 500

@bp.route('/prompts/<string:prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    try:
        # Use db.session.get for primary key lookup (SQLAlchemy 2.0 style)
        prompt = db.session.get(Prompt, prompt_id)
        if prompt:
            return jsonify(prompt.to_dict())
        else:
            return jsonify({"error": "Prompt not found"}), 404
    except Exception as e:
        # Use current_app.logger
        current_app.logger.error(f"Error getting prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve prompt"}), 500

@bp.route('/prompts', methods=['POST'])
@limiter.limit("20 per day")
def add_prompt():
    if not request.json or not 'title' in request.json or not 'text' in request.json:
        return jsonify({"error": "Missing title or text in request body"}), 400

    title = request.json['title'].strip()
    text = request.json['text'].strip()
    # Get optional username, default to None if not provided or empty
    username = request.json.get('username', '').strip() or None

    if not title or not text:
        return jsonify({"error": "Title and text cannot be empty"}), 400

    MAX_TITLE_LENGTH = 150
    if len(title) > MAX_TITLE_LENGTH:
         return jsonify({"error": f"Title cannot exceed {MAX_TITLE_LENGTH} characters"}), 400

    # Optional: Add username length validation if desired
    MAX_USERNAME_LENGTH = 80
    if username and len(username) > MAX_USERNAME_LENGTH:
        return jsonify({"error": f"Username cannot exceed {MAX_USERNAME_LENGTH} characters"}), 400

    try:
        modification_code = generate_modification_code()
        new_prompt = Prompt(
            title=title,
            text=text,
            username=username, # Save username
            modification_code=modification_code
            # response is initially null
        )
        db.session.add(new_prompt)
        db.session.commit()
        response_data = new_prompt.to_dict()
        response_data['modification_code'] = modification_code
        return jsonify(response_data), 201
    except Exception as e:
        db.session.rollback()
        # Use current_app.logger
        current_app.logger.error(f"Error adding prompt: {e}", exc_info=True)
        return jsonify({"error": "Failed to add prompt"}), 500


@bp.route('/prompts/<string:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    # Define max lengths
    MAX_TITLE_LENGTH = 150
    MAX_RESPONSE_LENGTH = 10000 # Define max length for response

    try:
        prompt = db.session.get(Prompt, prompt_id)
        if not prompt:
            return jsonify({"error": "Prompt not found"}), 404

        if prompt.read_only:
            return jsonify({"error": "Cannot modify a read-only prompt"}), 403

        provided_code = request.headers.get('X-Modification-Code')
        if not provided_code or provided_code != prompt.modification_code:
            return jsonify({"error": "Invalid or missing modification code"}), 403

        if not request.json:
            return jsonify({"error": "Missing request body"}), 400

        updated = False
        # Update title
        if 'title' in request.json:
            new_title = request.json['title'].strip()
            if new_title and new_title != prompt.title:
                 if len(new_title) > MAX_TITLE_LENGTH:
                     return jsonify({"error": f"Title cannot exceed {MAX_TITLE_LENGTH} characters"}), 400
                 prompt.title = new_title
                 updated = True
        # Update text
        if 'text' in request.json:
            new_text = request.json['text'].strip()
            if new_text and new_text != prompt.text:
                prompt.text = new_text
                updated = True
        # Update response
        if 'response' in request.json:
            new_response = request.json['response']
            if new_response is None or isinstance(new_response, str):
                 processed_response = new_response.strip() if isinstance(new_response, str) else new_response

                 # Use the MAX_RESPONSE_LENGTH constant here
                 if processed_response is not None and len(processed_response) > MAX_RESPONSE_LENGTH:
                     # Use f-string for the error message
                     return jsonify({"error": f"Response cannot exceed {MAX_RESPONSE_LENGTH} characters"}), 400

                 if processed_response != prompt.response:
                     prompt.response = processed_response
                     updated = True
            else:
                 return jsonify({"error": "Invalid type for response field, must be string or null"}), 400

        # Note: We are NOT allowing username to be updated via PUT

        if updated:
            db.session.commit()
        return jsonify(prompt.to_dict())

    except Exception as e:
        db.session.rollback()
        # Use current_app.logger
        current_app.logger.error(f"Error updating prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update prompt"}), 500


@bp.route('/prompts/<string:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    try:
        prompt = db.session.get(Prompt, prompt_id)
        if not prompt:
            return jsonify({"error": "Prompt not found"}), 404

        if prompt.read_only:
            return jsonify({"error": "Cannot delete a read-only prompt"}), 403

        provided_code = request.headers.get('X-Modification-Code')
        if not provided_code or provided_code != prompt.modification_code:
            return jsonify({"error": "Invalid or missing modification code"}), 403

        db.session.delete(prompt)
        db.session.commit()
        return '', 204 # No Content
    except Exception as e:
        db.session.rollback()
        # Use current_app.logger
        current_app.logger.error(f"Error deleting prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete prompt"}), 500

# --- Add Random Prompt Endpoint ---
@bp.route('/prompts/random', methods=['GET'])
def get_random_prompt():
    """Retrieve a single random prompt."""
    try:
        # Use func.random() for PostgreSQL (or func.rand() for MySQL, RANDOM() for SQLite)
        # Order by random and take the first one
        random_prompt = Prompt.query.order_by(func.random()).first()
        if random_prompt:
            return jsonify(random_prompt.to_dict())
        else:
            # Should only happen if the database is empty
            return jsonify({"error": "No prompts available"}), 404
    except Exception as e:
        # Use current_app.logger
        current_app.logger.error(f"Error getting random prompt: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve random prompt"}), 500

# --- Add Batch Prompt Endpoint ---
@bp.route('/prompts/batch', methods=['POST'])
def get_prompts_batch():
    """
    Retrieve multiple prompts based on a list of IDs provided in the request body.
    Expects JSON body: {"ids": ["id1", "id2", ...]}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    prompt_ids = data.get('ids')

    if not prompt_ids or not isinstance(prompt_ids, list):
        return jsonify({"error": "Missing or invalid 'ids' list in request body"}), 400

    if not prompt_ids: # Handle empty list case explicitly
        return jsonify([]) # Return empty list if no IDs provided

    try:
        # Fetch prompts where the ID is in the provided list
        # The .in_() operator is efficient for this
        found_prompts = Prompt.query.filter(Prompt.id.in_(prompt_ids)).all()

        # Optional: Maintain order if needed (more complex)
        # If you need the results in the same order as the input 'ids',
        # you might need to query individually or re-order in Python.
        # For now, the database order is sufficient.

        return jsonify([prompt.to_dict() for prompt in found_prompts])

    except Exception as e:
        # Use current_app.logger
        current_app.logger.error(f"Error getting prompts batch: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve prompts batch"}), 500