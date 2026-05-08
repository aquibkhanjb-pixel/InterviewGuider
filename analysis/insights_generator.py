import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import logging
from analysis.topic_extractor import AdvancedTopicExtractor
from analysis.ml_scorer import tfidf_rerank


class CompanyInsightsGenerator:
    """
    Advanced company insights generator with statistical analysis,
    trend detection, and personalized recommendations.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.topic_extractor = AdvancedTopicExtractor()

        # Statistical thresholds
        self.min_sample_size = 3
        self.confidence_threshold = 0.7
        self.trend_significance_threshold = 0.15

    def _assess_data_quality(self, experience_analyses: List[Dict]) -> Dict:
        """
        Assess the quality of the data for insights generation.
        
        Args:
            experience_analyses: List of analyzed experiences
            
        Returns:
            Data quality assessment
        """
        if not experience_analyses:
            return {
                'quality_score': 0.0,
                'sample_adequacy': 'insufficient',
                'confidence_level': 'none',
                'data_issues': ['No experiences available'],
                'recommendations': ['Collect more interview experiences']
            }
        
        # Calculate quality metrics
        total_experiences = len(experience_analyses)
        
        # Assess content quality
        content_lengths = []
        confidence_scores = []
        topic_counts = []
        
        for analysis in experience_analyses:
            # Content length assessment
            exp_meta = analysis.get('experience_metadata', {})
            content = exp_meta.get('content', '')
            content_lengths.append(len(content))
            
            # Topic analysis quality
            topics = analysis.get('topics', {})
            topic_counts.append(len(topics))
            
            # Overall confidence from topic extraction
            analysis_meta = analysis.get('analysis_metadata', {})
            confidence_scores.append(analysis_meta.get('confidence_score', 0.0))
        
        # Calculate quality metrics
        avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        avg_topics_per_exp = sum(topic_counts) / len(topic_counts) if topic_counts else 0
        
        # Assess sample adequacy
        if total_experiences >= 15:
            sample_adequacy = 'excellent'
        elif total_experiences >= 8:
            sample_adequacy = 'good' 
        elif total_experiences >= 5:
            sample_adequacy = 'adequate'
        elif total_experiences >= 3:
            sample_adequacy = 'minimal'
        else:
            sample_adequacy = 'insufficient'
        
        # Calculate overall quality score (0-1)
        content_score = min(avg_content_length / 500, 1.0)  # 500+ chars = good
        confidence_score = avg_confidence
        topic_score = min(avg_topics_per_exp / 5, 1.0)  # 5+ topics = good
        sample_score = min(total_experiences / 15, 1.0)  # 15+ experiences = excellent
        
        quality_score = (content_score + confidence_score + topic_score + sample_score) / 4
        
        # Determine confidence level
        if quality_score >= 0.8:
            confidence_level = 'high'
        elif quality_score >= 0.6:
            confidence_level = 'medium'
        elif quality_score >= 0.4:
            confidence_level = 'low'
        else:
            confidence_level = 'very_low'
        
        # Identify data issues
        data_issues = []
        recommendations = []
        
        if avg_content_length < 200:
            data_issues.append('Short experience descriptions')
            recommendations.append('Collect more detailed interview experiences')
        
        if avg_confidence < 0.5:
            data_issues.append('Low topic extraction confidence')
            recommendations.append('Improve content quality or extraction algorithms')
        
        if avg_topics_per_exp < 2:
            data_issues.append('Few topics per experience')
            recommendations.append('Target more technical interview experiences')
        
        if total_experiences < 5:
            data_issues.append('Small sample size')
            recommendations.append('Collect more experiences for statistical significance')
        
        return {
            'quality_score': round(quality_score, 2),
            'sample_adequacy': sample_adequacy,
            'confidence_level': confidence_level,
            'sample_size': total_experiences,
            'avg_content_length': round(avg_content_length),
            'avg_confidence': round(avg_confidence, 2),
            'avg_topics_per_experience': round(avg_topics_per_exp, 1),
            'data_issues': data_issues,
            'recommendations': recommendations
        }

    
    def generate_comprehensive_insights(self, company_name: str, experiences: List[Dict]) -> Dict:
        """
        Generate comprehensive company insights from interview experiences.
        
        Args:
            company_name: Name of the company
            experiences: List of interview experience dictionaries
            
        Returns:
            Comprehensive insights with statistical backing
        """
        if len(experiences) < self.min_sample_size:
            return self._insufficient_data_response(company_name, len(experiences))
        
        self.logger.info(f"Generating insights for {company_name} from {len(experiences)} experiences")

        # Extract topics from all experiences
        experience_analyses = []
        for exp in experiences:
            analysis = self.topic_extractor.extract_topics_from_experience(exp)
            analysis['experience_metadata'] = exp
            experience_analyses.append(analysis)

        # Generate comprehensive insights
        insights = {
            'company': company_name,
            'analysis_date': datetime.utcnow().isoformat(),
            'sample_size': len(experiences),
            'data_quality': self._assess_data_quality(experience_analyses),

            # Core insights
            'topic_insights': self._generate_topic_insights(experience_analyses),
            'difficulty_analysis': self._analyze_difficulty_trends(experience_analyses),
            'interview_process_insights': self._analyze_interview_process(experience_analyses),
            'temporal_trends': self._analyze_temporal_trends(experience_analyses),

            # Actionable recommendations
            'study_recommendations': self._generate_study_recommendations(experience_analyses),
            'preparation_strategy': self._generate_preparation_strategy(experience_analyses),
            'success_factors': self._identify_success_factors(experience_analyses),

            # Advanced analytics
            'statistical_confidence': self._calculate_statistical_confidence(experience_analyses),
            'comparative_analysis': self._generate_comparative_insights(company_name, experience_analyses),

        }

        return insights
    
    def _generate_topic_insights(self, analyses: List[Dict]) -> Dict:
        """Generate detailed topic insights with statistical backing."""
        # Aggregate all topics
        topic_frequencies = defaultdict(list)
        topic_importances = defaultdict(list)
        topic_confidence_scores = defaultdict(list)
        topic_semantic_scores = defaultdict(list)

        total_weight = 0
        for analysis in analyses:
            exp_weight = analysis['experience_metadata'].get('time_weight', 1.0)
            total_weight += exp_weight

            for topic, data in analysis['topics'].items():
                topic_frequencies[topic].append(data['frequency_percent'] * exp_weight)
                topic_importances[topic].append(data['importance_score'] * exp_weight)
                topic_confidence_scores[topic].append(data['confidence'])
                sem = data.get('semantic_confidence')
                if sem is not None:
                    topic_semantic_scores[topic].append(sem)

        # Calculate comprehensive statistics
        topic_insights = {}
        for topic in topic_frequencies.keys():
            frequencies = topic_frequencies[topic]
            importances = topic_importances[topic]
            confidences = topic_confidence_scores[topic]

            # Statistical calculations
            weighted_frequency = sum(frequencies) / total_weight * 100
            avg_importance = np.mean(importances)
            avg_confidence = np.mean(confidences)

            # Frequency statistics — use the already-weighted values directly
            freq_std = float(np.std(frequencies)) if len(frequencies) > 1 else 0.0

            # Averaged semantic confidence (None when model unavailable)
            sem_list = topic_semantic_scores[topic]
            avg_semantic = round(float(np.mean(sem_list)), 3) if sem_list else None

            # Determine priority level
            priority = self._determine_priority_level(weighted_frequency, avg_importance, avg_confidence)

            # Generate actionable insight
            category = topic.split('.')[0]
            topic_name = topic.split('.')[1].replace('_', ' ').title()

            topic_insights[topic] = {
                'topic_name': topic_name,
                'category': category,
                'weighted_frequency': round(weighted_frequency, 1),
                'average_importance': round(avg_importance, 2),
                'confidence_score': round(avg_confidence, 2),
                'semantic_confidence': avg_semantic,
                'frequency_std_dev': round(freq_std, 2),
                'priority_level': priority,
                'mentions_count': len(frequencies),
                'actionable_insight': self._generate_topic_actionable_insight(
                    topic_name, weighted_frequency, priority, len(frequencies)
                ),
                'study_resources': self._generate_study_resources(topic, category),
                'difficulty_assessment': self._assess_topic_difficulty(topic, analyses)
            }
        
        # Apply TF-IDF re-ranking: topics common to this company but not trivially
        # present in every experience rise above universally-mentioned topics.
        n_exp = len(analyses)
        topic_insights = tfidf_rerank(topic_insights, n_exp)

        return {
            'detailed_topics': topic_insights,
            'top_5_topics': list(topic_insights.keys())[:5],
            'high_priority_topics': [t for t, d in topic_insights.items()
                                     if d['priority_level'] == 'HIGH'],
            'topic_distribution': self._calculate_topic_distribution(topic_insights)
        }
    
    def _determine_priority_level(self, frequency: float, importance: float, confidence: float) -> str:
        """Determine priority level based on how often the topic appears across interviews."""
        if frequency >= 40:
            return 'HIGH'
        elif frequency >= 20:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_topic_actionable_insight(self, topic_name: str, frequency: float, 
                                         priority: str, mentions: int) -> str:
        """Generate actionable insight for a topic."""
        if priority == 'HIGH':
            return f"🔥 CRITICAL: {topic_name} appears in {frequency:.1f}% of interviews - prioritize this heavily"
        elif priority == 'MEDIUM':
            return f"⚡ IMPORTANT: {topic_name} mentioned in {frequency:.1f}% of cases - solid preparation needed"
        else:
            return f"💡 MODERATE: {topic_name} occasionally mentioned ({frequency:.1f}%) - good to review"
    
    def _generate_study_resources(self, topic: str, category: str) -> Dict:
        """Generate study resources for specific topics."""
        resources = {
            'practice_problems': [],
            'study_materials': [],
            'estimated_study_time': '2-3 days'
        }
        
        # Topic-specific resources
        topic_name = topic.split('.')[1]
        
        if category == 'algorithms':
            if 'dynamic_programming' in topic:
                resources['practice_problems'] = [
                    'LeetCode: Climbing Stairs',
                    'LeetCode: House Robber',
                    'LeetCode: Coin Change',
                    'LeetCode: Longest Common Subsequence'
                ]
                resources['estimated_study_time'] = '5-7 days'
            elif 'searching' in topic:
                resources['practice_problems'] = [
                    'LeetCode: Binary Search',
                    'LeetCode: Search in Rotated Sorted Array',
                    'LeetCode: Find Peak Element'
                ]
        
        elif category == 'data_structures':
            if 'tree' in topic:
                resources['practice_problems'] = [
                    'LeetCode: Binary Tree Inorder Traversal',
                    'LeetCode: Maximum Depth of Binary Tree',
                    'LeetCode: Validate Binary Search Tree'
                ]
        
        elif category == 'system_design':
            resources['study_materials'] = [
                'Designing Data-Intensive Applications',
                'System Design Interview by Alex Xu',
                'High Scalability blog'
            ]
            resources['estimated_study_time'] = '7-10 days'
        
        return resources
    
    def _analyze_difficulty_trends(self, analyses: List[Dict]) -> Dict:
        """Analyze difficulty trends across experiences."""
        difficulty_data = []
        
        for analysis in analyses:
            if 'difficulty_assessment' in analysis:
                difficulty_data.append(analysis['difficulty_assessment'])
        
        if not difficulty_data:
            return {'overall_trend': 'unknown', 'confidence': 0}
        
        # Aggregate difficulty scores
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        total_confidence = 0
        
        for diff_data in difficulty_data:
            if diff_data['overall_difficulty'] != 'unknown':
                difficulty_counts[diff_data['overall_difficulty']] += 1
                total_confidence += diff_data['confidence']
        
        total_assessments = sum(difficulty_counts.values())
        avg_confidence = total_confidence / len(difficulty_data) if difficulty_data else 0
        
        # Determine trend
        if total_assessments > 0:
            primary_difficulty = max(difficulty_counts, key=difficulty_counts.get)
            difficulty_percentage = (difficulty_counts[primary_difficulty] / total_assessments) * 100
        else:
            primary_difficulty = 'unknown'
            difficulty_percentage = 0
        
        return {
            'primary_difficulty': primary_difficulty,
            'difficulty_percentage': round(difficulty_percentage, 1),
            'difficulty_distribution': difficulty_counts,
            'average_confidence': round(avg_confidence, 2),
            'trend_insight': self._generate_difficulty_insight(primary_difficulty, difficulty_percentage)
        }
    def _insufficient_data_response(self, company_name: str, experience_count: int) -> Dict:
        """Generate response for insufficient data scenarios."""
        return {
            'company': company_name,
            'analysis_date': datetime.utcnow().isoformat(),
            'status': 'insufficient_data',
            'message': f'Only {experience_count} experiences available. Need at least {self.min_sample_size} for analysis.',
            'sample_size': experience_count,
            'data_quality': {
                'quality_score': 0.0,
                'sample_adequacy': 'insufficient',
                'confidence_level': 'none'
            },
            'recommendations': [
                'Collect more interview experiences',
                'Try different scraping sources',
                'Wait for more data to accumulate'
            ]
        }
    
    def _generate_difficulty_insight(self, difficulty: str, percentage: float) -> str:
        """Generate insight about difficulty trends."""
        if difficulty == 'hard':
            return f"⚠️ Challenging interviews: {percentage:.1f}% report high difficulty - thorough preparation essential"
        elif difficulty == 'medium':
            return f"📊 Balanced difficulty: {percentage:.1f}% find interviews moderately challenging"
        elif difficulty == 'easy':
            return f"✅ Approachable interviews: {percentage:.1f}% report manageable difficulty levels"
        else:
            return "❓ Mixed difficulty reports - prepare for various complexity levels"
        

    # Add these methods to your insights_generator.py file

    def _assess_topic_difficulty(self, topic: str, analyses: List[Dict]) -> Dict:
        """Assess difficulty level for a specific topic."""
        topic_difficulties = []
        
        for analysis in analyses:
            if topic in analysis.get('topics', {}):
                # Get difficulty from the experience's difficulty assessment
                difficulty_data = analysis.get('difficulty_assessment', {})
                if difficulty_data.get('overall_difficulty') != 'unknown':
                    topic_difficulties.append(difficulty_data['overall_difficulty'])
        
        if not topic_difficulties:
            return {
                'assessment': 'unknown',
                'confidence': 0.0,
                'distribution': {'easy': 0, 'medium': 0, 'hard': 0}
            }
        
        # Count difficulty levels
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        for diff in topic_difficulties:
            if diff in difficulty_counts:
                difficulty_counts[diff] += 1
        
        # Determine primary difficulty
        primary_difficulty = max(difficulty_counts, key=difficulty_counts.get)
        total_assessments = sum(difficulty_counts.values())
        confidence = difficulty_counts[primary_difficulty] / total_assessments if total_assessments > 0 else 0
        
        return {
            'assessment': primary_difficulty,
            'confidence': round(confidence, 2),
            'distribution': difficulty_counts,
            'sample_size': len(topic_difficulties)
        }

    def _calculate_topic_distribution(self, sorted_insights: Dict) -> Dict:
        """Calculate distribution of topics across categories."""
        category_distribution = defaultdict(int)
        priority_distribution = defaultdict(int)
        
        for topic_data in sorted_insights.values():
            category_distribution[topic_data['category']] += 1
            priority_distribution[topic_data['priority_level']] += 1
        
        total_topics = len(sorted_insights)
        
        return {
            'by_category': {
                category: {
                    'count': count,
                    'percentage': round((count / total_topics) * 100, 1)
                }
                for category, count in category_distribution.items()
            },
            'by_priority': {
                priority: {
                    'count': count,
                    'percentage': round((count / total_topics) * 100, 1)
                }
                for priority, count in priority_distribution.items()
            },
            'total_topics': total_topics
        }

    def _analyze_interview_process(self, analyses: List[Dict]) -> Dict:
        """Analyze interview process patterns."""
        round_data = defaultdict(int)
        process_insights = []
        
        for analysis in analyses:
            # Get interview round information
            interview_rounds = analysis.get('interview_rounds', {})
            for round_type, round_info in interview_rounds.items():
                if round_info.get('confidence', 0) > 0.5:
                    round_data[round_type] += 1
        
        total_experiences = len(analyses)
        
        # Generate insights about common rounds
        common_rounds = []
        for round_type, count in round_data.items():
            frequency = (count / total_experiences) * 100
            if frequency > 30:  # Appears in >30% of interviews
                common_rounds.append({
                    'round_type': round_type.replace('_', ' ').title(),
                    'frequency_percent': round(frequency, 1),
                    'count': count
                })
        
        # Sort by frequency
        common_rounds.sort(key=lambda x: x['frequency_percent'], reverse=True)
        
        return {
            'common_rounds': common_rounds,
            'total_round_types': len(round_data),
            'process_insight': f"Most interviews include {len(common_rounds)} common round types" if common_rounds else "Varied interview processes",
            'round_distribution': dict(round_data)
        }

    def _analyze_temporal_trends(self, analyses: List[Dict]) -> Dict:
        """Analyze trends over time."""
        # Group experiences by time periods
        recent_experiences = []
        older_experiences = []
        
        now = datetime.utcnow()
        six_months_ago = now - timedelta(days=180)
        
        for analysis in analyses:
            exp_date = analysis['experience_metadata'].get('experience_date', now)
            if isinstance(exp_date, str):
                try:
                    exp_date = datetime.fromisoformat(exp_date.replace('Z', '+00:00'))
                except:
                    exp_date = now
            
            if exp_date > six_months_ago:
                recent_experiences.append(analysis)
            else:
                older_experiences.append(analysis)
        
        if len(recent_experiences) < 2 or len(older_experiences) < 2:
            return {
                'trend_available': False,
                'message': 'Insufficient data for temporal analysis',
                'recent_count': len(recent_experiences),
                'older_count': len(older_experiences)
            }
        
        # Compare recent vs older patterns
        recent_topics = defaultdict(int)
        older_topics = defaultdict(int)
        
        for analysis in recent_experiences:
            for topic in analysis.get('topics', {}):
                recent_topics[topic] += 1
        
        for analysis in older_experiences:
            for topic in analysis.get('topics', {}):
                older_topics[topic] += 1
        
        # Find trending topics
        trending_up = []
        trending_down = []
        
        all_topics = set(recent_topics.keys()) | set(older_topics.keys())
        
        for topic in all_topics:
            recent_freq = recent_topics[topic] / len(recent_experiences)
            older_freq = older_topics[topic] / len(older_experiences) if older_experiences else 0
            
            change = recent_freq - older_freq
            
            if abs(change) > 0.2:  # Significant change threshold
                topic_name = topic.split('.')[1].replace('_', ' ').title()
                if change > 0:
                    trending_up.append({
                        'topic': topic_name,
                        'change': round(change * 100, 1)
                    })
                else:
                    trending_down.append({
                        'topic': topic_name,
                        'change': round(abs(change) * 100, 1)
                    })
        
        return {
            'trend_available': True,
            'recent_period': f"Last 6 months ({len(recent_experiences)} experiences)",
            'older_period': f"Earlier period ({len(older_experiences)} experiences)",
            'trending_up': sorted(trending_up, key=lambda x: x['change'], reverse=True)[:3],
            'trending_down': sorted(trending_down, key=lambda x: x['change'], reverse=True)[:3],
            'stability_insight': "Interview patterns remain relatively stable" if not (trending_up or trending_down) else "Notable shifts in interview focus detected"
        }

    def _generate_study_recommendations(self, analyses: List[Dict]) -> Dict:
        """Generate study recommendations based on analysis."""
        # Get top topics from analysis
        all_topics = defaultdict(int)
        for analysis in analyses:
            for topic in analysis.get('topics', {}):
                all_topics[topic] += 1
        
        # Sort by frequency
        sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = {
            'immediate_focus': [],
            'secondary_focus': [],
            'study_schedule': {},
            'resource_allocation': {}
        }
        
        # Immediate focus (top 3 topics)
        for i, (topic, count) in enumerate(sorted_topics[:3]):
            category = topic.split('.')[0]
            topic_name = topic.split('.')[1].replace('_', ' ').title()
            frequency = (count / len(analyses)) * 100
            
            recommendations['immediate_focus'].append({
                'topic': topic_name,
                'category': category,
                'frequency': round(frequency, 1),
                'study_hours': 15 if category == 'algorithms' else 10,
                'priority': 'HIGH' if i == 0 else 'MEDIUM'
            })
        
        # Secondary focus (next 3 topics)
        for topic, count in sorted_topics[3:6]:
            category = topic.split('.')[0]
            topic_name = topic.split('.')[1].replace('_', ' ').title()
            frequency = (count / len(analyses)) * 100
            
            recommendations['secondary_focus'].append({
                'topic': topic_name,
                'category': category,
                'frequency': round(frequency, 1),
                'study_hours': 8,
                'priority': 'LOW'
            })
        
        return recommendations

    def _generate_preparation_strategy(self, analyses: List[Dict]) -> Dict:
        """Generate comprehensive preparation strategy."""
        # Analyze difficulty distribution
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        
        for analysis in analyses:
            difficulty = analysis.get('difficulty_assessment', {}).get('overall_difficulty', 'unknown')
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
        
        total_with_difficulty = sum(difficulty_counts.values())
        
        strategy = {
            'difficulty_focus': 'unknown',
            'preparation_timeline': '4-6 weeks',
            'practice_distribution': {},
            'key_recommendations': []
        }
        
        if total_with_difficulty > 0:
            primary_difficulty = max(difficulty_counts, key=difficulty_counts.get)
            strategy['difficulty_focus'] = primary_difficulty
            
            if primary_difficulty == 'hard':
                strategy['preparation_timeline'] = '6-8 weeks'
                strategy['practice_distribution'] = {
                    'hard_problems': '50%',
                    'medium_problems': '35%',
                    'easy_problems': '15%'
                }
                strategy['key_recommendations'] = [
                    'Focus heavily on advanced algorithms and system design',
                    'Practice complex problem-solving patterns',
                    'Prepare for multiple rounds of technical interviews'
                ]
            elif primary_difficulty == 'medium':
                strategy['preparation_timeline'] = '4-6 weeks'
                strategy['practice_distribution'] = {
                    'medium_problems': '60%',
                    'hard_problems': '25%',
                    'easy_problems': '15%'
                }
                strategy['key_recommendations'] = [
                    'Balance breadth and depth in technical preparation',
                    'Focus on common algorithm patterns',
                    'Practice coding under time pressure'
                ]
            else:  # easy
                strategy['preparation_timeline'] = '3-4 weeks'
                strategy['practice_distribution'] = {
                    'easy_problems': '40%',
                    'medium_problems': '50%',
                    'hard_problems': '10%'
                }
                strategy['key_recommendations'] = [
                    'Focus on fundamentals and clean code',
                    'Practice explaining your thought process',
                    'Review basic data structures and algorithms'
                ]
        
        return strategy

    def _identify_success_factors(self, analyses: List[Dict]) -> Dict:
        """Identify factors that correlate with success."""
        successful_experiences = []
        unsuccessful_experiences = []
        
        for analysis in analyses:
            outcome = analysis['experience_metadata'].get('outcome', 'unknown')
            if outcome == 'offer':
                successful_experiences.append(analysis)
            elif outcome == 'rejected':
                unsuccessful_experiences.append(analysis)
        
        success_factors = {
            'sample_sizes': {
                'successful': len(successful_experiences),
                'unsuccessful': len(unsuccessful_experiences),
                'unknown': len(analyses) - len(successful_experiences) - len(unsuccessful_experiences)
            },
            'success_patterns': [],
            'failure_patterns': [],
            'confidence': 'low'
        }
        
        if len(successful_experiences) >= 2 and len(unsuccessful_experiences) >= 2:
            # Analyze topic patterns in successful vs unsuccessful interviews
            success_topics = defaultdict(int)
            failure_topics = defaultdict(int)
            
            for analysis in successful_experiences:
                for topic in analysis.get('topics', {}):
                    success_topics[topic] += 1
            
            for analysis in unsuccessful_experiences:
                for topic in analysis.get('topics', {}):
                    failure_topics[topic] += 1
            
            # Find differentiating factors
            for topic in success_topics:
                success_rate = success_topics[topic] / len(successful_experiences)
                failure_rate = failure_topics.get(topic, 0) / len(unsuccessful_experiences)
                
                if success_rate - failure_rate > 0.3:  # Significant difference
                    topic_name = topic.split('.')[1].replace('_', ' ').title()
                    success_factors['success_patterns'].append({
                        'factor': topic_name,
                        'success_rate': round(success_rate * 100, 1),
                        'difference': round((success_rate - failure_rate) * 100, 1)
                    })
            
            success_factors['confidence'] = 'medium' if len(success_factors['success_patterns']) > 0 else 'low'
        
        return success_factors

    def _calculate_statistical_confidence(self, analyses: List[Dict]) -> Dict:
        """Calculate overall statistical confidence in the analysis."""
        sample_size = len(analyses)
        
        # Confidence based on sample size
        if sample_size >= 20:
            sample_confidence = 0.9
        elif sample_size >= 10:
            sample_confidence = 0.7
        elif sample_size >= 5:
            sample_confidence = 0.5
        else:
            sample_confidence = 0.3
        
        # Confidence based on data quality
        total_topics = sum(len(analysis.get('topics', {})) for analysis in analyses)
        avg_topics_per_exp = total_topics / sample_size if sample_size > 0 else 0
        
        if avg_topics_per_exp >= 5:
            quality_confidence = 0.9
        elif avg_topics_per_exp >= 3:
            quality_confidence = 0.7
        elif avg_topics_per_exp >= 2:
            quality_confidence = 0.5
        else:
            quality_confidence = 0.3
        
        # Overall confidence
        overall_confidence = (sample_confidence + quality_confidence) / 2
        
        return {
            'overall_score': round(overall_confidence, 2),
            'sample_size_confidence': round(sample_confidence, 2),
            'data_quality_confidence': round(quality_confidence, 2),
            'confidence_level': 'high' if overall_confidence >= 0.7 else 'medium' if overall_confidence >= 0.5 else 'low',
            'factors': {
                'sample_size': sample_size,
                'avg_topics_per_experience': round(avg_topics_per_exp, 1)
            }
        }

    def _generate_comparative_insights(self, company_name: str, analyses: List[Dict]) -> Dict:
        """Generate comparative insights (placeholder for now)."""
        return {
            'comparison_available': False,
            'message': 'Comparative analysis requires data from multiple companies',
            'current_company': company_name,
            'sample_size': len(analyses)
        }

