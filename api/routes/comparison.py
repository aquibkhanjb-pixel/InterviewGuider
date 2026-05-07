from flask import Blueprint, jsonify, request
from database.connection import db_manager
from database.models import Company, InterviewExperience
import logging
from datetime import datetime

comparison_bp = Blueprint('comparison', __name__)
logger = logging.getLogger(__name__)


def _load_experiences(session, company) -> list:
    rows = (
        session.query(InterviewExperience)
        .filter(InterviewExperience.company_id == company.id)
        .order_by(InterviewExperience.experience_date.desc())
        .all()
    )
    return [
        {
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
        }
        for exp in rows
    ]


@comparison_bp.route('/', methods=['POST'])
def compare_companies():
    """Compare live ML-scored insights across multiple companies."""
    try:
        data = request.get_json()
        if not data or 'companies' not in data:
            return jsonify({'error': 'companies list required'}), 400

        companies = data['companies']
        if len(companies) < 2:
            return jsonify({'error': 'At least 2 companies required'}), 400
        if len(companies) > 5:
            return jsonify({'error': 'Maximum 5 companies allowed'}), 400

        from analysis.insights_generator import CompanyInsightsGenerator
        gen = CompanyInsightsGenerator()

        comparison_data = {}

        for company_name in companies:
            try:
                with db_manager.get_session() as session:
                    company = session.query(Company).filter(
                        Company.name == company_name
                    ).first()

                    if not company:
                        comparison_data[company_name] = {'error': 'Company not found'}
                        continue

                    total = (
                        session.query(InterviewExperience)
                        .filter(InterviewExperience.company_id == company.id)
                        .count()
                    )

                    if total == 0:
                        comparison_data[company_name] = {'error': 'No experiences — run analysis first'}
                        continue

                    experiences = _load_experiences(session, company)

                full = gen.generate_comprehensive_insights(company_name, experiences)

                if full.get('status') == 'insufficient_data':
                    comparison_data[company_name] = {'error': full.get('message', 'Insufficient data')}
                    continue

                detailed = full.get('topic_insights', {}).get('detailed_topics', {})

                # Normalise to what the frontend expects
                formatted = {
                    key: {
                        'topic_name':          td.get('topic_name', key),
                        'category':            td.get('category', ''),
                        'weighted_frequency':  round(td.get('weighted_frequency', 0), 1),
                        'priority_level':      td.get('priority_level', 'LOW'),
                        'confidence_score':    td.get('confidence_score', 0),
                        'mentions_count':      td.get('mentions_count', 0),
                        'discriminative_score': td.get('discriminative_score'),
                        'semantic_confidence': td.get('semantic_confidence'),
                    }
                    for key, td in detailed.items()
                }

                comparison_data[company_name] = {
                    'insights':    formatted,
                    'top_5_topics': list(formatted.keys())[:5],
                    'sample_size': total,
                }

            except Exception as exc:
                logger.error(f"Error generating insights for {company_name}: {exc}", exc_info=True)
                comparison_data[company_name] = {'error': str(exc)}

        comparison_insights = _generate_comparison_insights(comparison_data)

        return jsonify({
            'companies':          companies,
            'comparison_data':    comparison_data,
            'comparison_insights': comparison_insights,
            'generated_at':       datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error in company comparison: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _generate_comparison_insights(comparison_data: dict) -> dict:
    """Find common topics, unique topics, and average frequencies."""
    all_topics: dict = {}

    for company, data in comparison_data.items():
        if 'insights' not in data:
            continue
        for topic_key, td in data['insights'].items():
            if topic_key not in all_topics:
                all_topics[topic_key] = []
            all_topics[topic_key].append({
                'company':   company,
                'frequency': td['weighted_frequency'],
                'priority':  td['priority_level'],
                'topic_name': td['topic_name'],
            })

    common_topics = []
    unique_topics: dict = {}

    for topic_key, company_list in all_topics.items():
        if len(company_list) >= 2:
            avg_freq = sum(d['frequency'] for d in company_list) / len(company_list)
            common_topics.append({
                'topic':             company_list[0]['topic_name'],
                'companies':         company_list,
                'average_frequency': round(avg_freq, 1),
            })
        else:
            owner = company_list[0]['company']
            unique_topics.setdefault(owner, []).append(company_list[0]['topic_name'])

    common_topics.sort(key=lambda x: x['average_frequency'], reverse=True)

    return {
        'common_topics':  common_topics,
        'unique_topics':  unique_topics,
    }
