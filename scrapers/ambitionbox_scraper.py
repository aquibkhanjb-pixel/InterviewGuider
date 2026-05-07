import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config.settings import Config


class AmbitionBoxScraper(BaseScraper):
    """
    AmbitionBox interview experience scraper.
    Best source for Indian IT services companies (TCS, Infosys, Wipro, Capgemini, etc.)
    Targets https://www.ambitionbox.com/interviews/{slug}-interview-questions
    """

    def __init__(self):
        super().__init__('ambitionbox')
        self.base_url = 'https://www.ambitionbox.com'

        # Maps our company names to AmbitionBox URL slugs
        self.company_slugs = {
            'TCS':          'tcs',
            'Infosys':      'infosys',
            'Wipro':        'wipro',
            'Capgemini':    'capgemini',
            'HCL':          'hcl-technologies',
            'Accenture':    'accenture',
            'Cognizant':    'cognizant-technology-solutions',
            'TechMahindra': 'tech-mahindra',
            'IBM':          'ibm',
            'Deloitte':     'deloitte',
            'Mphasis':      'mphasis',
            'LTIMindtree':  'ltimindtree',
            'Hexaware':     'hexaware-technologies',
            'Persistent':   'persistent-systems',
            'Amazon':       'amazon',
            'Google':       'google',
            'Microsoft':    'microsoft',
            'Apple':        'apple',
            'Meta':         'meta',
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
            'MakeMyTrip':   'makemytrip',
            'Freshworks':   'freshworks',
            'Zoho':         'zoho',
            'Nykaa':        'nykaa',
        }

        # AmbitionBox blocks generic bot UAs — use a real browser UA
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.ambitionbox.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    # ------------------------------------------------------------------ #
    #  URL discovery
    # ------------------------------------------------------------------ #

    def discover_experience_urls(self, company: str, max_pages: int = 10) -> List[str]:
        """
        AmbitionBox URL pattern: /interviews/{slug}-interview-questions (paginated)
        Role-specific sub-pages: /interviews/{slug}-interview-questions/{role}
        Both contain real Q&A data from interview candidates.
        """
        urls = set()
        slug = self.company_slugs.get(company, company.lower().replace(' ', '-'))
        base_listing = f'{self.base_url}/interviews/{slug}-interview-questions'

        # Always include the main listing page as a document
        main_response = self.safe_request(base_listing)
        if main_response and main_response.status_code == 200:
            urls.add(base_listing)
            soup0 = BeautifulSoup(main_response.content, 'html.parser')
            # Collect role sub-pages linked from the main listing
            role_links = self._extract_links(soup0, slug)
            urls.update(role_links)
            self.logger.info(f'AmbitionBox main page for {slug}: {len(role_links)} role sub-pages')

            # Paginate through role sub-pages too
            for page in range(2, max_pages + 1):
                page_url = f'{base_listing}?page={page}'
                response = self.safe_request(page_url)
                if not response or response.status_code in (404, 500):
                    break
                soup = BeautifulSoup(response.content, 'html.parser')
                found = self._extract_links(soup, slug)
                if not found:
                    break
                urls.update(found)
        else:
            self.logger.info(f'AmbitionBox: no page found for {slug}')

        return list(urls)[:max_pages * 5]

    def _extract_links(self, soup: BeautifulSoup, slug: str) -> set:
        """Collect role sub-pages from listing (e.g. /interviews/tcs-.../software-engineer)."""
        urls = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Role sub-pages: /interviews/{slug}-interview-questions/{role}
            if (href.startswith(f'/interviews/{slug}-interview-questions/') and
                    not href.endswith('-interview-questions')):
                urls.add(urljoin(self.base_url, href))
        return urls

    # ------------------------------------------------------------------ #
    #  Content extraction
    # ------------------------------------------------------------------ #

    def extract_experience_data(self, url: str, target_company: str = None) -> Optional[Dict]:
        # For AmbitionBox, the URL itself IS the "experience" document (a role-specific Q&A page).
        # We treat the full page text as content so our NLP can extract topics.
        response = self.safe_request(url)
        if not response:
            return None

        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            title = self._extract_title(soup)
            if not title:
                return None

            content = self._extract_content(soup)
            # AmbitionBox pages are rich — require at least 300 chars
            if not content or len(content.strip()) < 300:
                return None

            experience_date = self._extract_date(soup)
            company = self._extract_company(title, content, target_company)
            role = self._extract_role(title, content)
            rounds = self._extract_rounds(content)

            return {
                'title':           title.strip(),
                'content':         content.strip(),
                'source_url':      url,
                'source_platform': 'ambitionbox',
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
        # AmbitionBox uses structured headings
        for sel in [
            'h1.interview-heading',
            '.interview-question-title',
            'h1',
            '.review-title',
            'title',
        ]:
            el = soup.select_one(sel)
            if el:
                t = el.get_text().strip()
                # Strip site name suffix common on AmbitionBox
                t = re.sub(r'\s*[-|]\s*AmbitionBox.*$', '', t).strip()
                if len(t) > 10:
                    return t
        return None

    def _extract_content(self, soup) -> str:
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()

        # AmbitionBox specific content containers
        for sel in [
            '.interview-content',
            '.interviewQuestion',
            '.review-description',
            '.interview-experience',
            'article',
            '.content-body',
            'main',
        ]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(separator='\n', strip=True)

        paras = soup.find_all('p')
        return '\n'.join(p.get_text().strip() for p in paras if p.get_text().strip())

    def _extract_date(self, soup) -> datetime:
        for sel in ['time[datetime]', '.review-date', '.posted-date', '.date']:
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

        return datetime.utcnow() - timedelta(days=45)

    def _extract_company(self, title: str, content: str, target_company: str = None) -> str:
        from utils.company_extractor import extract_company_from_content
        return extract_company_from_content(title, content, target_company)

    def _extract_role(self, title: str, content: str) -> str:
        text = (title + ' ' + content).lower()
        patterns = {
            'SDE Intern':  ['intern', 'internship', 'trainee', 'fresher', 'new grad'],
            'Senior SDE':  ['senior', 'staff', 'principal', 'lead'],
            'SDE-2':       ['sde-2', 'sde 2', 'mid level', 'associate'],
            'SDE-1':       ['sde-1', 'sde 1', 'junior'],
            'SDE':         ['sde', 'software engineer', 'developer', 'programmer'],
        }
        for role, kws in patterns.items():
            if any(kw in text for kw in kws):
                return role
        return 'Software Engineer'

    def _extract_rounds(self, content: str) -> Dict:
        content_lower = content.lower()
        rounds_found = set()
        for pat in [r'round\s*(\d+)', r'(\d+)\s*round', r'round\s*[:\-]']:
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
            'easy':   ['easy', 'simple', 'basic', 'straightforward'],
            'medium': ['medium', 'moderate', 'average'],
            'hard':   ['hard', 'difficult', 'challenging', 'tough'],
        }.items():
            if any(k in cl for k in kws):
                result.append(level)
        return result

    def _extract_outcome(self, content: str) -> str:
        cl = content.lower()
        if any(k in cl for k in ['selected', 'hired', 'offer', 'joined', 'got the job']):
            return 'offer'
        if any(k in cl for k in ['rejected', 'not selected', 'failed', 'no offer']):
            return 'rejected'
        return 'unknown'

    def _time_weight(self, experience_date: datetime) -> float:
        import math
        months_old = (datetime.utcnow() - experience_date).days / 30.44
        return max(math.exp(-Config.DECAY_LAMBDA * months_old), 0.1)
