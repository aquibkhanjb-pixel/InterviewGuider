import math
import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SemanticConfidenceScorer:
    """
    Semantic confidence scoring via fastembed (ONNX Runtime, ~80MB RAM).
    The model loads in a background thread so it never blocks request handlers.
    Requests served before the model is ready simply get semantic_confidence=None
    and proceed normally. Once loaded, all subsequent requests get scores.
    """

    _model = None
    _model_ready: bool = False   # True once background load succeeds or fails
    _load_started: bool = False  # True once the background thread has been kicked off
    _load_lock = threading.Lock()
    _topic_cache: Dict[str, list] = {}

    @classmethod
    def _load_model_background(cls):
        """Download + warm up the fastembed model in a daemon thread."""
        try:
            from fastembed import TextEmbedding
            model = TextEmbedding("BAAI/bge-small-en-v1.5")
            list(model.embed(["warmup"]))   # triggers actual ONNX session creation
            cls._model = model
            logger.info("SemanticConfidenceScorer: fastembed model ready (BAAI/bge-small-en-v1.5)")
        except Exception as exc:
            logger.warning(f"SemanticConfidenceScorer unavailable: {exc}")
            cls._model = None
        finally:
            cls._model_ready = True

    @classmethod
    def _get_model(cls):
        # Kick off background load on first call (non-blocking)
        with cls._load_lock:
            if not cls._load_started:
                cls._load_started = True
                t = threading.Thread(target=cls._load_model_background, daemon=True)
                t.start()
        # Return whatever state we're in — None until background load finishes
        return cls._model if cls._model_ready else None

    @classmethod
    def score(cls, topic_name: str, topic_keywords: List[str], text: str) -> Optional[float]:
        """
        Returns max cosine similarity (0–1) between the topic and its surrounding
        context windows in `text`, or None if the model is not available.
        """
        model = cls._get_model()
        if model is None or not text:
            return None

        try:
            import numpy as np
            from numpy.linalg import norm

            contexts: List[str] = []
            text_lower = text.lower()
            for kw in topic_keywords[:4]:
                kw_lower = kw.lower()
                pos = 0
                while len(contexts) < 6:
                    idx = text_lower.find(kw_lower, pos)
                    if idx == -1:
                        break
                    start = max(0, idx - 150)
                    end = min(len(text), idx + len(kw) + 150)
                    contexts.append(text[start:end])
                    pos = idx + 1

            if not contexts:
                return None

            query = f"interview question about {topic_name.replace('_', ' ')}"
            if query not in cls._topic_cache:
                # fastembed.embed() returns a generator — consume once and cache
                cls._topic_cache[query] = list(model.embed([query]))[0]
            topic_emb = np.asarray(cls._topic_cache[query])

            ctx_embs = list(model.embed(contexts[:6]))
            sims = [
                float(np.dot(topic_emb, ce) / (norm(topic_emb) * norm(ce) + 1e-10))
                for ce in ctx_embs
            ]
            return round(max(sims), 3)

        except Exception as exc:
            logger.debug(f"Semantic scoring error for '{topic_name}': {exc}")
            return None


def tfidf_rerank(topic_insights: Dict, n_experiences: int) -> Dict:
    """
    Re-ranks topics using consistency-boosted frequency scoring.

    Within a single company's corpus, a topic appearing in MORE experiences is
    MORE important — high document frequency is the signal, not noise. We
    therefore use consistency_score = df / n_experiences which BOOSTS topics
    that appear reliably across interviews instead of penalising them.

    Fields added to each topic:
      consistency_score  — df / n_experiences (0–1): how reliably this topic appears
      frequency_score    — weighted_frequency × consistency_score
      discriminative_score — alias for consistency_score (kept for frontend compat)

    IDF (log N/df) belongs at the cross-company level, not within one company.
    When experiences from multiple companies are available, replace
    consistency_score with a global IDF so topics unique to this company are
    boosted over universally common ones.
    """
    if not topic_insights or n_experiences < 2:
        for data in topic_insights.values():
            data.setdefault('consistency_score', 1.0)
            data.setdefault('frequency_score', 0.0)
            data.setdefault('discriminative_score', 1.0)
        return topic_insights

    for data in topic_insights.values():
        df = max(data.get('mentions_count', 1), 1)
        consistency = round(min(df / n_experiences, 1.0), 3)
        data['consistency_score'] = consistency
        data['frequency_score'] = round(data.get('weighted_frequency', 0) * consistency, 3)
        data['discriminative_score'] = consistency  # frontend compat

    items = list(topic_insights.items())
    n = len(items)

    freq_order = sorted(range(n), key=lambda i: items[i][1].get('weighted_frequency', 0), reverse=True)
    cons_order = sorted(range(n), key=lambda i: items[i][1].get('consistency_score', 0), reverse=True)

    freq_rank = [0] * n
    cons_rank = [0] * n
    for rank, idx in enumerate(freq_order):
        freq_rank[idx] = rank
    for rank, idx in enumerate(cons_order):
        cons_rank[idx] = rank

    blended = sorted(range(n), key=lambda i: 0.6 * freq_rank[i] + 0.4 * cons_rank[i])
    return dict(items[i] for i in blended)
