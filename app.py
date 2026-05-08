"""
Entry point for Render deployment.
This file creates the Flask application instance for production deployment.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the create_app function from main.py
from main import create_app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
