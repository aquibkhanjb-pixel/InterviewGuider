#!/usr/bin/env python3
"""
Centralized Company Extraction Service

This module provides a single, consistent way to extract company names
from interview experience content across all scrapers.

Key Features:
- Single source of truth for company patterns
- Priority-based matching to avoid conflicts
- Easy to extend for new companies
- Consistent across all platforms
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class CompanyExtractor:
    """Centralized company name extraction service."""

    def __init__(self):
        # PRIORITY-ORDERED company patterns
        # Companies higher in the list get priority in case of conflicts
        self.company_patterns = {
            # High Priority - Specific companies that might conflict with others
            'PhonePe': ['phonepe', 'phone pe'],
            'Myntra': ['myntra', 'myntra.com'],
            'PayPal': ['paypal', 'paypal.com'],
            'PayTM': ['paytm', 'paytm.com', 'one97'],

            # Tech Giants
            'Google': ['google', 'alphabet', 'goog', 'google.com', 'alphabet inc'],
            'Amazon': ['amazon', 'amzn', 'aws', 'amazon.com', 'amazon inc'],
            'Microsoft': ['microsoft', 'msft', 'ms', 'microsoft.com', 'microsoft corporation'],
            'Apple': ['apple', 'aapl', 'apple inc', 'apple.com'],
            'Meta': ['meta', 'facebook', 'fb', 'instagram', 'whatsapp', 'meta platforms'],
            'Netflix': ['netflix', 'nflx', 'netflix.com', 'netflix inc'],

            # Indian Tech Companies (in order of specificity)
            'Flipkart': ['flipkart', 'flipkart.com', 'flipkart india'],  # Removed phonepe/myntra
            'Zomato': ['zomato', 'zomato.com'],
            'Swiggy': ['swiggy', 'swiggy.com'],
            'Ola': ['ola', 'ola cabs', 'ola.com'],
            'Uber': ['uber', 'uber.com'],
            'Razorpay': ['razorpay', 'razorpay.com'],
            'Dream11': ['dream11', 'dream 11'],
            'Carwale': ['carwale', 'carwale.com', 'car wale'],
            'BigBasket': ['bigbasket', 'big basket'],
            'Grofers': ['grofers', 'blinkit'],
            'Dunzo': ['dunzo', 'dunzo.com'],

            # Other Companies
            'Freshworks': ['freshworks', 'freshdesk', 'freshservice'],
            'Zoho': ['zoho', 'zoho.com'],
            'InMobi': ['inmobi', 'inmobi.com'],
            'ShareChat': ['sharechat', 'share chat'],
            'Nykaa': ['nykaa', 'nykaa.com'],
            'PolicyBazaar': ['policybazaar', 'policy bazaar'],
            'MakeMyTrip': ['makemytrip', 'make my trip', 'mmt'],
            'BookMyShow': ['bookmyshow', 'book my show', 'bms'],
            'Lenskart': ['lenskart', 'lenskart.com'],
            'UrbanCompany': ['urbancompany', 'urban company', 'urbanclap', 'urban clap'],
            'Cred': ['cred', 'cred.com'],
            'Unacademy': ['unacademy', 'unacademy.com'],
            'Vedantu': ['vedantu', 'vedantu.com'],
            'Byju': ['byju', 'byjus', 'byju\'s'],

            # IT Services & Consulting
            'TCS': ['tcs', 'tata consultancy services', 'tata-consultancy', 'tatacons'],
            'Infosys': ['infosys', 'infy', 'infosys.com'],
            'Wipro': ['wipro', 'wipro technologies', 'wipro.com'],
            'Capgemini': ['capgemini', 'cap gemini', 'capgemini.com'],
            'HCL': ['hcl', 'hcl technologies', 'hcltech', 'hcl tech'],
            'Accenture': ['accenture', 'accenture.com'],
            'Cognizant': ['cognizant', 'ctsh', 'cognizant technology'],
            'TechMahindra': ['tech mahindra', 'techmahindra', 'techm', 'tech-mahindra'],
            'IBM': ['ibm', 'ibm india', 'international business machines'],
            'Deloitte': ['deloitte', 'deloitte consulting'],
            'Mphasis': ['mphasis'],
            'LTIMindtree': ['ltimindtree', 'lti mindtree', 'l&t infotech', 'lt infotech'],
            'Hexaware': ['hexaware', 'hexaware technologies'],
            'Persistent': ['persistent', 'persistent systems'],
        }

    def extract_company_from_content(self, title: str, content: str, target_company: Optional[str] = None) -> str:
        """
        Extract company name from title and content with priority-based matching.

        Args:
            title: Article/post title
            content: Article/post content
            target_company: Company we're specifically looking for (optional)

        Returns:
            Company name or "Unknown"
        """
        # If we have a target company, check it first
        if target_company:
            extracted = self._check_target_company_first(title, content, target_company)
            if extracted != "Unknown":
                return extracted

        # Combine title and content for analysis
        text = (title + " " + content).lower()

        # Use priority-based matching (first match wins)
        for company_name, patterns in self.company_patterns.items():
            if self._matches_company_patterns(text, patterns):
                logger.debug(f"Company matched: {company_name}")
                return company_name

        # If no match found, try URL-based extraction
        url_company = self._extract_from_url_patterns(title, content)
        if url_company != "Unknown":
            return url_company

        return "Unknown"

    def _check_target_company_first(self, title: str, content: str, target_company: str) -> str:
        """Check if content matches the target company we're scraping for."""
        text = (title + " " + content).lower()
        target_lower = target_company.lower()

        # Direct match
        if target_lower in text:
            return target_company

        # Check if target company has patterns defined
        patterns = self.company_patterns.get(target_company, [target_lower])
        if self._matches_company_patterns(text, patterns):
            return target_company

        return "Unknown"

    def _matches_company_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the company patterns."""
        for pattern in patterns:
            # Use word boundaries to avoid partial matches
            regex_pattern = r'\b' + re.escape(pattern) + r'\b'
            if re.search(regex_pattern, text):
                return True
        return False

    def _extract_from_url_patterns(self, title: str, content: str) -> str:
        """Try to extract company from URL patterns or context clues."""
        text = (title + " " + content).lower()

        # URL-based extraction patterns
        url_patterns = {
            'GeeksforGeeks': ['geeksforgeeks.org'],
            'LeetCode': ['leetcode.com'],
            'Glassdoor': ['glassdoor.com'],
            'Reddit': ['reddit.com'],
        }

        for company, url_parts in url_patterns.items():
            if any(url_part in text for url_part in url_parts):
                # This indicates the platform, not the target company
                continue

        return "Unknown"

    def add_company_patterns(self, company_name: str, patterns: List[str]) -> None:
        """Add new company patterns dynamically."""
        self.company_patterns[company_name] = patterns
        logger.info(f"Added patterns for {company_name}: {patterns}")

    def get_all_companies(self) -> List[str]:
        """Get list of all supported companies."""
        return list(self.company_patterns.keys())

    def get_patterns_for_company(self, company_name: str) -> List[str]:
        """Get patterns for a specific company."""
        return self.company_patterns.get(company_name, [])

# Global instance
company_extractor = CompanyExtractor()

def extract_company_from_content(title: str, content: str, target_company: Optional[str] = None) -> str:
    """Convenience function to extract company name."""
    return company_extractor.extract_company_from_content(title, content, target_company)

def add_company_patterns(company_name: str, patterns: List[str]) -> None:
    """Convenience function to add new company patterns."""
    company_extractor.add_company_patterns(company_name, patterns)

# Usage examples:
if __name__ == "__main__":
    # Test the extractor
    test_cases = [
        ("PhonePe Interview Experience", "I interviewed at PhonePe for SDE role...", "PhonePe"),
        ("Myntra Software Engineer Interview", "Myntra technical rounds were tough...", "Myntra"),
        ("Microsoft Coding Round", "Microsoft asked me to solve algorithms...", "Microsoft"),
        ("Google Phone Interview", "Google recruiter called me...", "Google"),
    ]

    for title, content, expected in test_cases:
        result = extract_company_from_content(title, content)
        print(f"Title: {title[:30]}...")
        print(f"Expected: {expected}, Got: {result}")
        print(f"✅ {'PASS' if result == expected else 'FAIL'}")
        print("-" * 50)