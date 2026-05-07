import math
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SemanticConfidenceScorer:
    """
    Semantic confidence scoring using sentence-transformers.
    Computes cosine similarity between a topic phrase and the text context
    around each keyword mention — much more robust than keyword-count heuristics.

    Lazy-loaded: the model is only downloaded/initialised on first use.
    Falls back to None if the library is unavailable.
    """

    _model = None
    _model_tried: bool = False
    _topic_cache: Dict[str, list] = {}

    @classmethod
    def _get_model(cls):
        if cls._model_tried:
            return cls._model
        cls._model_tried = True
        try:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SemanticConfidenceScorer: model loaded (all-MiniLM-L6-v2)")
        except Exception as exc:
            logger.warning(f"SemanticConfidenceScorer unavailable — falling back to keyword method: {exc}")
            cls._model = None
        return cls._model

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
                cls._topic_cache[query] = model.encode(query)
            topic_emb = np.asarray(cls._topic_cache[query])

            ctx_embs = model.encode(contexts[:6])
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
    Annotates each topic with TF-IDF-derived fields and re-sorts using a
    blended key so that both universally important topics AND company-specific
    topics rank highly.

    Fields added to each topic:
      idf               — log(N / df): how concentrated vs. spread this topic is
      tfidf_score       — weighted_frequency × idf (raw signal)
      discriminative_score — normalised 0-1 (how company-specific this topic is)

    Sort key = 0.6 × freq_rank + 0.4 × disc_rank
    This keeps "appears in every interview" topics near the top while still
    boosting topics that are uniquely concentrated in this company's process.

    NOTE: When cross-company corpora are available, replace the within-corpus
    IDF here with a global IDF precomputed across all companies so the
    discriminative_score truly reflects company-specific signal.
    """
    if not topic_insights or n_experiences < 2:
        for data in topic_insights.values():
            data.setdefault('idf', 0.0)
            data.setdefault('tfidf_score', 0.0)
            data.setdefault('discriminative_score', 0.5)
        return topic_insights

    # Compute raw IDF and TF-IDF
    for data in topic_insights.values():
        df = max(data.get('mentions_count', 1), 1)
        idf = math.log(n_experiences / df)
        data['idf'] = round(idf, 3)
        data['tfidf_score'] = round(data.get('weighted_frequency', 0) * idf, 3)

    # Normalise discriminative_score to [0, 1]
    max_tfidf = max((d['tfidf_score'] for d in topic_insights.values()), default=1) or 1
    for data in topic_insights.values():
        data['discriminative_score'] = round(data['tfidf_score'] / max_tfidf, 3)

    # Build blended sort key: rank by frequency (primary) boosted by discriminative signal
    items = list(topic_insights.items())
    n = len(items)

    freq_order = sorted(range(n), key=lambda i: items[i][1].get('weighted_frequency', 0), reverse=True)
    disc_order = sorted(range(n), key=lambda i: items[i][1].get('discriminative_score', 0), reverse=True)

    freq_rank = [0] * n
    disc_rank = [0] * n
    for rank, idx in enumerate(freq_order):
        freq_rank[idx] = rank
    for rank, idx in enumerate(disc_order):
        disc_rank[idx] = rank

    blended = sorted(range(n), key=lambda i: 0.6 * freq_rank[i] + 0.4 * disc_rank[i])
    return dict(items[i] for i in blended)
