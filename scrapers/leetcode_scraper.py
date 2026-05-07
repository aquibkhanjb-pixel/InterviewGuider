import re
import json
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config.settings import Config


# LeetCode serves a React SPA, so the HTML scraper returns an empty shell.
# We use their public GraphQL API instead.
_GRAPHQL_URL = 'https://leetcode.com/graphql/'

_TOPIC_LIST_QUERY = """
query categoryTopicList(
  $categories: [String!]!,
  $first: Int!,
  $orderBy: TopicSortingOption,
  $skip: Int,
  $query: String,
  $tags: [String!]
) {
  categoryTopicList(
    categories: $categories,
    first: $first,
    orderBy: $orderBy,
    skip: $skip,
    query: $query,
    tags: $tags
  ) {
    edges {
      node {
        id
        title
        commentCount
        viewCount
        post {
          id
          voteCount
          creationDate
          content
          author { username }
        }
        tags { name slug }
      }
    }
  }
}
"""

_TOPIC_DETAIL_QUERY = """
query DiscussTopic($topicId: Int!) {
  topic(id: $topicId) {
    id
    title
    post {
      id
      voteCount
      creationDate
      content
      author { username }
    }
  }
}
"""


class LeetCodeScraper(BaseScraper):
    """
    LeetCode interview-experience discussion scraper.
    Uses LeetCode's public GraphQL API — avoids the React SPA problem.
    """

    def __init__(self):
        super().__init__('leetcode')
        self.base_url = 'https://leetcode.com'

        self.company_mappings = {
            'Amazon':       ['amazon', 'amzn', 'aws'],
            'Google':       ['google', 'alphabet'],
            'Apple':        ['apple'],
            'Netflix':      ['netflix'],
            'Meta':         ['meta', 'facebook', 'fb'],
            'Microsoft':    ['microsoft', 'msft'],
            'Uber':         ['uber'],
            'Flipkart':     ['flipkart'],
            'Swiggy':       ['swiggy'],
            'Zomato':       ['zomato'],
            'PhonePe':      ['phonepe', 'phone pe'],
            'Paytm':        ['paytm'],
            'Razorpay':     ['razorpay'],
            'Cred':         ['cred'],
            'Ola':          ['ola'],
            'Dream11':      ['dream11'],
            'Myntra':       ['myntra'],
            'TCS':          ['tcs', 'tata consultancy'],
            'Infosys':      ['infosys'],
            'Wipro':        ['wipro'],
            'Capgemini':    ['capgemini'],
            'HCL':          ['hcl'],
            'Accenture':    ['accenture'],
            'Cognizant':    ['cognizant'],
            'IBM':          ['ibm'],
            'Deloitte':     ['deloitte'],
        }

        # GraphQL requires a JSON Content-Type and the CSRF token header
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Referer': 'https://leetcode.com/discuss/interview-experience/',
            'Origin': 'https://leetcode.com',
            'x-csrftoken': 'dummy',   # Public queries don't need a real token
        })

        # Collect post IDs during discovery, fetch full content in extract
        self._discovered_posts: Dict[str, Dict] = {}

    # ------------------------------------------------------------------ #
    #  URL discovery  (returns synthetic URLs that encode the topic ID)
    # ------------------------------------------------------------------ #

    def discover_experience_urls(self, company: str, max_pages: int = 10) -> List[str]:
        urls = set()
        variations = self.company_mappings.get(company, [company.lower()])

        for variation in variations:
            for skip in range(0, max_pages * 15, 15):
                posts = self._graphql_topic_list(variation, first=15, skip=skip)
                if not posts:
                    break
                for post in posts:
                    node = post.get('node', {})
                    topic_id = node.get('id')
                    title = node.get('title', '').lower()
                    if not topic_id:
                        continue
                    if not self._is_relevant(title, node.get('post', {}).get('content', ''), company):
                        continue
                    # Synthetic URL encodes both the readable slug and the numeric ID
                    url = f'https://leetcode.com/discuss/interview-experience/{topic_id}'
                    self._discovered_posts[url] = node
                    urls.add(url)

                # Stop paginating if this page had fewer than 15 results
                if len(posts) < 15:
                    break

        return list(urls)

    def _graphql_topic_list(self, query_term: str, first: int = 15, skip: int = 0) -> List[Dict]:
        payload = {
            'operationName': 'categoryTopicList',
            'query': _TOPIC_LIST_QUERY,
            'variables': {
                'categories': ['interview-experience'],
                'first': first,
                'orderBy': 'hot',
                'skip': skip,
                'query': query_term,
                'tags': [],
            },
        }
        try:
            response = self.session.post(_GRAPHQL_URL, json=payload, timeout=15)
            if response.status_code != 200:
                self.logger.debug(f'LeetCode GraphQL {response.status_code} for "{query_term}"')
                return []
            data = response.json()
            return data.get('data', {}).get('categoryTopicList', {}).get('edges', [])
        except Exception as e:
            self.logger.warning(f'LeetCode GraphQL error for "{query_term}": {e}')
            return []

    def _is_relevant(self, title: str, content: str, company: str) -> bool:
        variations = self.company_mappings.get(company, [company.lower()])
        text = (title + ' ' + content[:500]).lower()
        company_match = any(v in text for v in variations)
        interview_kws = ['interview', 'offer', 'onsite', 'rejected', 'hiring', 'round']
        has_interview = any(kw in text for kw in interview_kws)
        return company_match and has_interview

    # ------------------------------------------------------------------ #
    #  Content extraction
    # ------------------------------------------------------------------ #

    def extract_experience_data(self, url: str, target_company: str = None) -> Optional[Dict]:
        # Use cached node from discovery if available
        node = self._discovered_posts.get(url)

        if not node:
            # Fall back to fetching via GraphQL detail query
            topic_id = self._id_from_url(url)
            if not topic_id:
                return None
            node = self._graphql_topic_detail(topic_id)
            if not node:
                return None

        post = node.get('post', {})
        title = node.get('title', '').strip()
        if not title:
            return None

        # LeetCode stores content as HTML — strip tags
        raw_html = post.get('content', '')
        content = self._html_to_text(raw_html)
        if not content or len(content) < 200:
            return None

        creation_ts = post.get('creationDate')
        experience_date = (
            datetime.utcfromtimestamp(creation_ts)
            if creation_ts else datetime.utcnow() - timedelta(days=30)
        )

        company = self._extract_company(title, content, target_company)
        role = self._extract_role(title, content)
        rounds = self._extract_rounds(content)

        return {
            'title':           title,
            'content':         content,
            'source_url':      url,
            'source_platform': 'leetcode',
            'company':         company,
            'role':            role,
            'experience_date': experience_date,
            'rounds_count':    rounds['count'],
            'rounds_details':  rounds['details'],
            'difficulty_indicators': self._extract_difficulty(content),
            'outcome':         self._extract_outcome(content),
            'upvotes':         post.get('voteCount', 0),
            'time_weight':     self._time_weight(experience_date),
        }

    def _graphql_topic_detail(self, topic_id: int) -> Optional[Dict]:
        payload = {
            'operationName': 'DiscussTopic',
            'query': _TOPIC_DETAIL_QUERY,
            'variables': {'topicId': topic_id},
        }
        try:
            response = self.session.post(_GRAPHQL_URL, json=payload, timeout=15)
            if response.status_code != 200:
                return None
            return response.json().get('data', {}).get('topic')
        except Exception as e:
            self.logger.warning(f'LeetCode detail fetch error for {topic_id}: {e}')
            return None

    def _id_from_url(self, url: str) -> Optional[int]:
        m = re.search(r'/(\d+)$', url)
        if m:
            return int(m.group(1))
        return None

    def _html_to_text(self, html: str) -> str:
        if not html:
            return ''
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    def _extract_company(self, title: str, content: str, target_company: str = None) -> str:
        from utils.company_extractor import extract_company_from_content
        return extract_company_from_content(title, content, target_company)

    def _extract_role(self, title: str, content: str) -> str:
        text = (title + ' ' + content).lower()
        patterns = {
            'SDE Intern':  ['intern', 'internship', 'new grad', 'ng '],
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
        cl = content.lower()
        rounds_found = set()
        for pat in [r'round\s*(\d+)', r'(\d+)\s*round']:
            for m in re.finditer(pat, cl):
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
            'medium': ['medium', 'moderate'],
            'hard':   ['hard', 'difficult', 'challenging', 'tough'],
        }.items():
            if any(k in cl for k in kws):
                result.append(level)
        return result

    def _extract_outcome(self, content: str) -> str:
        cl = content.lower()
        if any(k in cl for k in ['got offer', 'received offer', 'accepted', 'hired', 'passed', 'offer letter']):
            return 'offer'
        if any(k in cl for k in ['rejected', 'failed', 'did not get', 'no offer']):
            return 'rejected'
        return 'unknown'

    def _time_weight(self, experience_date: datetime) -> float:
        import math
        months_old = (datetime.utcnow() - experience_date).days / 30.44
        return max(math.exp(-Config.DECAY_LAMBDA * months_old), 0.1)
