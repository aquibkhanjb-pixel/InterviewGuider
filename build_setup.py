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

# fastembed model pre-caching skipped — semantic scoring disabled on free tier.
# To enable: add fastembed>=0.3.0 to requirements.txt,
# set ENABLE_SEMANTIC_SCORING=true in Render env vars,
# and uncomment:
#   from fastembed import TextEmbedding
#   list(TextEmbedding("BAAI/bge-small-en-v1.5").embed(["warmup"]))
