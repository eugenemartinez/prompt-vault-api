from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# In-memory storage for prompts (replace with database later)
prompts_db = {}

# Helper function to generate a unique modification code
def generate_modification_code():
    return str(uuid.uuid4())[:8] # Simple 8-character code

@app.route('/prompts', methods=['GET'])
def get_prompts():
    """Retrieve all prompts."""
    return jsonify(list(prompts_db.values()))

@app.route('/prompts/<string:prompt_id>', methods=['GET'])
def get_prompt(prompt_id):
    """Retrieve a specific prompt by ID."""
    prompt = prompts_db.get(prompt_id)
    if prompt:
        return jsonify(prompt)
    else:
        return jsonify({"error": "Prompt not found"}), 404

@app.route('/prompts', methods=['POST'])
def add_prompt():
    """Add a new prompt."""
    if not request.json or not 'title' in request.json or not 'text' in request.json:
        return jsonify({"error": "Missing title or text in request body"}), 400

    prompt_id = str(uuid.uuid4())
    modification_code = generate_modification_code()
    new_prompt = {
        "id": prompt_id,
        "title": request.json['title'],
        "text": request.json['text'],
        "modification_code": modification_code,
        # Add other fields like 'read_only', 'created_at' later
    }
    prompts_db[prompt_id] = new_prompt
    # Return the new prompt *and* its modification code
    return jsonify({"prompt": new_prompt, "modification_code": modification_code}), 201

@app.route('/prompts/<string:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update an existing prompt using its modification code."""
    prompt = prompts_db.get(prompt_id)
    if not prompt:
        return jsonify({"error": "Prompt not found"}), 404

    if not request.json:
        return jsonify({"error": "Missing request body"}), 400

    # Check for modification code in request headers or body (choose one)
    # Using headers is common for auth-like tokens
    provided_code = request.headers.get('X-Modification-Code')
    # Alternatively, check in JSON body: provided_code = request.json.get('modification_code')

    if not provided_code or provided_code != prompt.get('modification_code'):
         return jsonify({"error": "Invalid or missing modification code"}), 403 # Forbidden

    # Update allowed fields
    if 'title' in request.json:
        prompt['title'] = request.json['title']
    if 'text' in request.json:
        prompt['text'] = request.json['text']

    prompts_db[prompt_id] = prompt
    return jsonify(prompt)

@app.route('/prompts/<string:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt using its modification code."""
    prompt = prompts_db.get(prompt_id)
    if not prompt:
        return jsonify({"error": "Prompt not found"}), 404

    # Check for modification code (similar to PUT)
    provided_code = request.headers.get('X-Modification-Code')
    # Alternatively, check in JSON body: provided_code = request.json.get('modification_code')

    if not provided_code or provided_code != prompt.get('modification_code'):
         return jsonify({"error": "Invalid or missing modification code"}), 403 # Forbidden

    del prompts_db[prompt_id]
    return '', 204 # No Content

# Basic root route for testing
@app.route('/')
def index():
    return "Prompt Vault API is running!"

if __name__ == '__main__':
    # Port 5328 is often used for development servers by convention
    app.run(debug=True, port=5328)