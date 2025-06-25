"""
Enhanced pattern matching for extracting structured information from PDFs.
"""

import re
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs
from itertools import product

from config.patterns import PATTERNS, CONFIG

logger = logging.getLogger(__name__)

class PatternMatcher:
    """Enhanced pattern matcher with hyperlink integration and validation."""
    
    def __init__(self):
        self.patterns = PATTERNS
        self.config = CONFIG
    
    def extract_info(self, text: str, filename: str, hyperlinks: List[str] = None) -> List[Dict[str, str]]:
        """
        Extract information from both text and hyperlinks.
        
        Args:
            text: Text content from PDF
            filename: Original filename
            hyperlinks: List of hyperlinks extracted from PDF
            
        Returns:
            List of entries with filename, orcid, and google_scholar
        """
        if hyperlinks is None:
            hyperlinks = []
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Extract from text
        text_orcids = self._extract_orcids_from_text(cleaned_text)
        text_scholars = self._extract_scholars_from_text(cleaned_text)
        
        # Extract from hyperlinks
        link_orcids = self._extract_orcids_from_links(hyperlinks)
        link_scholars = self._extract_scholars_from_links(hyperlinks)
        
        # Combine and deduplicate
        all_orcids = self._deduplicate_urls(text_orcids + link_orcids)
        all_scholars = self._deduplicate_urls(text_scholars + link_scholars)
        
        # Create entries
        entries = self._create_entries(filename, all_orcids, all_scholars)
        
        logger.debug(f"📊 {filename}: {len(all_orcids)} ORCIDs, {len(all_scholars)} Scholar URLs")
        
        return entries
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better pattern matching."""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove problematic characters but keep URL-relevant ones
        text = re.sub(r'[^\w\s\-@.:/?=&_]', ' ', text)
        
        # Fix common PDF extraction issues
        text = re.sub(r'(\w)([A-Z])', r'\1 \2', text)  # Add space before capitals
        text = re.sub(r'([a-z])(\d)', r'\1 \2', text)  # Add space before numbers
        
        return text.strip()
    
    def _extract_orcids_from_text(self, text: str) -> List[str]:
        """Extract ORCID URLs from text using multiple patterns."""
        orcids = set()
        
        for pattern_name, pattern in self.patterns['orcid'].items():
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Handle different match formats
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                    
                    orcid = self._normalize_orcid(match)
                    if orcid and self._is_valid_orcid(orcid):
                        orcids.add(orcid)
                        logger.debug(f"Found ORCID via {pattern_name}: {orcid}")
                        
            except Exception as e:
                logger.debug(f"Error with ORCID pattern {pattern_name}: {str(e)}")
        
        return list(orcids)
    
    def _extract_scholars_from_text(self, text: str) -> List[str]:
        """Extract Google Scholar URLs from text."""
        scholars = set()
        
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            try:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Handle different match formats
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                    
                    scholar_url = self._normalize_scholar_url(match)
                    if scholar_url and self._is_valid_scholar_url(scholar_url):
                        scholars.add(scholar_url)
                        logger.debug(f"Found Scholar via {pattern_name}: {scholar_url}")
                        
            except Exception as e:
                logger.debug(f"Error with Scholar pattern {pattern_name}: {str(e)}")
        
        return list(scholars)
    
    def _extract_orcids_from_links(self, hyperlinks: List[str]) -> List[str]:
        """Extract ORCID URLs from hyperlink list."""
        orcids = set()
        
        for link in hyperlinks:
            if not link or not isinstance(link, str):
                continue
            
            if 'orcid.org' in link.lower():
                orcid = self._normalize_orcid(link)
                if orcid and self._is_valid_orcid(orcid):
                    orcids.add(orcid)
                    logger.debug(f"Found ORCID in hyperlink: {orcid}")
        
        return list(orcids)
    
    def _extract_scholars_from_links(self, hyperlinks: List[str]) -> List[str]:
        """Extract Google Scholar URLs from hyperlink list."""
        scholars = set()
        
        for link in hyperlinks:
            if not link or not isinstance(link, str):
                continue
            
            if 'scholar.google' in link.lower():
                scholar_url = self._normalize_scholar_url(link)
                if scholar_url and self._is_valid_scholar_url(scholar_url):
                    scholars.add(scholar_url)
                    logger.debug(f"Found Scholar in hyperlink: {scholar_url}")
        
        return list(scholars)
    
    def _normalize_orcid(self, orcid_text: str) -> str:
        """Normalize ORCID to standard format."""
        if not orcid_text:
            return ""
        
        # Extract ORCID ID pattern
        orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_text.upper())
        if orcid_match:
            orcid_id = orcid_match.group(1)
            return f"https://orcid.org/{orcid_id}"
        
        return ""
    
    def _normalize_scholar_url(self, url_text: str) -> str:
        """normalize Google Scholar URL."""
        if not url_text:
            return ""
        
        url = url_text.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            if url.startswith('scholar.google'):
                url = 'https://' + url
            else:
                return ""
        
        # Basic validation and cleanup
        if 'scholar.google' in url and 'citations' in url:
            # Remove fragments and clean up
            url = url.split('#')[0]
            return url
        
        return ""
    
    def _is_valid_orcid(self, orcid: str) -> bool:
        """Validate ORCID format and basic structure."""
        if not orcid or not orcid.startswith('https://orcid.org/'):
            return False
        
        orcid_id = orcid.replace('https://orcid.org/', '')
        
        # Check format: 0000-0000-0000-000X
        if not re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', orcid_id):
            return False
        
        # Could add checksum validation here if needed
        return True
    
    def _is_valid_scholar_url(self, url: str) -> bool:
        """Validate Google Scholar URL format."""
        try:
            parsed = urlparse(url)
            if 'scholar.google' not in parsed.netloc:
                return False
            
            if 'citations' not in parsed.path:
                return False
            
            # Should have user parameter or other valid parameters
            query_params = parse_qs(parsed.query)
            return bool(query_params.get('user') or query_params.get('hl'))
            
        except Exception:
            return False
    
    def _deduplicate_urls(self, urls: List[str]) -> List[str]:
        """Remove duplicate URLs, keeping the best version."""
        if not urls:
            return []
        
        # Use set for basic deduplication, but prefer https over http
        unique_urls = {}
        
        for url in urls:
            if not url:
                continue
            
            # Normalize for comparison
            normalized = url.lower().replace('http://', 'https://')
            
            # Keep the https version if we have both
            if normalized not in unique_urls or url.startswith('https://'):
                unique_urls[normalized] = url
        
        return sorted(list(unique_urls.values()))
    
    def _create_entries(self, filename: str, orcids: List[str], scholars: List[str]) -> List[Dict[str, str]]:
        """Create entries for all combinations, with limits."""
        entries = []
        max_entries = self.config.get('max_entries_per_file', 50)
        
        if orcids and scholars:
            # Create combinations but limit total entries
            combinations = list(product(orcids, scholars))
            if len(combinations) > max_entries:
                logger.warning(f"Limiting {filename} to {max_entries} entries (found {len(combinations)} combinations)")
                combinations = combinations[:max_entries]
            
            for orcid, scholar in combinations:
                entries.append({
                    'filename': filename,
                    'orcid': orcid,
                    'google_scholar': scholar
                })
                
        elif orcids:
            for orcid in orcids[:max_entries]:
                entries.append({
                    'filename': filename,
                    'orcid': orcid,
                    'google_scholar': ''
                })
                
        elif scholars:
            for scholar in scholars[:max_entries]:
                entries.append({
                    'filename': filename,
                    'orcid': '',
                    'google_scholar': scholar
                })
        else:
            # No data found
            entries.append({
                'filename': filename,
                'orcid': '',
                'google_scholar': ''
            })
        
        return entries
