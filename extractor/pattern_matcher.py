"""
Pattern matching module for extracting specific information from text
"""

import re
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from itertools import product

from config.patterns import PATTERNS, CONFIG

logger = logging.getLogger(__name__)

class PatternMatcher:
    """Extracts structured information from unstructured text"""
    
    def __init__(self):
        self.patterns = PATTERNS
        self.config = CONFIG
    
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
        
        # Apply safety limits
        max_entries = self.config.get('max_entries_per_file', 50)
        if len(orcids) * len(google_scholars) > max_entries:
            logger.warning(f"Too many URL combinations in {filename}. Limiting to first {max_entries} entries.")
            # Trim to reasonable numbers
            max_each = int((max_entries ** 0.5)) + 1
            orcids = orcids[:max_each]
            google_scholars = google_scholars[:max_each]
        
        # Create entries for all combinations
        entries = self._create_entries(filename, orcids, google_scholars)
        
        logger.debug(f"Found {len(orcids)} ORCIDs and {len(google_scholars)} Google Scholar URLs in {filename}")
        logger.info(f"Created {len(entries)} entries for {filename}")
        
        return entries
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere with URL detection
        text = re.sub(r'[^\w\s\-@.:/?=&()_]', ' ', text)
        return text.strip()
    
    def _extract_all_orcids(self, text: str) -> List[str]:
        """Extract all ORCID URLs from text"""
        
        orcids = set()  # Use set to avoid duplicates
        
        # Try each ORCID pattern
        for pattern_name, pattern in self.patterns['orcid'].items():
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        # Handle different match types (groups vs full matches)
                        match_text = match if isinstance(match, str) else match[0] if match else ""
                        orcid_id = self._normalize_orcid(match_text)
                        
                        if orcid_id and self._is_valid_orcid(orcid_id):
                            orcids.add(orcid_id)
                            logger.debug(f"Found ORCID using pattern '{pattern_name}': {orcid_id}")
            except Exception as e:
                logger.warning(f"Error in ORCID pattern '{pattern_name}': {str(e)}")
                continue
        
        return sorted(list(orcids))  # Sort for consistency
    
    def _extract_all_google_scholars(self, text: str) -> List[str]:
        """Extract all Google Scholar URLs from text"""
        
        scholars = set()  # Use set to avoid duplicates
        
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        # Handle different match types
                        match_text = match if isinstance(match, str) else match[0] if match else ""
                        url = self._normalize_url(match_text)
                        
                        if url and self._is_valid_google_scholar_url(url):
                            scholars.add(url)
                            logger.debug(f"Found Google Scholar using pattern '{pattern_name}': {url}")
            except Exception as e:
                logger.warning(f"Error in Google Scholar pattern '{pattern_name}': {str(e)}")
                continue
        
        return sorted(list(scholars))  # Sort for consistency
    
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
        if not orcid_text or not isinstance(orcid_text, str):
            return ""
        
        # Clean the text
        orcid_text = orcid_text.strip()
        
        # Extract just the ORCID digits and hyphens
        orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_text)
        if orcid_match:
            orcid_id = orcid_match.group(1)
            return f"https://orcid.org/{orcid_id}"
        
        return ""
    
    def _is_valid_orcid(self, orcid: str) -> bool:
        """Validate ORCID format and basic structure"""
        if not orcid or not isinstance(orcid, str):
            return False
        
        # Extract ORCID ID from URL
        if 'orcid.org/' in orcid:
            orcid_id = orcid.split('orcid.org/')[-1]
        else:
            orcid_id = orcid
        
        # Check format: 0000-0000-0000-000X (where X can be digit or X)
        if not re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', orcid_id):
            return False
        
        # Basic length check
        if len(orcid_id) != 19:  # 16 digits + 3 hyphens
            return False
        
        return True
    
    def _normalize_url(self, url_text: str) -> str:
        """Normalize URL format"""
        if not url_text or not isinstance(url_text, str):
            return ""
        
        url = url_text.strip()
        
        # Remove common wrapper characters
        url = url.strip('()[]{}')
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            if 'scholar.google' in url:
                url = 'https://' + url
        
        # Check minimum length
        min_length = self.config.get('min_url_length', 10)
        if len(url) < min_length:
            return ""
        
        return url
    
    def _is_valid_google_scholar_url(self, url: str) -> bool:
        """Validate Google Scholar URL"""
        if not url or not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            
            # Check domain
            if 'scholar.google' not in parsed.netloc:
                return False
            
            # Check for required components
            if not ('citations' in url or 'user=' in url):
                return False
            
            # Check for common parameters that indicate a profile
            valid_params = ['user=', 'citations?', 'hl=', 'cstart=']
            if not any(param in url for param in valid_params):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"URL validation error for {url}: {str(e)}")
            return False
    
    def get_extraction_stats(self, text: str) -> Dict[str, int]:
        """
        Get statistics about what could be extracted from text
        Useful for debugging and analysis
        
        Returns:
            Dictionary with counts of potential matches
        """
        cleaned_text = self._clean_text(text)
        
        stats = {
            'orcid_patterns': {},
            'scholar_patterns': {},
            'total_orcids': 0,
            'total_scholars': 0
        }
        
        # Count matches for each ORCID pattern
        for pattern_name, pattern in self.patterns['orcid'].items():
            try:
                matches = re.findall(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                valid_matches = [self._normalize_orcid(m) for m in matches if self._normalize_orcid(m)]
                stats['orcid_patterns'][pattern_name] = len(valid_matches)
                stats['total_orcids'] += len(valid_matches)
            except:
                stats['orcid_patterns'][pattern_name] = 0
        
        # Count matches for each Google Scholar pattern
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            try:
                matches = re.findall(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                valid_matches = [self._normalize_url(m) for m in matches if self._is_valid_google_scholar_url(self._normalize_url(m))]
                stats['scholar_patterns'][pattern_name] = len(valid_matches)
                stats['total_scholars'] += len(valid_matches)
            except:
                stats['scholar_patterns'][pattern_name] = 0
        
        return stats
