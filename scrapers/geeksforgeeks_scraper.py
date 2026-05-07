import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from urllib.parse import urljoin, quote
from  scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config.settings import Config


class GeeksforGeeksScraper(BaseScraper):
    """
    Advanced GeeksforGeeks scraper with intelligent URL discovery.
    """
    
    def __init__(self):
        super().__init__('geeksforgeeks')
        self.base_url = 'https://www.geeksforgeeks.org'
        
        # Company name mappings for URL construction
        self.company_mappings = {
            'Amazon': ['amazon', 'aws'],
            'Google': ['google', 'alphabet'],
            'Apple': ['apple'],
            'Netflix': ['netflix'],
            'Meta': ['meta', 'facebook', 'fb'],
            'Microsoft': ['microsoft', 'msft'],
            'Flipkart': ['flipkart'],
            'Paytm': ['paytm'],
            'Ola': ['ola'],
            'Uber': ['uber'],
            'Swiggy': ['swiggy'],
            'Zomato': ['zomato'],
            'BigBasket': ['bigbasket', 'big-basket'],
            'Carwale': ['carwale'],
            'Razorpay': ['razorpay'],
            'PhonePe': ['phonepe', 'phone-pe'],
            'Myntra': ['myntra'],
            'MakeMyTrip': ['makemytrip', 'make-my-trip'],
            'BookMyShow': ['bookmyshow', 'book-my-show'],
            'Freshworks': ['freshworks', 'freshdesk'],
            'Zoho': ['zoho'],
            'InMobi': ['inmobi'],
            'ShareChat': ['sharechat', 'share-chat'],
            'Dream11': ['dream11', 'dream-11'],
            'Byju': ['byjus', 'byju'],
            'Unacademy': ['unacademy'],
            'Vedantu': ['vedantu'],
            'Nykaa': ['nykaa'],
            'PolicyBazaar': ['policybazaar', 'policy-bazaar'],
            'Lenskart': ['lenskart'],
            'UrbanClap': ['urbanclap', 'urban-clap', 'urbancompany'],
            'Cred': ['cred'],
            'Grofers': ['grofers'],
            'Dunzo': ['dunzo'],

            # IT Services & Consulting
            'TCS': ['tcs', 'tata-consultancy-services'],
            'Infosys': ['infosys'],
            'Wipro': ['wipro'],
            'Capgemini': ['capgemini'],
            'HCL': ['hcl', 'hcltech'],
            'Accenture': ['accenture'],
            'Cognizant': ['cognizant'],
            'TechMahindra': ['tech-mahindra', 'techmahindra'],
            'IBM': ['ibm'],
            'Deloitte': ['deloitte'],
            'Mphasis': ['mphasis'],
            'LTIMindtree': ['ltimindtree', 'lti-mindtree'],
            'Hexaware': ['hexaware'],
            'Persistent': ['persistent-systems', 'persistent'],
        }
    
    def discover_experience_urls(self, company: str, max_pages: int = 10) -> List[str]:
        """Discover interview experience URLs using multiple strategies."""
        urls = set()  # Use set to avoid duplicates

        # Strategy 1: Company articles page (NEW)
        article_urls = self._company_articles_discovery(company)
        urls.update(article_urls)

        # Early termination if we found enough URLs from articles
        if len(article_urls) >= 10:
            self.logger.info(f"Found sufficient URLs ({len(article_urls)}) from company articles, skipping other strategies")
            return list(urls)

        # Strategy 2: Direct search
        direct_urls = self._search_based_discovery(company, max_pages)
        urls.update(direct_urls)

        # Early termination if we have enough URLs
        if len(urls) >= 15:
            self.logger.info(f"Found sufficient URLs ({len(urls)}) from direct search, skipping remaining strategies")
            return list(urls)

        # Strategy 3: Category browsing (only if we don't have many URLs)
        if len(urls) < 8:
            urls.update(self._category_based_discovery(company))

        # Strategy 4: Company tag pages (only if we still need more)
        if len(urls) < 10:
            urls.update(self._tag_based_discovery(company))

        return list(urls)

    def _company_articles_discovery(self, company: str) -> set:
        """Discover URLs using the company-specific articles page pattern."""
        urls = set()

        # Use company name mappings for URL variations
        company_variations = self.company_mappings.get(company, [company.lower()])

        for variation in company_variations:
            company_articles_url = f"{self.base_url}/companies/{variation}/articles/"
            self.logger.info(f"Checking company articles page: {company_articles_url}")

            response = self.safe_request(company_articles_url)
            if not response:
                continue

            if response.status_code == 404:
                self.logger.debug(f"No company articles page found for {variation}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for interview experience links
            links = soup.find_all('a', href=True)
            found_links = 0

            for link in links:
                href = link.get('href')
                if href and self._is_interview_experience_url(href):
                    full_url = urljoin(self.base_url, href)
                    urls.add(full_url)
                    found_links += 1

            if found_links > 0:
                self.logger.info(f"Found {found_links} experience links from company articles page for {variation}")

        return urls

    def _search_based_discovery(self, company: str, max_pages: int) -> set:
        """Use alternative strategies since /search/ is blocked by robots.txt."""
        urls = set()

        # Since search is blocked, use direct URL patterns instead
        self.logger.info(f"Search endpoint blocked by robots.txt, using alternative discovery for {company}")

        # Strategy: Use known URL patterns for popular companies
        company_variations = self.company_mappings.get(company, [company.lower()])

        for variation in company_variations:
            known_patterns = [
                f"{self.base_url}/{variation}-interview-experience",
                f"{self.base_url}/{variation}-software-engineer-interview-experience",
                f"{self.base_url}/{variation}-sde-interview-experience",
                f"{self.base_url}/{variation}-coding-interview-experience"
            ]

            for pattern_url in known_patterns:
                response = self.safe_request(pattern_url)
                if response and response.status_code == 200:
                    if self._is_interview_experience_url(pattern_url):
                        urls.add(pattern_url)
                        self.logger.info(f"Found experience URL: {pattern_url}")
                        # Only log the first successful find per variation to reduce noise
                        break
                elif response and response.status_code == 404:
                    # Don't log 404s as warnings for direct URL attempts - this is expected
                    self.logger.debug(f"URL pattern not found: {pattern_url}")

        return urls
    
    def _category_based_discovery(self, company: str) -> set:
        """Browse interview experience categories."""
        urls = set()
        
        category_urls = [
            f"{self.base_url}/category/interview-experiences/",
            f"{self.base_url}/company-interview-corner/"
        ]
        
        for category_url in category_urls:
            response = self.safe_request(category_url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find company-specific experience links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and self._is_interview_experience_url(href):
                    full_url = urljoin(self.base_url, href)
                    if self._matches_company(full_url, company):
                        urls.add(full_url)
        
        return urls
    
    def _tag_based_discovery(self, company: str) -> set:
        """Use company tag pages to find experiences, handle 404s gracefully."""
        urls = set()

        company_variations = self.company_mappings.get(company, [company.lower()])

        for variation in company_variations:
            tag_url = f"{self.base_url}/tag/{variation}/"

            response = self.safe_request(tag_url)
            if not response:
                continue

            # Handle 404s gracefully
            if response.status_code == 404:
                self.logger.info(f"No tag page found for {variation} (404)")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            links = soup.find_all('a', href=True)
            found_links = 0
            for link in links:
                href = link.get('href')
                if href and self._is_interview_experience_url(href):
                    full_url = urljoin(self.base_url, href)
                    urls.add(full_url)
                    found_links += 1

            if found_links > 0:
                self.logger.info(f"Found {found_links} experience links from tag {variation}")

        return urls
    
    def _is_interview_experience_url(self, url: str) -> bool:
        """Check if URL is likely an interview experience."""
        url_lower = url.lower()
        experience_indicators = [
            'interview-experience',
            'interview-exp',
            'coding-interview',
            'sde-interview',
            'software-engineer-interview'
        ]
        
        return any(indicator in url_lower for indicator in experience_indicators)
    
    def _matches_company(self, url: str, company: str) -> bool:
        """Check if URL content matches the target company."""
        company_variations = self.company_mappings.get(company, [company.lower()])
        url_lower = url.lower()
        
        return any(variation in url_lower for variation in company_variations)
    
    def extract_experience_data(self, url: str, target_company: str = None) -> Optional[Dict]:
        """Extract structured data from GeeksforGeeks experience page."""
        response = self.safe_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            if not title:
                return None
            
            # Extract main content
            content = self._extract_content(soup)
            if not content or len(content.strip()) < 100:  # Skip very short content
                return None
            
            # Extract metadata
            experience_date = self._extract_date(soup, response.text)
            company = self._extract_company_from_content(title, content, target_company)
            role = self._extract_role_from_content(title, content)
            
            # Extract interview rounds information
            rounds_info = self._extract_rounds_info(content)
            
            return {
                'title': title.strip(),
                'content': content.strip(),
                'source_url': url,
                'company': company,
                'role': role,
                'experience_date': experience_date,
                'rounds_count': rounds_info['count'],
                'rounds_details': rounds_info['details'],
                'difficulty_indicators': self._extract_difficulty_indicators(content),
                'outcome': self._extract_outcome(content)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting data from {url}: {e}")
            return None
    
    def _extract_title(self, soup) -> Optional[str]:
        """Extract page title with fallbacks."""
        selectors = [
            'h1.entry-title',
            'h1.article-title', 
            'h1',
            '.page-title',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) > 10:
                    return title
        
        return None
    
    def _extract_content(self, soup) -> str:
        """Extract main article content."""
        # Remove unwanted elements
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()
        
        # Try different content selectors
        content_selectors = [
            '.entry-content',
            '.article-content',
            '.post-content',
            'article',
            '.content',
            'main'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                return content_elem.get_text(separator='\n', strip=True)
        
        # Fallback: get all paragraphs
        paragraphs = soup.find_all('p')
        return '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
    
    def _extract_date(self, soup, page_text: str) -> datetime:
        """Extract publication date with multiple strategies."""
        # Strategy 1: Look for date in structured data
        date_selectors = [
            '.entry-date',
            '.published-date',
            '.post-date',
            'time[datetime]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get('datetime') or date_elem.get_text()
                try:
                    return date_parser.parse(date_text)
                except:
                    continue
        
        # Strategy 2: Look for date patterns in text
        date_patterns = [
            r'Last Updated\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})',
            r'Published\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})',
            r'(\d{1,2}\s+\w+,?\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    return date_parser.parse(match.group(1))
                except:
                    continue
        
        # Fallback: return recent date
        return datetime.utcnow() - timedelta(days=30)
    
    def _extract_company_from_content(self, title: str, content: str, target_company: str = None) -> str:
        """Extract company name using centralized extraction service."""
        from utils.company_extractor import extract_company_from_content
        return extract_company_from_content(title, content, target_company)

    
    def _extract_role_from_content(self, title: str, content: str) -> str:
        """Extract role information."""
        text = (title + " " + content).lower()
        
        role_patterns = {
            'SDE Intern': ['intern', 'internship', 'summer intern'],
            'SDE-3': ['sde-3', 'sde 3', 'senior sde', 'staff engineer'],
            'SDE-2': ['sde-2', 'sde 2', 'sde ii'],
            'SDE-1': ['sde-1', 'sde 1', 'sde i'],
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
            'accepted', 'joined', 'success'
        ]
        
        negative_indicators = [
            'rejected', 'not selected', 'failed', 'did not get',
            'unsuccessful', "didn't make it"
        ]
        
        if any(indicator in content_lower for indicator in positive_indicators):
            return 'offer'
        elif any(indicator in content_lower for indicator in negative_indicators):
            return 'rejected'
        else:
            return 'unknown'