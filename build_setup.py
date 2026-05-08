"""
Render build-time setup: download NLTK data and sentence-transformers model
so they are cached and available instantly at runtime.
"""
import nltk

for pkg in ['punkt', 'punkt_tab', 'stopwords']:
    try:
        nltk.download(pkg, quiet=True)
        print(f"NLTK '{pkg}' ready")
    except Exception as e:
        print(f"NLTK '{pkg}' skipped: {e}")

# sentence-transformers removed from requirements — exceeds Render free tier 512MB RAM.
# SemanticConfidenceScorer handles ImportError gracefully (returns None for all topics).
