# ============================================================================
# scrapers/pipeline_manager.py - Complete System Orchestration
# ============================================================================

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from scrapers.leetcode_scraper import LeetCodeScraper
from scrapers.glassdoor_scraper import GlassdoorScraper
from scrapers.redit_scrapper import RedditScraper
from scrapers.interviewbit_scraper import InterviewBitScraper
from scrapers.ambitionbox_scraper import AmbitionBoxScraper

from database.connection import db_manager
from database.models import Company, InterviewExperience, Topic, TopicMention, CompanyInsight
from scrapers.geeksforgeeks_scraper import GeeksforGeeksScraper
from analysis.topic_extractor import AdvancedTopicExtractor
from analysis.insights_generator import CompanyInsightsGenerator
from config.settings import Config
from utils.logger import project_logger

class PipelineManager:
    """
    Complete pipeline orchestration system.
    Manages the entire flow: Scraping -> Analysis -> Storage -> Insights
    """
    
    def __init__(self):
        self.logger = project_logger.get_logger('pipeline_manager')
        self.session_id = str(uuid.uuid4())[:8]
        
        # Initialize multiple scrapers
        self.scrapers = {
            'geeksforgeeks': GeeksforGeeksScraper(),
            'interviewbit':  InterviewBitScraper(),
            'ambitionbox':   AmbitionBoxScraper(),
            'leetcode':      LeetCodeScraper(),
            'reddit':        RedditScraper(),
            'glassdoor':     GlassdoorScraper(),
        }
        
        self.topic_extractor = AdvancedTopicExtractor()
        self.insights_generator = CompanyInsightsGenerator()
        
        # Enhanced statistics tracking
        self.session_stats = {
            'start_time': datetime.utcnow(),
            'companies_processed': 0,
            'experiences_scraped': 0,
            'topics_extracted': 0,
            'insights_generated': 0,
            'errors_encountered': 0,
            'scraper_performance': {
                'geeksforgeeks': {'attempted': 0, 'successful': 0},
                'interviewbit':  {'attempted': 0, 'successful': 0},
                'ambitionbox':   {'attempted': 0, 'successful': 0},
                'leetcode':      {'attempted': 0, 'successful': 0},
                'reddit':        {'attempted': 0, 'successful': 0},
                'glassdoor':     {'attempted': 0, 'successful': 0},
            }
        }
    
    def run_complete_analysis(self, company_name: str, 
                            max_experiences: int = 20,
                            force_refresh: bool = False) -> Dict:
        """
        Run complete analysis pipeline for a company.
        
        Args:
            company_name: Name of the company to analyze
            max_experiences: Maximum number of experiences to collect
            force_refresh: Whether to force fresh scraping
            
        Returns:
            Complete analysis results with insights
        """
        start_time = time.time()
        
        self.logger.info(f"Starting complete analysis for {company_name}")
        project_logger.log_scraping_session(
             company_name, {'max_experiences': max_experiences}, self.session_id
        )
        
        results = {
            'company': company_name,
            'session_id': self.session_id,
            'analysis_date': datetime.utcnow().isoformat(),
            'status': 'success',
            'stages_completed': [],
            'data_collection': {},
            'analysis_results': {},
            'insights': {},
            'performance_metrics': {},
            'recommendations': {}
        }
        
        try:
            # Stage 1: Data Collection
            collection_results = self._run_data_collection_stage(
                company_name, max_experiences, force_refresh
            )
            results['data_collection'] = collection_results
            results['stages_completed'].append('data_collection')
            
            if collection_results['total_experiences'] == 0:
                results['status'] = 'no_data'
                results['message'] = 'No interview experiences found for analysis'
                return results
            
            # Stage 2: Topic Analysis
            analysis_results = self._run_analysis_stage(company_name)
            results['analysis_results'] = analysis_results
            results['stages_completed'].append('analysis')
            
            # Stage 3: Insights Generation
            insights = self._run_insights_generation_stage(company_name)
            results['insights'] = insights
            results['stages_completed'].append('insights_generation')
            
            # Stage 4: Performance Metrics
            performance_metrics = self._calculate_performance_metrics(start_time)
            results['performance_metrics'] = performance_metrics
            
            # Stage 5: Generate Recommendations
            recommendations = self._generate_actionable_recommendations(insights)
            results['recommendations'] = recommendations
            
            self.session_stats['companies_processed'] += 1
            
            self.logger.info(f"Complete analysis finished for {company_name} in {performance_metrics['total_time_seconds']:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for {company_name}: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
            self.session_stats['errors_encountered'] += 1
        
        return results
    
    def _run_data_collection_stage(self, company_name: str, 
                                max_experiences: int, 
                                force_refresh: bool) -> Dict:
        """Enhanced data collection with multiple scrapers."""
        stage_start = time.time()
        self.logger.info(f"Stage 1: Multi-platform data collection for {company_name}")
        
        existing_count = self._get_existing_experience_count(company_name)
        
        collection_results = {
            'existing_experiences': existing_count,
            'newly_scraped': 0,
            'total_experiences': existing_count,
            'scraping_performed': False,
            'platform_results': {},
            'collection_time_seconds': 0
        }
        
        should_scrape = (
            force_refresh or 
            existing_count < max_experiences or
            self._is_data_stale(company_name)
        )
        
        if should_scrape:
            # Distribute scraping across platforms
            experiences_per_platform = max_experiences // len(self.scrapers)
            total_scraped = 0
            
            for platform_name, scraper in self.scrapers.items():
                platform_start = time.time()
                platform_scraped = 0
                
                try:
                    self.logger.info(f"Scraping from {platform_name}...")
                    self.session_stats['scraper_performance'][platform_name]['attempted'] += 1
                    
                    # Scrape experiences
                    platform_experiences = list(scraper.scrape_company_experiences(
                        company_name, 
                        max_experiences=experiences_per_platform
                    ))
                    
                    # Store each experience
                    for exp_data in platform_experiences:
                        experience_id = self._store_experience(exp_data)
                        if experience_id:
                            platform_scraped += 1
                            total_scraped += 1
                    
                    # Record platform results
                    collection_results['platform_results'][platform_name] = {
                        'scraped_count': platform_scraped,
                        'time_seconds': time.time() - platform_start,
                        'success_rate': platform_scraped / max(len(platform_experiences), 1)
                    }
                    
                    self.session_stats['scraper_performance'][platform_name]['successful'] += platform_scraped
                    self.logger.info(f"{platform_name}: {platform_scraped} experiences")
                    
                except Exception as e:
                    self.logger.error(f"{platform_name} scraping failed: {e}")
                    collection_results['platform_results'][platform_name] = {
                        'scraped_count': 0,
                        'error': str(e),
                        'time_seconds': time.time() - platform_start
                    }
            
            collection_results['newly_scraped'] = total_scraped
            collection_results['scraping_performed'] = True
            self.session_stats['experiences_scraped'] += total_scraped
        
        collection_results['total_experiences'] = self._get_existing_experience_count(company_name)
        collection_results['collection_time_seconds'] = time.time() - stage_start
        
        return collection_results
    
    def _run_analysis_stage(self, company_name: str) -> Dict:
        """Run topic analysis on all experiences."""
        stage_start = time.time()
        self.logger.info(f"Stage 2: Topic Analysis for {company_name}")
        
        # Get all experiences for the company
        experiences = self._get_company_experiences(company_name)
        
        analysis_results = {
            'experiences_analyzed': 0,
            'total_topics_found': 0,
            'unique_topics': set(),
            'analysis_time_seconds': 0,
            'topic_distribution': {}
        }
        
        topics_found = []
        
        for experience in experiences:
            try:
                # Skip if already analyzed recently
                if self._is_experience_recently_analyzed(experience['id']):
                    continue
                
                # Extract topics
                topic_analysis = self.topic_extractor.extract_topics_from_experience({
                    'content': experience['content'],
                    'title': experience['title'],
                    'experience_date': experience['experience_date']
                })
                
                # Store topic mentions
                if topic_analysis['topics']:
                    self._store_topic_mentions(experience['id'], topic_analysis['topics'])
                    
                    for topic in topic_analysis['topics'].keys():
                        analysis_results['unique_topics'].add(topic)
                        topics_found.append(topic)
                
                analysis_results['experiences_analyzed'] += 1
                analysis_results['total_topics_found'] += len(topic_analysis['topics'])
                
            except Exception as e:
                self.logger.error(f"Error analyzing experience {experience['id']}: {e}")
        
        # Calculate topic distribution
        topic_counts = {}
        for topic in topics_found:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        analysis_results['topic_distribution'] = topic_counts
        analysis_results['unique_topics'] = list(analysis_results['unique_topics'])
        analysis_results['analysis_time_seconds'] = time.time() - stage_start
        
        self.session_stats['topics_extracted'] += analysis_results['total_topics_found']
        
        return analysis_results
    
    def _run_insights_generation_stage(self, company_name: str) -> Dict:
        """Generate comprehensive insights."""
        stage_start = time.time()
        self.logger.info(f"Stage 3: Insights Generation for {company_name}")
        
        # Get processed experiences with topics
        experiences_with_topics = self._get_experiences_with_topic_data(company_name)
        
        if not experiences_with_topics:
            return {
                'status': 'no_data',
                'message': 'No analyzed experiences available for insights generation'
            }
        
        # Generate comprehensive insights
        insights = self.insights_generator.generate_comprehensive_insights(
            company_name, experiences_with_topics
        )
        
        # Store insights in database
        self._store_company_insights(company_name, insights)
        
        insights['generation_time_seconds'] = time.time() - stage_start
        self.session_stats['insights_generated'] += 1
        
        project_logger.log_analysis_results(
            company_name,
            len(insights.get('topic_insights', {}).get('detailed_topics', {})),
            insights.get('statistical_confidence', 0),
            self.session_id
        )
        
        return insights
    
    def _generate_actionable_recommendations(self, insights: Dict) -> Dict:
        """Generate specific, actionable recommendations."""
        
        if not insights or 'topic_insights' not in insights:
            return {}
        
        topic_insights = insights['topic_insights']
        high_priority_topics = topic_insights.get('high_priority_topics', [])
        top_5_topics = topic_insights.get('top_5_topics', [])
        
        recommendations = {
            'immediate_focus': [],
            'study_plan': {},
            'time_allocation': {},
            'practice_strategy': {},
            'timeline': {}
        }
        
        # Immediate focus recommendations
        for topic in high_priority_topics[:3]:
            if topic in topic_insights['detailed_topics']:
                topic_data = topic_insights['detailed_topics'][topic]
                recommendations['immediate_focus'].append({
                    'topic': topic_data['topic_name'],
                    'priority': 'CRITICAL',
                    'reason': f"Appears in {topic_data['weighted_frequency']}% of interviews",
                    'action': f"Dedicate 40% of study time to {topic_data['topic_name']}"
                })
        
        # Study plan (4-week timeline)
        week_plan = {}
        for i, topic in enumerate(top_5_topics[:4]):
            if topic in topic_insights['detailed_topics']:
                topic_data = topic_insights['detailed_topics'][topic]
                week_plan[f'Week {i+1}'] = {
                    'focus_topic': topic_data['topic_name'],
                    'study_resources': topic_data.get('study_resources', {}),
                    'estimated_hours': self._estimate_study_hours(topic_data['category']),
                    'practice_problems': topic_data.get('practice_problems', [])
                }
        
        recommendations['study_plan'] = week_plan
        
        # Time allocation based on priority
        total_topics = len(top_5_topics)
        high_priority_count = len(high_priority_topics)
        
        if high_priority_count > 0:
            recommendations['time_allocation'] = {
                'high_priority_topics': '60%',
                'medium_priority_topics': '30%',
                'additional_preparation': '10%'
            }
        
        # Practice strategy
        difficulty_analysis = insights.get('difficulty_analysis', {})
        primary_difficulty = difficulty_analysis.get('primary_difficulty', 'medium')
        
        recommendations['practice_strategy'] = {
            'difficulty_focus': primary_difficulty,
            'problem_solving_approach': self._get_problem_solving_strategy(primary_difficulty),
            'mock_interviews': 'Schedule 2-3 mock interviews focusing on top topics',
            'system_design': 'Include if 3+ years experience' if 'system_design' in [t.split('.')[0] for t in top_5_topics] else 'Optional'
        }
        
        # Timeline recommendations
        recommendations['timeline'] = {
            'preparation_duration': '3-4 weeks',
            'daily_study_hours': '2-3 hours',
            'mock_interview_timing': 'Week 3-4',
            'final_review': 'Last 2-3 days before interview'
        }
        
        return recommendations
    
    def _estimate_study_hours(self, category: str) -> str:
        """Estimate study hours needed for different categories."""
        hour_estimates = {
            'algorithms': '15-20 hours',
            'data_structures': '12-15 hours', 
            'system_design': '20-25 hours',
            'programming_concepts': '8-10 hours',
            'technologies': '5-8 hours'
        }
        return hour_estimates.get(category, '10-12 hours')
    
    def _get_problem_solving_strategy(self, difficulty: str) -> str:
        """Get problem solving strategy based on difficulty."""
        strategies = {
            'easy': 'Focus on implementation speed and clean code',
            'medium': 'Balance between optimization and correctness',
            'hard': 'Emphasize problem breakdown and multiple approaches'
        }
        return strategies.get(difficulty, 'Practice systematic problem-solving approach')
    
    # Database helper methods
    def _get_existing_experience_count(self, company_name: str) -> int:
        """Get count of existing experiences for a company."""
        try:
            with db_manager.get_session() as session:
                count = session.query(InterviewExperience).join(Company).filter(
                    Company.name == company_name
                ).count()
                return count
        except Exception as e:
            self.logger.error(f"Error getting experience count: {e}")
            return 0
    
    def _is_data_stale(self, company_name: str, days_threshold: int = 7) -> bool:
        """Check if existing data is stale."""
        try:
            with db_manager.get_session() as session:
                latest_experience = session.query(InterviewExperience).join(Company).filter(
                    Company.name == company_name
                ).order_by(InterviewExperience.scraped_at.desc()).first()
                
                if latest_experience:
                    scraped = latest_experience.scraped_at
                    if scraped and scraped.tzinfo is not None:
                        scraped = scraped.replace(tzinfo=None)
                    days_since_update = (datetime.utcnow() - scraped).days if scraped else 999
                    return days_since_update > days_threshold
                
                return True  # No data means stale
                
        except Exception as e:
            self.logger.error(f"Error checking data staleness: {e}")
            return True
    
    def _store_experience(self, experience_data: Dict) -> Optional[int]:
        """Store interview experience in database."""
        try:
            with db_manager.get_session() as session:
                # Check if experience already exists by URL to avoid duplicates
                existing = session.query(InterviewExperience).filter(
                    InterviewExperience.source_url == experience_data['source_url']
                ).first()

                if existing:
                    self.logger.debug(f"Experience already exists: {experience_data['source_url']}")
                    return existing.id

                # Get or create company
                company = session.query(Company).filter(
                    Company.name == experience_data['company']
                ).first()

                if not company:
                    company = Company(
                        name=experience_data['company'],
                        display_name=experience_data['company']
                    )
                    session.add(company)
                    session.flush()  # Keep flush here to get ID

                # Create experience
                experience = InterviewExperience(
                    company_id=company.id,
                    title=experience_data['title'],
                    content=experience_data['content'],
                    source_url=experience_data['source_url'],
                    source_platform=experience_data['source_platform'],
                    role=experience_data.get('role', 'Software Engineer'),
                    experience_date=experience_data['experience_date'],
                    time_weight=experience_data.get('time_weight', 1.0),
                    success=experience_data.get('outcome') == 'offer',
                    scraped_at=datetime.utcnow(),
                    processed_at=None
                )

                session.add(experience)
                session.commit()  # COMMIT THE TRANSACTION!

                return experience.id

        except Exception as e:
            self.logger.error(f"Error storing experience: {e}")
            return None
    
    def _get_company_experiences(self, company_name: str) -> List[Dict]:
        """Get all experiences for a company."""
        try:
            with db_manager.get_session() as session:
                experiences = session.query(InterviewExperience).join(Company).filter(
                    Company.name == company_name
                ).all()
                
                return [
                    {
                        'id': exp.id,
                        'title': exp.title,
                        'content': exp.content,
                        'experience_date': exp.experience_date,
                        'time_weight': exp.time_weight,
                        'source_platform': exp.source_platform
                    }
                    for exp in experiences
                ]
                
        except Exception as e:
            self.logger.error(f"Error getting company experiences: {e}")
            return []
    
    def _is_experience_recently_analyzed(self, experience_id: int, hours_threshold: int = 24) -> bool:
        """Check if experience was analyzed recently."""
        try:
            with db_manager.get_session() as session:
                experience = session.query(InterviewExperience).filter(
                    InterviewExperience.id == experience_id
                ).first()
                
                if experience and experience.processed_at:
                    proc = experience.processed_at
                    if proc.tzinfo is not None:
                        proc = proc.replace(tzinfo=None)
                    hours_since = (datetime.utcnow() - proc).total_seconds() / 3600
                    return hours_since < hours_threshold
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking analysis recency: {e}")
            return False
    
    def _store_topic_mentions(self, experience_id: int, topics: Dict):
        """Store topic mentions for an experience."""
        try:
            with db_manager.get_session() as session:
                for topic_key, topic_data in topics.items():
                    # Get or create topic
                    topic = session.query(Topic).filter(Topic.name == topic_key).first()
                    
                    if not topic:
                        category = topic_data['category']
                        topic_name = topic_data['topic_name']
                        
                        topic = Topic(
                            name=topic_key,
                            display_name=topic_name,
                            category=category,
                            description=f"{topic_name} in {category}"
                        )
                        session.add(topic)
                        session.flush()
                    
                    # Create topic mention
                    mention = TopicMention(
                        experience_id=experience_id,
                        topic_id=topic.id,
                        frequency=topic_data['raw_count'],
                        importance_score=topic_data['importance_score'],
                        confidence=topic_data.get('confidence', 0.5)
                    )
                    
                    session.add(mention)
                
                # Update experience processed timestamp
                experience = session.query(InterviewExperience).filter(
                    InterviewExperience.id == experience_id
                ).first()
                
                if experience:
                    experience.processed_at = datetime.utcnow()

                session.commit()  # COMMIT THE TRANSACTION!
                
        except Exception as e:
            self.logger.error(f"Error storing topic mentions: {e}")
    
    def _get_experiences_with_topic_data(self, company_name: str) -> List[Dict]:
        """Get experiences with their topic analysis data."""
        try:
            with db_manager.get_session() as session:
                experiences = session.query(InterviewExperience).join(Company).filter(
                    Company.name == company_name,
                    InterviewExperience.processed_at.isnot(None)
                ).all()
                
                result = []
                for exp in experiences:
                    # Get topic mentions for this experience
                    mentions = session.query(TopicMention).filter(
                        TopicMention.experience_id == exp.id
                    ).all()
                    
                    topics_data = {}
                    for mention in mentions:
                        topic_key = mention.topic.name
                        topics_data[topic_key] = {
                            'raw_count': mention.frequency,
                            'importance_score': mention.importance_score,
                            'confidence': mention.confidence,
                            'category': mention.topic.category,
                            'topic_name': mention.topic.display_name
                        }
                    
                    result.append({
                        'id': exp.id,
                        'title': exp.title,
                        'content': exp.content,
                        'experience_date': exp.experience_date,
                        'time_weight': exp.time_weight,
                        'source_platform': exp.source_platform,
                        'outcome': 'offer' if exp.success is True else ('rejected' if exp.success is False else 'unknown'),
                        'topics': topics_data
                    })
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error getting experiences with topics: {e}")
            return []
    
    def _store_company_insights(self, company_name: str, insights: Dict):
        """Store generated insights in database."""
        try:
            with db_manager.get_session() as session:
                company = session.query(Company).filter(
                    Company.name == company_name
                ).first()
                
                if not company:
                    return
                
                # Clear old insights
                session.query(CompanyInsight).filter(
                    CompanyInsight.company_id == company.id
                ).delete()
                
                # Store new insights
                if 'topic_insights' in insights and 'detailed_topics' in insights['topic_insights']:
                    for topic_key, topic_data in insights['topic_insights']['detailed_topics'].items():
                        topic = session.query(Topic).filter(Topic.name == topic_key).first()
                        
                        if topic:
                            insight = CompanyInsight(
                                company_id=company.id,
                                topic_id=topic.id,
                                weighted_frequency=topic_data['weighted_frequency'],
                                confidence_score=topic_data['confidence_score'],
                                sample_size=insights['sample_size'],
                                priority_level=topic_data['priority_level'].lower(),
                                study_recommendation=topic_data['actionable_insight'],
                                analysis_date=datetime.utcnow()
                            )

                            session.add(insight)

                session.commit()  # COMMIT THE TRANSACTION!
                
        except Exception as e:
            self.logger.error(f"Error storing company insights: {e}")
    
    def _calculate_performance_metrics(self, start_time: float) -> Dict:
        """Calculate performance metrics for the pipeline run."""
        total_time = time.time() - start_time
        
        return {
            'total_time_seconds': round(total_time, 2),
            'experiences_per_second': round(self.session_stats['experiences_scraped'] / max(total_time, 1), 2),
            'topics_per_second': round(self.session_stats['topics_extracted'] / max(total_time, 1), 2),
            'memory_efficient': True,  # Using generators
            'session_stats': self.session_stats
        }
    
    def run_batch_analysis(self, companies: List[str], max_experiences_each: int = 20) -> Dict:
        """Run analysis for multiple companies in parallel."""
        self.logger.info(f"Starting batch analysis for {len(companies)} companies")
        
        batch_results = {
            'companies_processed': [],
            'total_time_seconds': 0,
            'summary_stats': {},
            'errors': []
        }
        
        start_time = time.time()
        
        # Process companies with controlled parallelism
        with ThreadPoolExecutor(max_workers=2) as executor:  # Conservative parallelism
            future_to_company = {
                executor.submit(self.run_complete_analysis, company, max_experiences_each): company
                for company in companies
            }
            
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    result = future.result()
                    batch_results['companies_processed'].append(result)
                except Exception as e:
                    error_info = {'company': company, 'error': str(e)}
                    batch_results['errors'].append(error_info)
                    self.logger.error(f"Batch processing failed for {company}: {e}")
        
        batch_results['total_time_seconds'] = time.time() - start_time
        
        # Calculate summary statistics
        successful_results = [r for r in batch_results['companies_processed'] if r['status'] == 'success']
        
        if successful_results:
            total_experiences = sum(r['data_collection']['total_experiences'] for r in successful_results)
            total_topics = sum(len(r['analysis_results'].get('unique_topics', [])) for r in successful_results)
            
            batch_results['summary_stats'] = {
                'successful_companies': len(successful_results),
                'failed_companies': len(batch_results['errors']),
                'total_experiences_analyzed': total_experiences,
                'total_unique_topics_found': total_topics,
                'average_processing_time': sum(r['performance_metrics']['total_time_seconds'] 
                                             for r in successful_results) / len(successful_results)
            }
        
        self.logger.info(f"Batch analysis completed: {batch_results['summary_stats']}")
        
        return batch_results
    
    def get_system_health_metrics(self) -> Dict:
        """Get comprehensive system health metrics."""
        try:
            health_metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'database_health': db_manager.health_check(),
                'scraper_stats': {},
                'session_stats': self.session_stats,
                'system_performance': {}
            }
            
            # Get scraper statistics
            for platform, scraper in self.scrapers.items():
                if hasattr(scraper, 'stats'):
                    health_metrics['scraper_stats'][platform] = scraper.stats
                if hasattr(scraper, 'rate_limiter'):
                    health_metrics['scraper_stats'][f'{platform}_rate_limiter'] = scraper.rate_limiter.get_stats()
            
            # Database metrics
            with db_manager.get_session() as session:
                health_metrics['system_performance'] = {
                    'total_companies': session.query(Company).count(),
                    'total_experiences': session.query(InterviewExperience).count(),
                    'total_topics': session.query(Topic).count(),
                    'recent_scrapes': session.query(InterviewExperience).filter(
                        InterviewExperience.scraped_at >= datetime.utcnow() - timedelta(days=7)
                    ).count()
                }
            
            return health_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting health metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    def cleanup_unknown_companies(self):
        """Clean up experiences with 'Unknown' company names."""
        try:
            with db_manager.get_session() as session:
                # Get all experiences with 'Unknown' company
                unknown_company = session.query(Company).filter(Company.name == 'Unknown').first()
                if unknown_company:
                    unknown_experiences = session.query(InterviewExperience).filter(
                        InterviewExperience.company_id == unknown_company.id
                    ).all()
                    
                    self.logger.info(f"Found {len(unknown_experiences)} experiences with Unknown company")
                    
                    # Get Amazon company (create if doesn't exist)
                    amazon_company = session.query(Company).filter(Company.name == 'Amazon').first()
                    if not amazon_company:
                        amazon_company = Company(
                            name='Amazon',
                            display_name='Amazon',
                            industry='Cloud/E-commerce',
                            size='large'
                        )
                        session.add(amazon_company)
                        session.flush()
                    
                    # Re-assign unknown experiences to Amazon
                    for exp in unknown_experiences:
                        exp.company_id = amazon_company.id
                    
                    session.commit()
                    self.logger.info(f"Reassigned {len(unknown_experiences)} experiences to Amazon")
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up unknown companies: {e}")

    def fix_unknown_companies(self):
        """Fix existing 'Unknown' company entries by re-analyzing their content."""
        try:
            with db_manager.get_session() as session:
                # Get Unknown company
                unknown_company = session.query(Company).filter(Company.name == 'Unknown').first()
                if not unknown_company:
                    self.logger.info("No 'Unknown' company found")
                    return
                
                # Get all experiences with Unknown company
                unknown_experiences = session.query(InterviewExperience).filter(
                    InterviewExperience.company_id == unknown_company.id
                ).all()
                
                self.logger.info(f"Found {len(unknown_experiences)} experiences to re-classify")
                
                company_reassignments = {}
                
                for exp in unknown_experiences:
                    # Re-extract company name using improved method
                    detected_company = self._re_extract_company_name(exp.title, exp.content)
                    
                    if detected_company != "Unknown":
                        if detected_company not in company_reassignments:
                            company_reassignments[detected_company] = []
                        company_reassignments[detected_company].append(exp)
                
                # Create/update companies and reassign experiences
                for company_name, experiences in company_reassignments.items():
                    # Get or create company
                    company = session.query(Company).filter(Company.name == company_name).first()
                    if not company:
                        company = Company(
                            name=company_name,
                            display_name=company_name,
                            industry=self._determine_industry(company_name),
                            size='medium'
                        )
                        session.add(company)
                        session.flush()
                        self.logger.info(f"Created new company: {company_name}")
                    
                    # Reassign experiences
                    for exp in experiences:
                        exp.company_id = company.id
                    
                    self.logger.info(f"Reassigned {len(experiences)} experiences to {company_name}")
                
                session.commit()
                self.logger.info("Company reassignment completed")
                
        except Exception as e:
            self.logger.error(f"Error fixing unknown companies: {e}")

    def _re_extract_company_name(self, title: str, content: str) -> str:
        """Re-extract company name using the improved method."""
        # Use the same improved extraction logic
        return self._extract_company_from_content(title, content)
    
    def _determine_industry(self, company_name: str) -> str:
        """Determine industry based on company name."""
        industry_mapping = {
            # Global Tech Giants
            'Amazon': 'Cloud/E-commerce',
            'Google': 'Technology/Internet',
            'Apple': 'Technology/Consumer Electronics',
            'Netflix': 'Entertainment/Streaming',
            'Meta': 'Social Media/Technology',
            'Microsoft': 'Technology/Cloud',

            # Indian Unicorns & Startups
            'Flipkart': 'E-commerce',
            'Myntra': 'E-commerce/Fashion',
            'Carwale': 'Automotive/Technology',
            'Swiggy': 'Food Delivery/Logistics',
            'Zomato': 'Food Delivery/Restaurant Aggregator',
            'Paytm': 'Fintech/Digital Payments',
            'PhonePe': 'Fintech/Digital Payments',
            'Razorpay': 'Fintech/Payments Gateway',
            'Ola': 'Transportation/Mobility',
            'Uber': 'Transportation/Mobility',
            'Byju': 'EdTech',
            'Unacademy': 'EdTech',
            'Vedantu': 'EdTech',
            'Freshworks': 'SaaS/Customer Engagement',
            'Zoho': 'SaaS/Enterprise Software',
            'InMobi': 'AdTech/Marketing Technology',
            'ShareChat': 'Social Media/Regional Content',
            'Dream11': 'Fantasy Sports/Gaming',
            'BigBasket': 'E-commerce/Online Grocery',
            'Grofers': 'E-commerce/Online Grocery',
            'Dunzo': 'Hyperlocal Delivery/Logistics',
            'Nykaa': 'E-commerce/Beauty & Lifestyle',
            'PolicyBazaar': 'InsurTech/Fintech',
            'MakeMyTrip': 'Travel & Tourism',
            'BookMyShow': 'Entertainment/Ticketing',
            'Lenskart': 'E-commerce/Eyewear',
            'UrbanClap': 'Services/Marketplace (now Urban Company)',
            'Cred': 'Fintech/Credit & Rewards'
        }

        return industry_mapping.get(company_name, 'Technology')

# ============================================================================
# API Integration Point
# ============================================================================

# Create a global pipeline manager instance
pipeline_manager = PipelineManager()

def get_pipeline_manager() -> PipelineManager:
    """Get the global pipeline manager instance."""
    return pipeline_manager