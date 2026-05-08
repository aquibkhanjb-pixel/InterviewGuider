from flask import Blueprint, jsonify, request
from database.connection import db_manager
from database.models import Company, InterviewExperience
from config.settings import Config
import logging

companies_bp = Blueprint('companies', __name__)
logger = logging.getLogger(__name__)

@companies_bp.route('/', methods=['GET'])
def get_companies():
    """Get list of all tracked companies with statistics."""
    try:
        with db_manager.get_session() as session:
            companies_data = []
            
            for company in session.query(Company).all():
                experience_count = session.query(InterviewExperience).filter(
                    InterviewExperience.company_id == company.id
                ).count()
                
                latest_update = session.query(InterviewExperience).filter(
                    InterviewExperience.company_id == company.id
                ).order_by(InterviewExperience.scraped_at.desc()).first()
                
                companies_data.append({
                    'id': company.id,
                    'name': company.name,
                    'display_name': company.display_name or company.name,
                    'experience_count': experience_count,
                    'latest_update': latest_update.scraped_at.isoformat() if latest_update else None,
                    'status': 'active' if experience_count > 0 else 'inactive'
                })
            
            return jsonify({
                'companies': companies_data,
                'total_companies': len(companies_data),
                'target_companies': Config.TARGET_COMPANIES
            })
            
    except Exception as e:
        logger.error(f"Error fetching companies: {e}", exc_info=True)
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@companies_bp.route('/<company_name>/experiences', methods=['GET'])
def get_company_experiences(company_name):
    """Get interview experiences for a specific company."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with db_manager.get_session() as session:
            company = session.query(Company).filter(
                Company.name.ilike(company_name.strip())
            ).first()
            
            if not company:
                return jsonify({'error': 'Company not found'}), 404
            
            experiences = session.query(InterviewExperience).filter(
                InterviewExperience.company_id == company.id
            ).order_by(InterviewExperience.experience_date.desc()).offset(offset).limit(limit).all()
            
            experiences_data = []
            for exp in experiences:
                experiences_data.append({
                    'id': exp.id,
                    'title': exp.title,
                    'content_preview': exp.content[:200] + '...' if len(exp.content) > 200 else exp.content,
                    'role': exp.role,
                    'experience_date': exp.experience_date.isoformat(),
                    'source_platform': exp.source_platform,
                    'source_url': exp.source_url,  # Add source URL for reference
                    'time_weight': exp.time_weight,
                    'success': exp.success,
                    'difficulty_score': exp.difficulty_score
                })
            
            total_count = session.query(InterviewExperience).filter(
                InterviewExperience.company_id == company.id
            ).count()
            
            return jsonify({
                'company': company_name,
                'experiences': experiences_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_next': offset + limit < total_count
                }
            })
            
    except Exception as e:
        logger.error(f"Error fetching experiences for {company_name}: {e}")
        return jsonify({'error': 'Internal server error'}), 500