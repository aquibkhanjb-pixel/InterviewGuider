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

try:
    from sentence_transformers import SentenceTransformer
    SentenceTransformer('all-MiniLM-L6-v2')
    print("sentence-transformers model cached OK")
except Exception as e:
    print(f"sentence-transformers model skipped (will load at runtime): {e}")
