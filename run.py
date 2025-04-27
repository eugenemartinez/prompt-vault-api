from app import create_app

app = create_app()

if __name__ == '__main__':
    # Use Flask's built-in server for development
    # The host='0.0.0.0' makes it accessible on your network
    # Debug=True enables auto-reloading and debugger
    # Port 5328 as before
    app.run(host='0.0.0.0', port=5328, debug=True)