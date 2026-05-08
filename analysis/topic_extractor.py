import re
import math
import nltk
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
from datetime import datetime
import logging

# Download required NLTK data — must succeed before the imports below
_NLTK_PACKAGES = ['punkt', 'punkt_tab', 'stopwords']
for _pkg in _NLTK_PACKAGES:
    try:
        nltk.data.find(f'tokenizers/{_pkg}' if 'punkt' in _pkg else f'corpora/{_pkg}')
    except LookupError:
        try:
            nltk.download(_pkg, quiet=True)
        except Exception:
            pass  # will fail at runtime if truly unavailable

try:
    from nltk.corpus import stopwords as _nltk_stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    _NLTK_AVAILABLE = True
except Exception:
    _NLTK_AVAILABLE = False
    _nltk_stopwords = None
    def word_tokenize(text): return text.split()
    def sent_tokenize(text): return [text]

class AdvancedTopicExtractor:
    """
    Sophisticated topic extraction using multiple NLP techniques:
    1. Technical keyword dictionary with synonyms
    2. Context-aware pattern matching
    3. TF-IDF style importance scoring
    4. Difficulty level assessment
    5. Interview round classification
    6. Semantic confidence scoring (sentence-transformers, optional)
    """

    _FALLBACK_STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'this', 'that', 'these', 'those', 'it',
        'as', 'at', 'its', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'out', 'off', 'over', 'then',
        'there', 'when', 'where', 'which', 'who', 'whom', 'what', 'if', 'not',
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.stop_words = set(_nltk_stopwords.words('english')) if (_NLTK_AVAILABLE and _nltk_stopwords) else self._FALLBACK_STOPWORDS
        except Exception:
            self.stop_words = self._FALLBACK_STOPWORDS

        # Initialize comprehensive keyword dictionary
        self.technical_keywords = self._build_keyword_dictionary()

        # Flatten for quick lookup
        self.keyword_lookup = self._create_lookup_table()

        # Reverse map: "category.topic" → list of keywords (for semantic scorer)
        self.topic_keywords_map = {
            f"{cat}.{sub}": kws
            for cat, subcats in self.technical_keywords.items()
            for sub, kws in subcats.items()
        }

        # Context patterns for better detection
        self.context_patterns = self._build_context_patterns()

        # Difficulty indicators
        self.difficulty_patterns = self._build_difficulty_patterns()
    
    def _build_keyword_dictionary(self) -> Dict[str, Dict[str, List[str]]]:
        """Build comprehensive technical keyword dictionary."""
        return {
            'data_structures': {
                'array': ['array', 'arrays', 'list', 'arraylist', 'vector', '1d array', '2d array'],
                'linked_list': ['linked list', 'linkedlist', 'singly linked', 'doubly linked', 'circular linked'],
                'stack': ['stack', 'stacks', 'lifo', 'push', 'pop', 'stack overflow'],
                'queue': ['queue', 'queues', 'fifo', 'enqueue', 'dequeue', 'circular queue', 'priority queue'],
                'tree': ['tree', 'trees', 'binary tree', 'bst', 'binary search tree', 'balanced tree', 'avl tree', 'red black tree'],
                'heap': ['heap', 'heaps', 'min heap', 'max heap', 'binary heap', 'heapify'],
                'hash_table': ['hash', 'hashmap', 'hash table', 'hash set', 'dictionary', 'map', 'hashtable'],
                'graph': ['graph', 'graphs', 'vertices', 'edges', 'adjacency', 'directed graph', 'undirected graph', 'weighted graph'],
                'trie': ['trie', 'prefix tree', 'suffix tree', 'radix tree']
            },
            'algorithms': {
                'sorting': ['sort', 'sorting', 'merge sort', 'quick sort', 'heap sort', 'bubble sort', 'insertion sort', 'selection sort'],
                'searching': ['search', 'binary search', 'linear search', 'dfs', 'bfs', 'depth first', 'breadth first'],
                'dynamic_programming': ['dynamic programming', 'dp', 'memoization', 'tabulation', 'optimal substructure', 'overlapping subproblems'],
                'greedy': ['greedy', 'greedy algorithm', 'greedy approach', 'local optimum'],
                'recursion': ['recursion', 'recursive', 'backtracking', 'divide and conquer'],
                'two_pointers': ['two pointer', 'two pointers', 'sliding window', 'fast slow pointer'],
                'string_algorithms': ['string', 'substring', 'string matching', 'kmp', 'rabin karp', 'string manipulation']
            },
            'system_design': {
                'scalability': ['scalability', 'scale', 'scaling', 'horizontal scaling', 'vertical scaling', 'scale out', 'scale up'],
                'load_balancer': ['load balancer', 'load balancing', 'nginx', 'haproxy', 'round robin'],
                'database': ['database', 'sql', 'nosql', 'mongodb', 'mysql', 'postgresql', 'cassandra', 'dynamodb'],
                'caching': ['cache', 'caching', 'redis', 'memcached', 'cdn', 'content delivery network'],
                'microservices': ['microservice', 'microservices', 'api', 'rest api', 'service oriented', 'distributed systems'],
                'messaging': ['queue', 'kafka', 'rabbitmq', 'pub sub', 'message queue', 'event driven'],
                'consistency': ['consistency', 'acid', 'cap theorem', 'eventual consistency', 'strong consistency']
            },
            'programming_concepts': {
                'oop': ['oop', 'object oriented', 'inheritance', 'polymorphism', 'encapsulation', 'abstraction'],
                'concurrency': ['thread', 'threading', 'concurrency', 'parallel', 'async', 'synchronization', 'mutex', 'semaphore'],
                'design_patterns': ['singleton', 'factory', 'observer', 'decorator', 'strategy', 'builder', 'adapter'],
                'complexity': ['time complexity', 'space complexity', 'big o', 'o(n)', 'o(log n)', 'o(n^2)', 'complexity analysis']
            },
            'technologies': {
                'languages': ['java', 'python', 'c++', 'cpp', 'javascript', 'go', 'rust', 'scala', 'kotlin'],
                'frameworks': ['spring', 'django', 'react', 'angular', 'express', 'flask', 'nodejs'],
                'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ec2', 's3', 'lambda'],
                'databases': ['mysql', 'postgresql', 'mongodb', 'cassandra', 'dynamodb', 'elasticsearch']
            }
        }
    
    def _create_lookup_table(self) -> Dict[str, Dict]:
        """Create flattened lookup table for quick keyword matching."""
        lookup = {}
        
        for category, subcategories in self.technical_keywords.items():
            for topic, keywords in subcategories.items():
                for keyword in keywords:
                    lookup[keyword.lower()] = {
                        'category': category,
                        'topic': topic,
                        'canonical': keywords[0]  # First keyword is canonical
                    }
        
        return lookup
    
    def _build_context_patterns(self) -> Dict[str, List[str]]:
        """Build context patterns for better topic detection."""
        return {
            'algorithm_discussion': [
                r'implement(?:ed|ing)?\s+(\w+(?:\s+\w+){0,2})',
                r'(?:write|code|solve)\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})\s+(?:algorithm|solution)',
                r'(?:asked|given)\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})\s+(?:problem|question)'
            ],
            'data_structure_usage': [
                r'us(?:e|ed|ing)\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})',
                r'implement(?:ed|ing)?\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})',
                r'(?:maintain|store|keep)\s+(?:data|elements|items)\s+in\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})'
            ],
            'system_design_discussion': [
                r'design(?:ed|ing)?\s+(?:a|an)?\s*(\w+(?:\s+\w+){0,2})\s+(?:system|service|application)',
                r'(?:scale|scaling)\s+(?:the\s+)?(\w+(?:\s+\w+){0,2})',
                r'(?:handle|managing)\s+(\w+(?:\s+\w+){0,2})\s+(?:load|traffic|requests)'
            ]
        }
    
    def _build_difficulty_patterns(self) -> Dict[str, List[str]]:
        """Build patterns to assess topic difficulty."""
        return {
            'easy': [
                r'(?:simple|easy|basic|straightforward|trivial)',
                r'(?:beginner|junior|entry.level)',
                r'(?:took|solved|finished)\s+(?:quickly|fast|easily)'
            ],
            'medium': [
                r'(?:medium|moderate|intermediate|standard)',
                r'(?:took|required)\s+(?:some|considerable)\s+(?:time|thought|effort)',
                r'(?:tricky|challenging)\s+(?:but|however)\s+(?:manageable|doable)'
            ],
            'hard': [
                r'(?:hard|difficult|challenging|tough|complex|advanced)',
                r'(?:struggled|difficulty|trouble|hard time)',
                r'(?:senior|experienced|expert).level',
                r'(?:took|required)\s+(?:long|much|lot of)\s+(?:time|effort|thinking)'
            ]
        }
    
    def extract_topics_from_experience(self, experience_data: Dict) -> Dict:
        """
        Extract topics from interview experience using advanced NLP techniques.
        
        Args:
            experience_data: Dictionary containing experience content and metadata
            
        Returns:
            Comprehensive topic analysis results
        """
        content = experience_data.get('content', '')
        title = experience_data.get('title', '')
        experience_date = experience_data.get('experience_date', datetime.utcnow())
        
        if not content:
            return {'topics': {}, 'analysis': {}}
        
        # Preprocess text
        combined_text = f"{title} {content}"
        processed_text = self._preprocess_text(combined_text)
        
        # Multiple extraction methods
        keyword_topics = self._extract_by_keywords(processed_text)
        context_topics = self._extract_by_context(processed_text)
        pattern_topics = self._extract_by_patterns(processed_text)
        
        # Merge and score topics
        all_topics = self._merge_topic_extractions(keyword_topics, context_topics, pattern_topics)
        scored_topics = self._calculate_topic_scores(all_topics, processed_text, experience_date)
        
        # Additional analysis
        difficulty_assessment = self._assess_difficulty(processed_text)
        interview_rounds = self._classify_interview_rounds(processed_text)
        key_insights = self._extract_key_insights(processed_text)
        
        return {
            'topics': scored_topics,
            'difficulty_assessment': difficulty_assessment,
            'interview_rounds': interview_rounds,
            'key_insights': key_insights,
            'analysis_metadata': {
                'total_topics_found': len(scored_topics),
                'text_length': len(processed_text),
                'processing_date': datetime.utcnow(),
                'confidence_score': self._calculate_overall_confidence(scored_topics)
            }
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better analysis."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces and periods
        text = re.sub(r'[^\w\s\.]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_by_keywords(self, text: str) -> Dict[str, int]:
        """Extract topics using direct keyword matching."""
        topics = defaultdict(int)
        
        for keyword, info in self.keyword_lookup.items():
            # Use word boundary matching for better accuracy
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text)
            
            if matches:
                topic_key = f"{info['category']}.{info['topic']}"
                topics[topic_key] += len(matches)
        
        return dict(topics)
    
    def _extract_by_context(self, text: str) -> Dict[str, int]:
        """Extract topics using context patterns."""
        topics = defaultdict(int)
        
        for context_type, patterns in self.context_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Extract the captured term
                    if match.groups():
                        term = match.group(1).strip()
                        
                        # Check if term matches our keywords
                        for keyword, info in self.keyword_lookup.items():
                            if keyword in term or term in keyword:
                                topic_key = f"{info['category']}.{info['topic']}"
                                topics[topic_key] += 1
        
        return dict(topics)
    
    def _extract_by_patterns(self, text: str) -> Dict[str, int]:
        """Extract topics using advanced pattern matching."""
        topics = defaultdict(int)
        
        # Advanced patterns for specific concepts
        advanced_patterns = {
            'algorithms.dynamic_programming': [
                r'dp\s*\[',
                r'memoization|tabulation',
                r'optimal substructure',
                r'overlapping subproblems',
                r'knapsack|lis|lcs|edit.distance'
            ],
            'algorithms.two_pointers': [
                r'two.pointer',
                r'left.*right.*pointer',
                r'sliding.window',
                r'fast.*slow.*pointer'
            ],
            'system_design.scalability': [
                r'horizontal.*scaling',
                r'vertical.*scaling',
                r'scale.*million.*users',
                r'handle.*concurrent.*requests',
                r'load.*balancing'
            ],
            'data_structures.tree': [
                r'binary.*search.*tree',
                r'left.*child.*right.*child',
                r'root.*node.*leaf',
                r'inorder.*preorder.*postorder',
                r'tree.*traversal'
            ]
        }
        
        for topic, patterns in advanced_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                if matches > 0:
                    topics[topic] += matches
        
        return dict(topics)
    
    def _merge_topic_extractions(self, *extractions) -> Dict[str, int]:
        """Merge results from multiple extraction methods."""
        merged = defaultdict(int)
        
        for extraction in extractions:
            for topic, count in extraction.items():
                merged[topic] += count
        
        return dict(merged)
    
    # Max topics that get the expensive semantic-confidence encode call.
    # Keeps Render free-tier inference time under ~10 s per experience.
    _MAX_SEMANTIC_TOPICS = 5

    def _calculate_topic_scores(self, topics: Dict[str, int], text: str, experience_date: datetime) -> Dict[str, Dict]:
        """Calculate comprehensive topic scores."""
        from analysis.ml_scorer import SemanticConfidenceScorer

        scored_topics = {}
        text_words = len(text.split())

        # Only run the expensive semantic encode for the top-N most frequent topics.
        top_topics_for_semantic = set(
            t for t, _ in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:self._MAX_SEMANTIC_TOPICS]
        )

        from utils.time_utils import ExponentialDecayCalculator
        decay_calc = ExponentialDecayCalculator()

        for topic, raw_count in topics.items():
            # Basic frequency
            frequency = (raw_count / text_words) * 100 if text_words > 0 else 0

            # Category importance multipliers
            category = topic.split('.')[0]
            importance_multipliers = {
                'algorithms': 1.6,
                'data_structures': 1.5,
                'system_design': 1.8,
                'programming_concepts': 1.3,
                'technologies': 1.1
            }

            multiplier = importance_multipliers.get(category, 1.0)

            # Calculate importance score with logarithmic scaling
            importance_score = frequency * multiplier * math.log(raw_count + 1)

            # Time decay factor
            time_factor = decay_calc.calculate_weight(experience_date)

            # Final weighted importance
            weighted_importance = importance_score * time_factor

            # Semantic confidence only for top topics (saves ~95% of encode calls)
            topic_name = topic.split('.')[1]
            if topic in top_topics_for_semantic:
                topic_kws = self.topic_keywords_map.get(topic, [])
                semantic_conf = SemanticConfidenceScorer.score(topic_name, topic_kws, text)
            else:
                semantic_conf = None

            confidence = self._calculate_topic_confidence(raw_count, frequency, semantic_conf)

            scored_topics[topic] = {
                'raw_count': raw_count,
                'frequency_percent': round(frequency, 2),
                'importance_score': round(importance_score, 2),
                'weighted_importance': round(weighted_importance, 2),
                'time_factor': round(time_factor, 3),
                'category': category,
                'topic_name': topic_name,
                'confidence': confidence,
                'semantic_confidence': round(semantic_conf, 3) if semantic_conf is not None else None,
            }

        # Sort by weighted importance
        return dict(sorted(scored_topics.items(),
                           key=lambda x: x[1]['weighted_importance'],
                           reverse=True))
    
    def _calculate_topic_confidence(self, raw_count: int, frequency: float,
                                    semantic_score: float = None) -> float:
        """
        Confidence score for topic detection.
        Uses semantic cosine similarity when available (sentence-transformers),
        otherwise falls back to the count + frequency heuristic.
        """
        if semantic_score is not None:
            return round(semantic_score, 2)

        count_factor = min(raw_count / 5.0, 1.0)
        frequency_factor = min(frequency / 2.0, 1.0)
        return round((count_factor + frequency_factor) / 2, 2)
    
    def _assess_difficulty(self, text: str) -> Dict:
        """Assess the difficulty level of the interview."""
        difficulty_scores = {'easy': 0, 'medium': 0, 'hard': 0}
        
        for difficulty, patterns in self.difficulty_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                difficulty_scores[difficulty] += matches
        
        # Determine overall difficulty
        total_mentions = sum(difficulty_scores.values())
        if total_mentions == 0:
            overall_difficulty = 'unknown'
            confidence = 0.0
        else:
            overall_difficulty = max(difficulty_scores, key=difficulty_scores.get)
            confidence = difficulty_scores[overall_difficulty] / total_mentions
        
        return {
            'overall_difficulty': overall_difficulty,
            'confidence': round(confidence, 2),
            'breakdown': difficulty_scores,
            'difficulty_indicators': self._extract_difficulty_indicators(text)
        }
    
    def _extract_difficulty_indicators(self, text: str) -> List[str]:
        """Extract specific difficulty indicators."""
        indicators = []
        
        # Time-based indicators
        time_patterns = [
            r'(?:took|spent|required)\s+(\d+)\s*(?:hours?|minutes?|days?)',
            r'(?:quick|fast|quickly|immediately)',
            r'(?:long|lengthy|extended|struggled|difficult)'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
        
        return indicators[:5]  # Limit to top 5 indicators
    
    def _classify_interview_rounds(self, text: str) -> Dict:
        """Classify different types of interview rounds."""
        round_types = {
            'coding': ['coding', 'algorithm', 'data structure', 'leetcode', 'hackerrank'],
            'system_design': ['system design', 'architecture', 'scalability', 'design'],
            'behavioral': ['behavioral', 'culture fit', 'leadership', 'teamwork', 'conflict'],
            'technical_discussion': ['technical discussion', 'past projects', 'experience', 'deep dive']
        }
        
        round_classifications = {}
        
        for round_type, keywords in round_types.items():
            score = 0
            for keyword in keywords:
                score += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))
            
            if score > 0:
                round_classifications[round_type] = {
                    'score': score,
                    'confidence': min(score / 3.0, 1.0)  # Normalize confidence
                }
        
        return round_classifications
    
    def _extract_key_insights(self, text: str) -> List[str]:
        """Extract key insights and advice from the experience."""
        insight_patterns = [
            r'(?:tip|advice|suggestion|recommendation|key|important)[:.]?\s*(.{20,100})',
            r'(?:focus on|prepare|study|practice)\s+(.{20,100})',
            r'(?:learnt|learned|realized|understood)\s+(.{20,100})'
        ]
        
        insights = []
        for pattern in insight_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 15:
                    insights.append(match.strip()[:200])  # Limit length
        
        return insights[:5]  # Top 5 insights
    
    def _calculate_overall_confidence(self, topics: Dict) -> float:
        """Calculate overall confidence in the analysis."""
        if not topics:
            return 0.0
        
        confidences = [topic_data['confidence'] for topic_data in topics.values()]
        return round(sum(confidences) / len(confidences), 2)
