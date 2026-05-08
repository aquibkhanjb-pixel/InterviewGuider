"""
Analysis routes - async background scraping + polling.
Jobs are stored in the database so any gunicorn worker can read them.
"""

import json
import threading
import uuid
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from database.connection import db_manager
from database.models import Company, InterviewExperience, AnalysisJob

analysis_bp = Blueprint('analysis', __name__)
logger = logging.getLogger(__name__)


def _normalize_company_name(name: str) -> str:
    """
    Canonical company name: strip whitespace, title-case each word.
    Short ALL-CAPS words (≤ 5 chars) are kept as-is so "TCS" stays "TCS"
    rather than "Tcs", but "AMAZON" (6 chars) becomes "Amazon".
    """
    if not name:
        return name
    return ' '.join(
        w if (w.isupper() and len(w) <= 5) else w.capitalize()
        for w in name.strip().split()
    )


def _set_job(job_id: str, **kwargs):
    """Upsert job fields in the database."""
    with db_manager.get_session() as session:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            job = AnalysisJob(id=job_id)
            session.add(job)
        for key, value in kwargs.items():
            if key == 'result':
                job.result_json = json.dumps(value)
            elif key == 'started_at' and isinstance(value, str):
                job.started_at = datetime.fromisoformat(value)
            elif key == 'finished_at' and isinstance(value, str):
                job.finished_at = datetime.fromisoformat(value)
            elif hasattr(job, key):
                setattr(job, key, value)
        session.commit()


def _get_job(job_id: str) -> dict:
    """Read job from database. Returns {} if not found."""
    with db_manager.get_session() as session:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            return {}
        return {
            'status':      job.status,
            'company':     job.company,
            'error':       job.error,
            'started_at':  job.started_at.isoformat() if job.started_at else None,
            'finished_at': job.finished_at.isoformat() if job.finished_at else None,
            'result':      json.loads(job.result_json) if job.result_json else None,
        }


def _ensure_company(company_name: str) -> str:
    """
    Create company in DB if it doesn't exist yet.
    Uses case-insensitive lookup so 'TCS' and 'tcs' map to the same row.
    Returns the canonical name as stored in the DB.
    """
    normalized = _normalize_company_name(company_name)
    with db_manager.get_session() as session:
        # ilike = case-insensitive LIKE — finds 'TCS', 'tcs', 'Tcs' as the same
        company = session.query(Company).filter(
            Company.name.ilike(normalized)
        ).first()
        if not company:
            company = Company(name=normalized, display_name=company_name.strip())
            session.add(company)
            session.commit()
            logger.info(f"Created new company: {normalized}")
            return normalized
        return company.name


def _run_pipeline(job_id: str, company_name: str, max_experiences: int, force_refresh: bool):
    """Worker function – runs in a background thread."""
    _set_job(job_id, status='running', started_at=datetime.utcnow().isoformat())
    try:
        from scrapers.pipeline_manager import pipeline_manager
        results = pipeline_manager.run_complete_analysis(
            company_name,
            max_experiences=max_experiences,
            force_refresh=force_refresh
        )

        with db_manager.get_session() as session:
            total = session.query(InterviewExperience).join(Company).filter(
                Company.name == company_name
            ).count()

        dc = results.get('data_collection', {})
        _set_job(job_id,
            status='completed',
            finished_at=datetime.utcnow().isoformat(),
            result={
                'status': results['status'],
                'company': company_name,
                'data_collection': {
                    'total_experiences': total,
                    'newly_scraped': dc.get('newly_scraped', 0),
                    'scrapers_used': list(dc.get('platform_results', {}).keys()),
                    'platforms_breakdown': dc.get('platform_results', {}),
                    'time_taken': f"{results.get('performance_metrics', {}).get('total_time_seconds', 0):.1f}s"
                },
                'analysis_metadata': {
                    'topics_identified': len(results.get('analysis_results', {}).get('unique_topics', [])),
                    'insights_generated': len(
                        results.get('insights', {})
                              .get('topic_insights', {})
                              .get('detailed_topics', {})
                    ),
                    'stages_completed': results.get('stages_completed', []),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        )
        logger.info(f"Job {job_id} completed for {company_name}")

    except Exception as e:
        logger.error(f"Job {job_id} failed for {company_name}: {e}", exc_info=True)
        _set_job(job_id, status='failed', error=str(e), finished_at=datetime.utcnow().isoformat())


@analysis_bp.route('/<company_name>', methods=['POST'])
def trigger_analysis(company_name):
    """Start a background scraping job and return a job_id immediately."""
    try:
        data = request.get_json() or {}
        max_experiences = data.get('max_experiences', 20)
        force_refresh = data.get('force_refresh', False)

        # Normalize before storing so 'TCS' and 'tcs' resolve to the same company
        canonical = _ensure_company(company_name)

        job_id = str(uuid.uuid4())[:12]
        _set_job(job_id, status='queued', company=canonical)

        thread = threading.Thread(
            target=_run_pipeline,
            args=(job_id, canonical, max_experiences, force_refresh),
            daemon=True
        )
        thread.start()

        logger.info(f"Started job {job_id} for '{canonical}'")
        return jsonify({
            'status': 'started',
            'job_id': job_id,
            'company': canonical,
            'message': f'Scraping started for {canonical}. Poll /api/analysis/job/{job_id} for progress.'
        }), 202

    except Exception as e:
        logger.error(f"Failed to start analysis for '{company_name}': {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500


@analysis_bp.route('/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Poll this endpoint to check scraping job progress."""
    job = _get_job(job_id)
    if not job:
        return jsonify({'status': 'error', 'error': 'Job not found'}), 404

    response = {
        'job_id':     job_id,
        'status':     job.get('status'),
        'company':    job.get('company'),
        'started_at': job.get('started_at'),
    }
    if job.get('status') == 'completed':
        response['result'] = job.get('result', {})
        response['finished_at'] = job.get('finished_at')
    elif job.get('status') == 'failed':
        response['error'] = job.get('error')
        response['finished_at'] = job.get('finished_at')

    return jsonify(response)


@analysis_bp.route('/status', methods=['GET'])
def get_analysis_status():
    return jsonify({
        'status': 'active',
        'message': 'Async pipeline active: scraping + NLP analysis + insights generation',
        'available_features': ['scraping', 'topic_extraction', 'insights_generation'],
        'scrapers': ['geeksforgeeks', 'leetcode', 'glassdoor', 'reddit']
    })
