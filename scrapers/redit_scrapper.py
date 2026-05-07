import re
import json
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from urllib.parse import urljoin, quote
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config.settings import Config


class RedditScraper(BaseScraper):
    """
    Advanced Reddit scraper for interview experiences.
    Updated to match GeeksforGeeks scraper format with enhanced functionality.
    """

    def __init__(self):
        super().__init__('reddit')
        self.base_url = 'https://www.reddit.com'

        # Use Reddit's JSON API (no auth required for public posts)
        self.api_base = 'https://www.reddit.com/r'

        # Expanded company name mappings including Indian companies
        self.company_mappings = {
            # International Companies
            'Amazon': ['amazon', 'amzn', 'aws', 'amazon.com', 'amazon inc'],
            'Google': ['google', 'alphabet', 'goog', 'google.com', 'alphabet inc'],
            'Apple': ['apple', 'aapl', 'apple inc', 'apple.com'],
            'Netflix': ['netflix', 'nflx', 'netflix.com', 'netflix inc'],
            'Meta': ['meta', 'facebook', 'fb', 'instagram', 'whatsapp', 'meta platforms'],
            'Microsoft': ['microsoft', 'msft', 'ms', 'microsoft.com', 'microsoft corporation'],

            # Indian Companies
            'Flipkart': ['flipkart', 'flipkart.com', 'flipkart india'],
            'Carwale': ['carwale', 'carwale.com', 'car wale'],
            'Swiggy': ['swiggy', 'swiggy.com'],
            'Zomato': ['zomato', 'zomato.com'],
            'Paytm': ['paytm', 'paytm.com', 'one97'],
            'Ola': ['ola', 'ola cabs', 'ola.com'],
            'Uber': ['uber', 'uber.com'],
            'Byju': ['byju', 'byjus', 'byju\'s'],
            'Razorpay': ['razorpay', 'razorpay.com'],
            'Freshworks': ['freshworks', 'freshdesk', 'freshservice'],
            'Zoho': ['zoho', 'zoho.com'],
            'InMobi': ['inmobi', 'inmobi.com'],
            'ShareChat': ['sharechat', 'share chat'],
            'Dream11': ['dream11', 'dream 11'],
            'PhonePe': ['phonepe', 'phone pe'],
            'Myntra': ['myntra', 'myntra.com'],
            'BigBasket': ['bigbasket', 'big basket'],
            'Grofers': ['grofers', 'blinkit'],
            'Dunzo': ['dunzo', 'dunzo.com'],
            'Nykaa': ['nykaa', 'nykaa.com'],
            'PolicyBazaar': ['policybazaar', 'policy bazaar'],
            'MakeMyTrip': ['makemytrip', 'make my trip', 'mmt'],
            'BookMyShow': ['bookmyshow', 'book my show', 'bms'],
            'Lenskart': ['lenskart', 'lenskart.com'],
            'UrbanClap': ['urbanclap', 'urban clap', 'urbancompany', 'urban company'],
            'Cred': ['cred', 'cred.com'],
            'Unacademy': ['unacademy', 'unacademy.com'],
            'Vedantu': ['vedantu', 'vedantu.com'],

            # IT Services & Consulting
            'TCS': ['tcs', 'tata consultancy', 'tata consultancy services'],
            'Infosys': ['infosys', 'infy'],
            'Wipro': ['wipro', 'wipro technologies'],
            'Capgemini': ['capgemini', 'cap gemini'],
            'HCL': ['hcl', 'hcl technologies', 'hcltech'],
            'Accenture': ['accenture'],
            'Cognizant': ['cognizant', 'cognizant technology'],
            'TechMahindra': ['tech mahindra', 'techmahindra'],
            'IBM': ['ibm', 'ibm india'],
            'Deloitte': ['deloitte'],
            'Mphasis': ['mphasis'],
            'LTIMindtree': ['ltimindtree', 'lti mindtree'],
            'Hexaware': ['hexaware'],
            'Persistent': ['persistent systems', 'persistent'],
        }

        # Enhanced headers for Reddit
        self.session.headers.update({
            'User-Agent': 'Interview Intelligence Research Bot 1.0 (Educational Use)',
            'Accept': 'application/json'
        })

    def discover_experience_urls(self, company: str, max_pages: int = 10) -> List[str]:
        """Discover interview experience URLs using multiple strategies."""
        urls = set()  # Use set to avoid duplicates

        # Strategy 1: Multiple subreddit search
        urls.update(self._search_multiple_subreddits(company, max_pages))

        # Strategy 2: Company-specific subreddit search
        urls.update(self._search_company_subreddit(company))

        # Strategy 3: Recent posts from career subreddits
        urls.update(self._get_recent_career_posts(company))

        return list(urls)

    def _search_multiple_subreddits(self, company: str, max_pages: int) -> set:
        """Search multiple relevant subreddits for interview experiences."""
        urls = set()

        subreddits = [
            'cscareerquestions',
            'ExperiencedDevs',
            'interviews',
            'leetcode',
            'ITCareerQuestions',
            'cscareerquestionsEU',
            'DeveloperJobs',
            'programming'
        ]

        search_terms = [
            f'{company} interview experience',
            f'{company} coding interview',
            f'{company} software engineer interview',
            f'{company} onsite interview',
            f'{company} phone screen'
        ]

        for subreddit in subreddits:
            for search_term in search_terms:
                # Use Reddit's search API
                search_url = f"{self.api_base}/{subreddit}/search.json"
                params = {
                    'q': search_term,
                    'restrict_sr': 'on',
                    'sort': 'relevance',
                    'limit': 25,
                    't': 'all'  # All time
                }

                response = self.safe_request(search_url, params=params)
                if not response:
                    continue

                try:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])

                    for post in posts:
                        post_data = post.get('data', {})
                        permalink = post_data.get('permalink')

                        if permalink and self._is_interview_experience_post(post_data, company):
                            full_url = f"https://www.reddit.com{permalink}"
                            urls.add(full_url)

                except Exception as e:
                    self.logger.warning(f"Error parsing Reddit JSON for {subreddit}: {e}")

        return urls

    def _search_company_subreddit(self, company: str) -> set:
        """Search company-specific subreddits."""
        urls = set()

        # Check if company has its own subreddit
        company_subreddits = [
            company.lower(),
            f"{company.lower()}careers",
            f"{company.lower()}employees"
        ]

        for subreddit_name in company_subreddits:
            search_url = f"{self.api_base}/{subreddit_name}/search.json"
            params = {
                'q': 'interview experience',
                'restrict_sr': 'on',
                'sort': 'relevance',
                'limit': 20
            }

            response = self.safe_request(search_url, params=params)
            if not response:
                continue

            try:
                data = response.json()
                posts = data.get('data', {}).get('children', [])

                for post in posts:
                    post_data = post.get('data', {})
                    permalink = post_data.get('permalink')

                    if permalink and self._is_interview_experience_post(post_data, company):
                        full_url = f"https://www.reddit.com{permalink}"
                        urls.add(full_url)

            except Exception as e:
                self.logger.warning(f"Error searching company subreddit {subreddit_name}: {e}")

        return urls

    def _get_recent_career_posts(self, company: str) -> set:
        """Get recent posts from career-focused subreddits with targeted search."""
        urls = set()

        career_subreddits = ['cscareerquestions', 'ExperiencedDevs']

        for subreddit in career_subreddits:
            # Use targeted search instead of browsing all new posts
            search_url = f"{self.api_base}/{subreddit}/search.json"

            # Search with specific company + interview terms
            search_queries = [
                f'"{company}" interview',
                f'{company} interview experience',
                f'{company} coding interview'
            ]

            for query in search_queries:
                params = {
                    'q': query,
                    'restrict_sr': 'on',
                    'sort': 'relevance',
                    'limit': 25,
                    't': 'year'  # Limit to past year for relevancy
                }

                response = self.safe_request(search_url, params=params)
                if not response:
                    continue

                try:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])

                    for post in posts:
                        post_data = post.get('data', {})
                        if self._is_interview_experience_post(post_data, company):
                            permalink = post_data.get('permalink')
                            if permalink:
                                full_url = f"https://www.reddit.com{permalink}"
                                urls.add(full_url)

                except Exception as e:
                    self.logger.warning(f"Error searching {subreddit} for {query}: {e}")

        return urls

    def _is_interview_experience_post(self, post_data: Dict, company: str) -> bool:
        """Enhanced check if Reddit post is an interview experience."""
        title = post_data.get('title', '').lower()
        selftext = post_data.get('selftext', '').lower()

        # Use centralized company extraction for better accuracy
        from utils.company_extractor import extract_company_from_content

        # Extract company from post content
        extracted_company = extract_company_from_content(title, selftext, company)

        # Must match the target company exactly
        company_match = extracted_company == company

        # Stronger interview keyword matching with word boundaries
        import re
        interview_patterns = [
            r'\binterview\s+experience\b',
            r'\binterview\s+(process|round|question)\b',
            r'\b(onsite|phone|technical|coding|behavioral)\s+interview\b',
            r'\b(got|received|rejected)\s+(offer|rejection)\b',
            r'\binterview\s+(failed|passed|cleared)\b',
            r'\bhired\s+at\b',
            r'\boffered\s+position\b'
        ]

        # Check if any interview pattern matches in title or content
        full_text = f"{title} {selftext}"
        interview_match = any(re.search(pattern, full_text) for pattern in interview_patterns)

        # Content must be substantial enough to be a real experience writeup
        min_content_length = len(selftext) >= 300

        # Company must appear in the title, OR be mentioned 3+ times in the body.
        # This stops posts where the company is only a passing mention in a long thread.
        company_variations = self.company_mappings.get(company, [company.lower()])
        company_in_title = any(v in title for v in company_variations)
        body_mentions = sum(selftext.count(v) for v in company_variations)
        company_prominence = company_in_title or body_mentions >= 3

        # Avoid common false positives
        false_positive_keywords = [
            'job posting', 'salary negotiation', 'company culture',
            'benefits', 'work life balance', 'resignation', 'performance review'
        ]
        is_false_positive = any(keyword in full_text for keyword in false_positive_keywords)

        # Must have company match AND interview keywords AND good length AND prominent company AND not false positive
        result = company_match and interview_match and min_content_length and company_prominence and not is_false_positive

        if result:
            self.logger.debug(f"Valid interview post found: {title[:50]}... for {company}")

        return result

    def extract_experience_data(self, url: str, target_company: str = None) -> Optional[Dict]:
        """Extract structured data from Reddit post."""
        # Convert to JSON API URL
        json_url = url.rstrip('/') + '.json'

        response = self.safe_request(json_url)
        if not response:
            return None

        try:
            data = response.json()

            # Reddit JSON structure: [post, comments]
            post_data = data[0]['data']['children'][0]['data']

            # Extract basic information
            title = post_data.get('title', '').strip()
            if not title:
                return None

            content = post_data.get('selftext', '').strip()
            if not content or len(content) < 500:  # Require substantial content
                return None

            # Must contain at least one interview-specific keyword
            interview_keywords = ['interview', 'round', 'hiring', 'offer', 'rejected', 'onsite', 'technical']
            if not any(kw in content.lower() for kw in interview_keywords):
                return None

            # Extract metadata
            experience_date = self._extract_date_from_timestamp(post_data.get('created_utc'))
            company = self._extract_company_from_content(title, content, target_company)
            role = self._extract_role_from_content(title, content)

            # Extract interview rounds information
            rounds_info = self._extract_rounds_info(content)

            return {
                'title': title,
                'content': content,
                'source_url': url,
                'source_platform': 'reddit',
                'company': company,
                'role': role,
                'experience_date': experience_date,
                'rounds_count': rounds_info['count'],
                'rounds_details': rounds_info['details'],
                'difficulty_indicators': self._extract_difficulty_indicators(content),
                'outcome': self._extract_outcome(content),
                'upvotes': post_data.get('ups', 0),
                'comments_count': post_data.get('num_comments', 0),
                'time_weight': self._calculate_time_weight(experience_date),
                'subreddit': post_data.get('subreddit', 'unknown')
            }

        except Exception as e:
            self.logger.error(f"Error extracting data from {url}: {e}")
            return None

    def _extract_date_from_timestamp(self, timestamp: float) -> datetime:
        """Convert Reddit timestamp to datetime."""
        if timestamp:
            return datetime.utcfromtimestamp(timestamp)
        else:
            return datetime.utcnow() - timedelta(days=30)

    def _extract_company_from_content(self, title: str, content: str, target_company: str = None) -> str:
        """Extract company name using centralized extraction service."""
        from utils.company_extractor import extract_company_from_content
        return extract_company_from_content(title, content, target_company)

    def _extract_role_from_content(self, title: str, content: str) -> str:
        """Extract role information."""
        text = (title + " " + content).lower()

        role_patterns = {
            'SDE Intern': ['intern', 'internship', 'summer intern', 'new grad'],
            'Senior SDE': ['senior', 'staff', 'principal', 'l6', 'l7', 'senior sde'],
            'SDE-3': ['sde-3', 'sde 3', 'senior sde', 'staff engineer'],
            'SDE-2': ['sde-2', 'sde 2', 'sde ii', 'mid level', 'l5'],
            'SDE-1': ['sde-1', 'sde 1', 'sde i', 'junior', 'l4'],
            'SDE': ['sde', 'software development engineer', 'software developer', 'software engineer']
        }

        for role, patterns in role_patterns.items():
            if any(pattern in text for pattern in patterns):
                return role

        return "Software Engineer"

    def _extract_rounds_info(self, content: str) -> Dict:
        """Extract information about interview rounds."""
        content_lower = content.lower()

        # Count round mentions
        round_patterns = [
            r'round\s*(\d+)',
            r'(\d+)\s*round',
            r'round\s*[:\-]',
            r'interview\s*(\d+)',
        ]

        rounds_found = set()
        for pattern in round_patterns:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                if match.group(1).isdigit():
                    rounds_found.add(int(match.group(1)))

        # Extract round descriptions
        round_descriptions = []
        round_sections = re.split(r'round\s*\d+|interview\s*\d+', content, flags=re.IGNORECASE)

        for i, section in enumerate(round_sections[1:], 1):  # Skip first split part
            if len(section.strip()) > 50:  # Only meaningful sections
                round_descriptions.append({
                    'round_number': i,
                    'description': section[:500]  # Limit length
                })

        return {
            'count': len(rounds_found) if rounds_found else max(len(round_descriptions), 1),
            'details': round_descriptions
        }

    def _extract_difficulty_indicators(self, content: str) -> List[str]:
        """Extract difficulty indicators from content."""
        content_lower = content.lower()
        difficulty_indicators = []

        difficulty_patterns = {
            'easy': ['easy', 'simple', 'basic', 'straightforward'],
            'medium': ['medium', 'moderate', 'intermediate', 'standard'],
            'hard': ['hard', 'difficult', 'challenging', 'tough', 'complex']
        }

        for difficulty, keywords in difficulty_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                difficulty_indicators.append(difficulty)

        return difficulty_indicators

    def _extract_outcome(self, content: str) -> str:
        """Extract interview outcome."""
        content_lower = content.lower()

        positive_indicators = [
            'got the offer', 'selected', 'hired', 'offer letter',
            'accepted', 'joined', 'success', 'got offer', 'received offer'
        ]

        negative_indicators = [
            'rejected', 'not selected', 'failed', 'did not get',
            'unsuccessful', "didn't make it", 'no offer'
        ]

        if any(indicator in content_lower for indicator in positive_indicators):
            return 'offer'
        elif any(indicator in content_lower for indicator in negative_indicators):
            return 'rejected'
        else:
            return 'unknown'

    def _calculate_time_weight(self, experience_date: datetime) -> float:
        """Calculate time-based weight for the experience."""
        days_old = (datetime.utcnow() - experience_date).days
        months_old = days_old / 30.44

        # Use exponential decay
        import math
        decay_lambda = Config.DECAY_LAMBDA
        weight = math.exp(-decay_lambda * months_old)

        # Ensure minimum weight
        return max(weight, 0.1)