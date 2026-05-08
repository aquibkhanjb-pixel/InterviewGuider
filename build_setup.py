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
    from fastembed import TextEmbedding
    # Trigger model download + ONNX cache at build time so first request is fast
    list(TextEmbedding("BAAI/bge-small-en-v1.5").embed(["warmup"]))
    print("fastembed model cached OK")
except Exception as e:
    print(f"fastembed model skipped (will download at runtime): {e}")
