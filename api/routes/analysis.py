"""
Analysis routes - async background scraping + polling.
"""

import threading
import uuid
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from database.connection import db_manager
from database.models import Company, InterviewExperience

analysis_bp = Blueprint('analysis', __name__)
logger = logging.getLogger(__name__)

# In-memory job store  {job_id: {status, company, result, error, started_at}}
_jobs: dict = {}
_jobs_lock = threading.Lock()


def _set_job(job_id: str, **kwargs):
    with _jobs_lock:
        _jobs[job_id] = {**_jobs.get(job_id, {}), **kwargs}


def _get_job(job_id: str):
    with _jobs_lock:
        return dict(_jobs.get(job_id, {}))


def _ensure_company(company_name: str):
    """Create company in DB if it doesn't exist yet."""
    with db_manager.get_session() as session:
        company = session.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(name=company_name, display_name=company_name)
            session.add(company)
            session.commit()
            logger.info(f"Created new company: {company_name}")


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

        _ensure_company(company_name)

        job_id = str(uuid.uuid4())[:12]
        _set_job(job_id, status='queued', company=company_name)

        thread = threading.Thread(
            target=_run_pipeline,
            args=(job_id, company_name, max_experiences, force_refresh),
            daemon=True
        )
        thread.start()

        logger.info(f"Started job {job_id} for '{company_name}'")
        return jsonify({
            'status': 'started',
            'job_id': job_id,
            'company': company_name,
            'message': f'Scraping started for {company_name}. Poll /api/analysis/job/{job_id} for progress.'
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
        'job_id': job_id,
        'status': job.get('status'),
        'company': job.get('company'),
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
