import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config.settings import Config


class InterviewBitScraper(BaseScraper):
    """
    InterviewBit interview experience scraper.
    Targets https://www.interviewbit.com/interview-experience/
    which has structured, high-quality interview writeups.
    """

    def __init__(self):
        super().__init__('interviewbit')
        self.base_url = 'https://www.interviewbit.com'
        self.exp_base = f'{self.base_url}/interview-experience'

        # Maps our company names to InterviewBit URL slugs
        self.company_slugs = {
            'Amazon':       'amazon',
            'Google':       'google',
            'Microsoft':    'microsoft',
            'Apple':        'apple',
            'Meta':         'facebook',
            'Netflix':      'netflix',
            'Uber':         'uber',
            'Flipkart':     'flipkart',
            'Swiggy':       'swiggy',
            'Zomato':       'zomato',
            'PhonePe':      'phonepe',
            'Paytm':        'paytm',
            'Razorpay':     'razorpay',
            'Cred':         'cred',
            'Ola':          'ola',
            'Dream11':      'dream11',
            'Myntra':       'myntra',
            'Carwale':      'carwale',
            'BigBasket':    'bigbasket',
            'MakeMyTrip':   'makemytrip',
            'BookMyShow':   'bookmyshow',
            'Freshworks':   'freshworks',
            'Zoho':         'zoho',
            'InMobi':       'inmobi',
            'ShareChat':    'sharechat',
            'Nykaa':        'nykaa',
            'PolicyBazaar': 'policybazaar',
            'Lenskart':     'lenskart',
            'Unacademy':    'unacademy',
            'Byju':         'byjus',
            'TCS':          'tcs',
            'Infosys':      'infosys',
            'Wipro':        'wipro',
            'Capgemini':    'capgemini',
            'HCL':          'hcl',
            'Accenture':    'accenture',
            'Cognizant':    'cognizant',
            'TechMahindra': 'tech-mahindra',
            'IBM':          'ibm',
            'Deloitte':     'deloitte',
            'Mphasis':      'mphasis',
            'Persistent':   'persistent-systems',
        }

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.interviewbit.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    # ------------------------------------------------------------------ #
    #  URL discovery
    # ------------------------------------------------------------------ #

    def discover_experience_urls(self, company: str, max_pages: int = 10) -> List[str]:
        """
        InterviewBit's live URL pattern is /{slug}-interview-questions/
        The page contains structured technical Q&A asked in real interviews,
        which feeds our NLP topic extractor just as well as narrative experiences.
        """
        urls = set()
        slug = self.company_slugs.get(company, company.lower().replace(' ', '-'))

        # Construct the primary URL without fetching (safe_request marks URLs as seen,
        # which would block the subsequent extract_experience_data call for the same URL).
        # Instead, do a lightweight HEAD-style check via plain session.get with no side effects.
        primary_url = f'{self.base_url}/{slug}-interview-questions/'
        try:
            response = self.session.get(primary_url, timeout=Config.TIMEOUT, allow_redirects=True)
            if response.status_code == 200:
                urls.add(primary_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if not href.startswith('/'):
                        continue
                    if (f'/{slug}-' in href and 'interview' in href and
                            href.endswith('/') and href != f'/{slug}-interview-questions/'):
                        urls.add(urljoin(self.base_url, href))
                self.logger.info(f'InterviewBit found {len(urls)} pages for {slug}')
            else:
                self.logger.info(f'InterviewBit: {response.status_code} for {slug}')
        except Exception as e:
            self.logger.warning(f'InterviewBit discovery error for {slug}: {e}')

        return list(urls)[:max_pages]

    # ------------------------------------------------------------------ #
    #  Content extraction
    # ------------------------------------------------------------------ #

    def extract_experience_data(self, url: str, target_company: str = None) -> Optional[Dict]:
        response = self.safe_request(url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            title = self._extract_title(soup)
            if not title:
                return None

            content = self._extract_content(soup)
            if not content or len(content.strip()) < 200:
                return None

            experience_date = self._extract_date(soup)
            company = self._extract_company(title, content, target_company)
            role = self._extract_role(title, content)
            rounds = self._extract_rounds(content)

            return {
                'title':           title.strip(),
                'content':         content.strip(),
                'source_url':      url,
                'source_platform': 'interviewbit',
                'company':         company,
                'role':            role,
                'experience_date': experience_date,
                'rounds_count':    rounds['count'],
                'rounds_details':  rounds['details'],
                'difficulty_indicators': self._extract_difficulty(content),
                'outcome':         self._extract_outcome(content),
                'time_weight':     self._time_weight(experience_date),
            }

        except Exception as e:
            self.logger.error(f'Error extracting {url}: {e}')
            return None

    def _extract_title(self, soup) -> Optional[str]:
        for sel in ['h1.interview-heading', 'h1', '.interview-title', 'title']:
            el = soup.select_one(sel)
            if el:
                t = el.get_text().strip()
                if len(t) > 10:
                    return t
        return None

    def _extract_content(self, soup) -> str:
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()

        for sel in ['.interview-content', '.content-area', 'article', '.post-content',
                    '.questions-list', '.ibQuestions', 'main', '.container']:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator='\n', strip=True)
                if len(text) > 200:
                    return text

        # InterviewBit's Q&A is spread across the full page — use all body text
        body = soup.find('body')
        if body:
            return body.get_text(separator='\n', strip=True)

        paras = soup.find_all('p')
        return '\n'.join(p.get_text().strip() for p in paras if p.get_text().strip())

    def _extract_date(self, soup) -> datetime:
        for sel in ['time[datetime]', '.post-date', '.date', '.published']:
            el = soup.select_one(sel)
            if el:
                raw = el.get('datetime') or el.get_text()
                try:
                    return date_parser.parse(raw)
                except Exception:
                    pass

        for pattern in [
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})',
        ]:
            m = re.search(pattern, soup.get_text())
            if m:
                try:
                    return date_parser.parse(m.group(1))
                except Exception:
                    pass

        return datetime.utcnow() - timedelta(days=30)

    def _extract_company(self, title: str, content: str, target_company: str = None) -> str:
        from utils.company_extractor import extract_company_from_content
        return extract_company_from_content(title, content, target_company)

    def _extract_role(self, title: str, content: str) -> str:
        text = (title + ' ' + content).lower()
        patterns = {
            'SDE Intern':  ['intern', 'internship', 'new grad'],
            'Senior SDE':  ['senior', 'staff', 'principal', 'l6', 'l7'],
            'SDE-2':       ['sde-2', 'sde 2', 'l5'],
            'SDE-1':       ['sde-1', 'sde 1', 'l4'],
            'SDE':         ['sde', 'software engineer', 'developer'],
        }
        for role, kws in patterns.items():
            if any(kw in text for kw in kws):
                return role
        return 'Software Engineer'

    def _extract_rounds(self, content: str) -> Dict:
        content_lower = content.lower()
        rounds_found = set()
        for pat in [r'round\s*(\d+)', r'(\d+)\s*round']:
            for m in re.finditer(pat, content_lower):
                if m.group(1).isdigit():
                    rounds_found.add(int(m.group(1)))

        sections = re.split(r'round\s*\d+', content, flags=re.IGNORECASE)
        details = []
        for i, sec in enumerate(sections[1:], 1):
            if len(sec.strip()) > 50:
                details.append({'round_number': i, 'description': sec[:500]})

        return {
            'count':   len(rounds_found) if rounds_found else max(len(details), 1),
            'details': details,
        }

    def _extract_difficulty(self, content: str) -> List[str]:
        cl = content.lower()
        result = []
        for level, kws in {
            'easy':   ['easy', 'simple', 'straightforward'],
            'medium': ['medium', 'moderate', 'intermediate'],
            'hard':   ['hard', 'difficult', 'challenging', 'tough'],
        }.items():
            if any(k in cl for k in kws):
                result.append(level)
        return result

    def _extract_outcome(self, content: str) -> str:
        cl = content.lower()
        if any(k in cl for k in ['got offer', 'received offer', 'selected', 'hired', 'joined', 'offer letter']):
            return 'offer'
        if any(k in cl for k in ['rejected', 'not selected', 'failed', 'no offer']):
            return 'rejected'
        return 'unknown'

    def _time_weight(self, experience_date: datetime) -> float:
        import math
        months_old = (datetime.utcnow() - experience_date).days / 30.44
        return max(math.exp(-Config.DECAY_LAMBDA * months_old), 0.1)
