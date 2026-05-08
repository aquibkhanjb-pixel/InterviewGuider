"""
Insights routes — serves ML-augmented topic insights on demand.
Calls CompanyInsightsGenerator directly from DB experiences so TF-IDF,
discriminative_score, and semantic_confidence are always included.
"""

from flask import Blueprint, request, jsonify
from database.connection import db_manager
from database.models import Company, InterviewExperience
import logging
from datetime import datetime

insights_bp = Blueprint('insights', __name__)
logger = logging.getLogger(__name__)


def _normalize(name: str) -> str:
    """Mirror of analysis.py normalization so lookups are always consistent."""
    if not name:
        return name
    return ' '.join(
        w if (w.isupper() and len(w) <= 5) else w.capitalize()
        for w in name.strip().split()
    )

# Module-level singleton so AdvancedTopicExtractor (and its pre-compiled regex
# patterns) is built once per process, not once per request.
_generator = None

def _get_generator():
    global _generator
    if _generator is None:
        from analysis.insights_generator import CompanyInsightsGenerator
        _generator = CompanyInsightsGenerator()
    return _generator

# Simple in-process cache: (company_name, experience_count, last_scraped) -> response dict
# Cleared automatically when the process restarts (e.g. after a new deploy).
_insights_cache: dict = {}


def _load_experiences(session, company) -> list:
    """
    Convert InterviewExperience ORM rows to the dict format that
    CompanyInsightsGenerator.generate_comprehensive_insights() expects.
    """
    rows = (
        session.query(InterviewExperience)
        .filter(InterviewExperience.company_id == company.id)
        .order_by(InterviewExperience.experience_date.desc())
        .all()
    )
    result = []
    for exp in rows:
        result.append({
            'id':              exp.id,
            'title':           exp.title or '',
            'content':         exp.content or '',
            'experience_date': exp.experience_date or datetime.utcnow(),
            'time_weight':     exp.time_weight if exp.time_weight is not None else 1.0,
            'source_platform': exp.source_platform,
            'outcome': (
                'offer'    if exp.success is True  else
                'rejected' if exp.success is False else
                'unknown'
            ),
        })
    return result


@insights_bp.route('/<company_name>', methods=['GET'])
def get_company_insights(company_name):
    """
    Get ML-augmented insights for a company.
    Runs CompanyInsightsGenerator on the stored experiences so every topic
    includes tfidf_score, discriminative_score, idf, and semantic_confidence.
    """
    try:
        company_name = _normalize(company_name)
        logger.info(f"Generating insights for {company_name}")

        with db_manager.get_session() as session:
            company = session.query(Company).filter(
                Company.name.ilike(company_name)
            ).first()

            if not company:
                return jsonify({'error': 'Company not found', 'company': company_name}), 404

            total_experiences = (
                session.query(InterviewExperience)
                .filter(InterviewExperience.company_id == company.id)
                .count()
            )

            if total_experiences == 0:
                return jsonify({
                    'company':  company_name,
                    'insights': {},
                    'analysis_metadata': {
                        'sample_size':          0,
                        'last_updated':         datetime.utcnow().isoformat(),
                        'data_quality_score':   0.0,
                        'confidence_threshold': 0.7,
                        'ml_scoring':           False,
                    },
                    'status':  'no_data',
                    'message': f'No interview experiences found for {company_name}. Please run data collection first.',
                })

            experiences = _load_experiences(session, company)

            latest = (
                session.query(InterviewExperience)
                .filter(InterviewExperience.company_id == company.id)
                .order_by(InterviewExperience.scraped_at.desc())
                .first()
            )
            last_updated = (
                latest.scraped_at.isoformat()
                if latest and latest.scraped_at
                else datetime.utcnow().isoformat()
            )

        # Run ML-augmented insights generation outside the DB session.
        # Reuse the singleton generator so compiled regex patterns are not rebuilt.
        cache_key = (company_name, total_experiences, last_updated)
        if cache_key in _insights_cache:
            logger.info(f"Returning cached insights for {company_name}")
            return jsonify(_insights_cache[cache_key])

        gen = _get_generator()
        full = gen.generate_comprehensive_insights(company_name, experiences)

        if full.get('status') == 'insufficient_data':
            return jsonify({
                'company':  company_name,
                'insights': {},
                'analysis_metadata': {
                    'sample_size':          total_experiences,
                    'last_updated':         last_updated,
                    'data_quality_score':   30.0,
                    'confidence_threshold': 0.7,
                    'ml_scoring':           False,
                },
                'status':  'insufficient_data',
                'message': full.get('message', 'Not enough experiences for analysis.'),
            })

        detailed_topics = (
            full.get('topic_insights', {})
                .get('detailed_topics', {})
        )

        # Detect whether the semantic model was active (any topic has a non-null semantic_confidence)
        ml_active = any(
            t.get('semantic_confidence') is not None
            for t in detailed_topics.values()
        )

        quality = full.get('data_quality', {})
        response_data = {
            'company':  company_name,
            'insights': detailed_topics,
            'top_5_topics':         full.get('topic_insights', {}).get('top_5_topics', []),
            'high_priority_topics': full.get('topic_insights', {}).get('high_priority_topics', []),
            'analysis_metadata': {
                'sample_size':          total_experiences,
                'last_updated':         last_updated,
                'data_quality_score':   round(quality.get('quality_score', 0.5) * 100, 1),
                'confidence_threshold': 0.7,
                'total_topics':         len(detailed_topics),
                'ml_scoring':           ml_active,
            },
            'difficulty_analysis':         full.get('difficulty_analysis', {}),
            'interview_process_insights':  full.get('interview_process_insights', {}),
            'success_factors':             full.get('success_factors', {}),
            'study_recommendations':       full.get('study_recommendations', {}),
            'status':  'live_data',
            'message': f'ML-augmented insights from {total_experiences} experiences',
        }
        _insights_cache[cache_key] = response_data
        return jsonify(response_data)

    except Exception as e:
        import traceback
        logger.error(f"Error getting insights for {company_name}: {e}", exc_info=True)
        return jsonify({
            'error':     str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc(),
            'company':   company_name,
            'message':   'Insights temporarily unavailable',
        })  # 200 so WebFetch can read the body


@insights_bp.route('/<company_name>/recommendations', methods=['GET'])
def get_recommendations(company_name):
    """Get study recommendations derived from the full ML insights."""
    try:
        company_name = _normalize(company_name)
        with db_manager.get_session() as session:
            company = session.query(Company).filter(
                Company.name.ilike(company_name)
            ).first()

            if not company:
                return jsonify({'error': 'Company not found', 'company': company_name}), 404

            total_experiences = (
                session.query(InterviewExperience)
                .filter(InterviewExperience.company_id == company.id)
                .count()
            )

            if total_experiences == 0:
                return jsonify({
                    'company': company_name,
                    'recommendations': {'high_priority': [], 'medium_priority': [], 'low_priority': []},
                    'study_plan': {'estimated_weeks': 0, 'hours_per_week': 0, 'focus_areas': []},
                    'status':  'no_data',
                    'message': f'No data available for {company_name}. Please run data collection first.',
                })

            experiences = _load_experiences(session, company)

        gen = _get_generator()
        full = gen.generate_comprehensive_insights(company_name, experiences)

        study_recs  = full.get('study_recommendations', {})
        prep        = full.get('preparation_strategy', {})
        success_f   = full.get('success_factors', {})
        topic_dist  = (
            full.get('topic_insights', {})
                .get('topic_distribution', {})
        )

        return jsonify({
            'company':         company_name,
            'recommendations': study_recs,
            'preparation_strategy': prep,
            'success_factors': success_f,
            'topic_distribution': topic_dist,
            'study_plan': {
                'estimated_weeks':  prep.get('preparation_timeline', '4-6 weeks'),
                'focus_areas':      prep.get('key_recommendations', []),
                'difficulty_focus': prep.get('difficulty_focus', 'unknown'),
            },
            'analysis_insights': {
                'total_experiences_analyzed': total_experiences,
                'topic_coverage': len(
                    full.get('topic_insights', {}).get('detailed_topics', {})
                ),
            },
            'status':  'data_driven',
            'message': f'Recommendations based on {total_experiences} experiences',
        })

    except Exception as e:
        logger.error(f"Error getting recommendations for {company_name}: {e}", exc_info=True)
        return jsonify({'error': str(e), 'company': company_name}), 500
