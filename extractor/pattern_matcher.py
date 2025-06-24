"""
Pattern matching module for extracting specific information from text
"""

import re
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from itertools import product

from config.patterns import PATTERNS

logger = logging.getLogger(__name__)

class PatternMatcher:
    """Extracts structured information from unstructured text"""
    
    def __init__(self):
        self.patterns = PATTERNS
    
    def extract_info(self, text: str, filename: str) -> List[Dict[str, str]]:
        """
        Extract ORCID and Google Scholar links from text.
        Returns multiple entries if multiple URLs are found.
        
        Args:
            text: Text content from PDF
            filename: Original filename
            
        Returns:
            List of dictionaries, each containing filename, orcid, and google_scholar
        """
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract all instances
        orcids = self._extract_all_orcids(cleaned_text)
        google_scholars = self._extract_all_google_scholars(cleaned_text)
        
        # Create entries for all combinations
        entries = self._create_entries(filename, orcids, google_scholars)
        
        logger.debug(f"Found {len(orcids)} ORCIDs and {len(google_scholars)} Google Scholar URLs in {filename}")
        
        return entries
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\-@.:/?=&]', ' ', text)
        return text.strip()
    
    def _extract_all_orcids(self, text: str) -> List[str]:
        """Extract all ORCID URLs from text"""
        
        orcids = set()  # Use set to avoid duplicates
        
        # Try each ORCID pattern
        for pattern_name, pattern in self.patterns['orcid'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    orcid_id = self._normalize_orcid(match)
                    if orcid_id and self._is_valid_orcid(orcid_id):
                        orcids.add(orcid_id)
                        logger.debug(f"Found ORCID using pattern '{pattern_name}': {orcid_id}")
        
        return list(orcids)
    
    def _extract_all_google_scholars(self, text: str) -> List[str]:
        """Extract all Google Scholar URLs from text"""
        
        scholars = set()  # Use set to avoid duplicates
        
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    url = self._normalize_url(match)
                    if self._is_valid_google_scholar_url(url):
                        scholars.add(url)
                        logger.debug(f"Found Google Scholar using pattern '{pattern_name}': {url}")
        
        return list(scholars)
    
    def _create_entries(self, filename: str, orcids: List[str], google_scholars: List[str]) -> List[Dict[str, str]]:
        """
        Create CSV entries for all combinations of ORCIDs and Google Scholar URLs
        
        Args:
            filename: Original PDF filename
            orcids: List of ORCID URLs found
            google_scholars: List of Google Scholar URLs found
            
        Returns:
            List of entry dictionaries
        """
        
        entries = []
        
        if orcids and google_scholars:
            # Create entry for each combination
            for orcid, scholar in product(orcids, google_scholars):
                entries.append({
                    'filename': filename,
                    'orcid': orcid,
                    'google_scholar': scholar
                })
        elif orcids:
            # Only ORCIDs found, create entries with empty Google Scholar
            for orcid in orcids:
                entries.append({
                    'filename': filename,
                    'orcid': orcid,
                    'google_scholar': ''
                })
        elif google_scholars:
            # Only Google Scholar found, create entries with empty ORCID
            for scholar in google_scholars:
                entries.append({
                    'filename': filename,
                    'orcid': '',
                    'google_scholar': scholar
                })
        else:
            # Nothing found, create single empty entry
            entries.append({
                'filename': filename,
                'orcid': '',
                'google_scholar': ''
            })
        
        return entries
    
    def _normalize_orcid(self, orcid_text: str) -> str:
        """Normalize ORCID to standard format"""
        # Extract just the ORCID digits and hyphens
        orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_text)
        if orcid_match:
            return f"https://orcid.org/{orcid_match.group(1)}"
        return ""
    
    def _is_valid_orcid(self, orcid: str) -> bool:
        """Validate ORCID format and checksum"""
        if not orcid:
            return False
        
        # Extract ORCID ID
        orcid_id = orcid.replace('https://orcid.org/', '')
        
        # Check format
        if not re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]
