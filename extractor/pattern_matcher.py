"""
Pattern matching module for extracting specific information from text
"""

import re
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse

from config.patterns import PATTERNS

logger = logging.getLogger(__name__)

class PatternMatcher:
    """Extracts structured information from unstructured text"""
    
    def __init__(self):
        self.patterns = PATTERNS
    
    def extract_info(self, text: str, filename: str) -> Dict[str, str]:
        """Extract name, ORCID, and Google Scholar links from text"""
        
        result = {
            'filename': filename,
            'name': '',
            'orcid': '',
            'google_scholar': ''
        }
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract information
        result['name'] = self._extract_name(cleaned_text)
        result['orcid'] = self._extract_orcid(cleaned_text)
        result['google_scholar'] = self._extract_google_scholar(cleaned_text)
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\-@.:/?=&]', ' ', text)
        return text.strip()
    
    def _extract_name(self, text: str) -> str:
        """Extract name using various patterns"""
        
        # Try each name pattern
        for pattern_name, pattern in self.patterns['name'].items():
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Take the first reasonable match
                for match in matches:
                    candidate = match.strip() if isinstance(match, str) else match[0].strip()
                    if self._is_valid_name(candidate):
                        logger.debug(f"Found name using pattern '{pattern_name}': {candidate}")
                        return candidate
        
        return ""
    
    def _extract_orcid(self, text: str) -> str:
        """Extract ORCID using patterns"""
        
        for pattern_name, pattern in self.patterns['orcid'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Extract ORCID ID from match
                for match in matches:
                    orcid_id = self._normalize_orcid(match)
                    if orcid_id:
                        logger.debug(f"Found ORCID using pattern '{pattern_name}': {orcid_id}")
                        return orcid_id
        
        return ""
    
    def _extract_google_scholar(self, text: str) -> str:
        """Extract Google Scholar links"""
        
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    url = self._normalize_url(match)
                    if self._is_valid_google_scholar_url(url):
                        logger.debug(f"Found Google Scholar using pattern '{pattern_name}': {url}")
                        return url
        
        return ""
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate if extracted text is a reasonable name"""
        if not name or len(name) < 2:
            return False
        
        # Check if it contains at least some letters
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        # Avoid common false positives
        false_positives = ['email', 'phone', 'address', 'university', 'department']
        if any(fp in name.lower() for fp in false_positives):
            return False
        
        return True
    
    def _normalize_orcid(self, orcid_text: str) -> str:
        """Normalize ORCID to standard format"""
        # Extract just the ORCID digits and hyphens
        orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_text)
        if orcid_match:
            return f"https://orcid.org/{orcid_match.group(1)}"
        return ""
    
    def _normalize_url(self, url_text: str) -> str:
        """Normalize URL format"""
        url = url_text.strip()
        if not url.startswith(('http://', 'https://')):
            if 'scholar.google' in url:
                url = 'https://' + url
        return url
    
    def _is_valid_google_scholar_url(self, url: str) -> bool:
        """Validate Google Scholar URL"""
        try:
            parsed = urlparse(url)
            return 'scholar.google' in parsed.netloc and 'user=' in url
        except:
            return False
