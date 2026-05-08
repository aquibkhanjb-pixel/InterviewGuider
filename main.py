import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def create_app():
    """Create Flask application with database setup."""
    from flask import Flask, jsonify
    from flask_cors import CORS
    from config.settings import config
    from database.models import db
    from database.connection import initialize_database
    
    # Get configuration
    config_name = os.getenv('FLASK_ENV', 'development')
    app_config = config.get(config_name, config['default'])
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(app_config)
    
    # Enable CORS for all origins (portfolio project — restrict after confirming Vercel URL)
    CORS(app)
    
    # Initialize database
    db.init_app(app)

    # Initialize database tables and seed data
    with app.app_context():
        try:
            success = initialize_database(app, db)
            if not success:
                print("WARNING: Database initialization had issues, but continuing...")
                # In production, we'll create tables even if seeding fails
                try:
                    db.create_all()
                    print("INFO: Database tables created successfully")
                except Exception as e:
                    print(f"ERROR: Failed to create tables: {e}")
                    # Only raise in development
                    if config_name == 'development':
                        raise RuntimeError("Database initialization failed")
        except Exception as e:
            print(f"ERROR: Database initialization error: {e}")
            # Only raise in development, allow production to continue
            if config_name == 'development':
                raise
    
    # Register routes with enhanced error handling
    routes_registered = False
    try:
        from api.routes import register_routes
        register_routes(app)
        routes_registered = True
        print("SUCCESS: API routes registered successfully")
    except ImportError as e:
        print(f"WARNING: Could not import API routes: {e}")
        print("NOTE: Please ensure api/routes/__init__.py exists")
        routes_registered = False
    except Exception as e:
        print(f"ERROR: Error registering routes: {e}")
        routes_registered = False
    
    # Enhanced basic routes with proper JSON responses
    @app.route('/')
    def root():
        return jsonify({
            'message': 'Interview Intelligence System', 
            'status': 'running',
            'version': '1.0.0',
            'routes_registered': routes_registered,
            'endpoints': {
                'health': '/api/health',
                'companies': '/api/companies/',
                'insights': '/api/insights/<company_name>',
                'analysis': '/api/analysis/<company_name>',
                'comparison': '/api/compare/',
                'docs': '/api/docs'
            }
        })
    
    @app.route('/api/health', strict_slashes=False)
    def health():
        from database.connection import db_manager
        from sqlalchemy import text, inspect
        health_status = db_manager.health_check()
        tables = []
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
        except Exception as e:
            tables = [f"error: {e}"]
        return jsonify({
            'status': 'healthy' if health_status else 'unhealthy',
            'database': 'connected' if health_status else 'disconnected',
            'routes_registered': routes_registered,
            'tables': tables,
            'timestamp': 'now'
        })
    
    @app.route('/api/debug/insights/<company_name>')
    def debug_insights(company_name):
        """Temporary debug endpoint — returns error traceback as 200 so it's visible."""
        import traceback
        try:
            from database.connection import db_manager
            from database.models import Company, InterviewExperience
            from datetime import datetime as _dt

            with db_manager.get_session() as session:
                company = session.query(Company).filter(Company.name == company_name).first()
                if not company:
                    return jsonify({'error': 'company not found'})
                rows = session.query(InterviewExperience).filter(
                    InterviewExperience.company_id == company.id
                ).limit(3).all()
                experiences = [
                    {
                        'id': r.id,
                        'title': r.title or '',
                        'content': r.content or '',
                        'experience_date': r.experience_date or _dt.utcnow(),
                        'time_weight': r.time_weight if r.time_weight is not None else 1.0,
                        'source_platform': r.source_platform,
                        'outcome': 'unknown',
                    }
                    for r in rows
                ]

            from analysis.topic_extractor import AdvancedTopicExtractor
            te = AdvancedTopicExtractor()
            sample = te.extract_topics_from_experience(experiences[0]) if experiences else {}

            from analysis.insights_generator import CompanyInsightsGenerator
            gen = CompanyInsightsGenerator()
            result = gen.generate_comprehensive_insights(company_name, experiences)
            return jsonify({'ok': True, 'sample_topics': list(sample.get('topics', {}).keys())[:5], 'status': result.get('status', 'unknown')})

        except Exception as e:
            return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()})

    @app.route('/api/docs')
    def docs():
        return jsonify({
            'title': 'Interview Intelligence System API',
            'version': '1.0.0',
            'description': 'Advanced interview preparation system with AI-powered insights',
            'routes_status': 'fully_loaded' if routes_registered else 'basic_only',
            'available_endpoints': [str(rule.rule) for rule in app.url_map.iter_rules() if rule.endpoint != 'static']
        })
    
    # Enhanced error handlers with debugging info
    @app.errorhandler(404)
    def not_found(error):
        available_routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                available_routes.append(f"{rule.rule} [{methods}]")
        
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested API endpoint does not exist',
            'routes_registered': routes_registered,
            'available_routes': available_routes
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'routes_registered': routes_registered
        }), 500
    
    return app

def main():
    """Main application entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interview Intelligence System')
    parser.add_argument('--mode', choices=['web', 'test'], default='web')
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        app = create_app()
        print("=" * 60)
        print("STARTING: Interview Intelligence System...")
        print("INFO: API will be available at: http://localhost:5000")
        print("=" * 60)
        
        # Print available routes for debugging
        with app.app_context():
            print("INFO: Available routes:")
            route_count = 0
            for rule in app.url_map.iter_rules():
                if rule.endpoint != 'static':
                    methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                    print(f"   {rule.rule} [{methods}]")
                    route_count += 1
            
            print(f"\nINFO: Total routes registered: {route_count}")
            
            # Check for missing route files
            missing_files = []
            route_files = [
                'api/routes/__init__.py',
                'api/routes/analysis.py',
                'api/routes/companies.py',
                'api/routes/insights.py',
                'api/routes/comparison.py',
                'api/routes/health.py'
            ]
            
            for file_path in route_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
            
            if missing_files:
                print(f"\nWARNING: Missing route files:")
                for file_path in missing_files:
                    print(f"   ERROR: {file_path}")
                print("\nTIP: Create these files to enable full API functionality")
            else:
                print("\nSUCCESS: All route files present")
        
        print("=" * 60)
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )
    elif args.mode == 'test':
        test_database_setup()

def test_database_setup():
    """Test database setup."""
    print("INFO: Testing database setup...")
    
    try:
        app = create_app()
        with app.app_context():
            from database.models import Company, db
            from database.connection import db_manager
            
            # Test health check
            health = db_manager.health_check()
            print(f"INFO: Database health: {'SUCCESS: Connected' if health else 'ERROR: Failed'}")

            # Test querying
            companies = Company.query.all()
            print(f"INFO: Companies in database: {len(companies)}")
            for company in companies:
                print(f"   - {company.name}")

            # Test route registration
            from api.routes import register_routes
            print("INFO: Route registration: SUCCESS: Working")
            
        print("SUCCESS: Database setup test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"ERROR: Route import failed: {e}")
        print("NOTE: This is expected if api/routes/__init__.py doesn't exist")
        return False
    except Exception as e:
        print(f"ERROR: Database setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()