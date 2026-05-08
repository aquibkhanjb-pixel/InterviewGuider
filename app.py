"""
Entry point for Render deployment.
This file creates the Flask application instance for production deployment.
"""
import os
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the create_app function from main.py
from main import create_app

# Create the application instance
app = create_app()

def _preload_ml_models():
    """
    Warm the sentence-transformers model in a background thread so the
    first user request doesn't have to wait 60+ seconds for it to load.
    The model was already downloaded during the build step (render.yaml),
    so this is just a fast read from disk into memory.
    """
    try:
        from analysis.ml_scorer import SemanticConfidenceScorer
        SemanticConfidenceScorer._get_model()
        print("ML model pre-loaded successfully")
    except Exception as e:
        print(f"ML model pre-load skipped: {e}")

# Start pre-loading immediately; daemon=True means it won't block shutdown
threading.Thread(target=_preload_ml_models, daemon=True).start()

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
