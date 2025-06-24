"""
Pattern matching module for extracting specific information from text
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict

from config.patterns import PATTERNS

logger = logging.getLogger(__name__)

class PatternMatcher:
    """Extracts structured information from unstructured text"""
    
    def __init__(self):
        self.patterns = PATTERNS
    
    def extract_info(self, text: str, filename: str) -> List[Dict[str, str]]:
        """Extract multiple applicant records from text (one per person found)"""
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Extract all possible information
        all_names = self._extract_all_names(cleaned_text)
        all_orcids = self._extract_all_orcids(cleaned_text)
        all_google_scholars = self._extract_all_google_scholars(cleaned_text)
        
        logger.debug(f"Found in {filename}: {len(all_names)} names, {len(all_orcids)} ORCIDs, {len(all_google_scholars)} Google Scholar URLs")
        
        # Create applicant records
        records = self._create_applicant_records(
            filename, all_names, all_orcids, all_google_scholars, cleaned_text
        )
        
        # If no specific records found, create one default entry
        if not records:
            records = [{
                'filename': filename,
                'name': '',
                'orcid': '',
                'google_scholar': '',
                'record_number': 1
            }]
        
        return records
    
    def _create_applicant_records(self, filename: str, names: List[str], 
                                orcids: List[str], google_scholars: List[str], 
                                text: str) -> List[Dict[str, str]]:
        """Create individual applicant records by associating names with IDs"""
        
        records = []
        
        # Try to associate names with ORCIDs and Google Scholar URLs
        associations = self._associate_names_with_ids(names, orcids, google_scholars, text)
        
        record_number = 1
        
        # Create records from associations
        for association in associations:
            record = {
                'filename': filename,
                'name': association['name'],
                'orcid': association['orcid'],
                'google_scholar': association['google_scholar'],
                'record_number': record_number
            }
            records.append(record)
            record_number += 1
        
        # Add any remaining unassociated ORCIDs
        used_orcids = {assoc['orcid'] for assoc in associations if assoc['orcid']}
        for orcid in orcids:
            if orcid not in used_orcids:
                record = {
                    'filename': filename,
                    'name': '',
                    'orcid': orcid,
                    'google_scholar': '',
                    'record_number': record_number
                }
                records.append(record)
                record_number += 1
        
        # Add any remaining unassociated Google Scholar URLs
        used_scholars = {assoc['google_scholar'] for assoc in associations if assoc['google_scholar']}
        for scholar_url in google_scholars:
            if scholar_url not in used_scholars:
                record = {
                    'filename': filename,
                    'name': '',
                    'orcid': '',
                    'google_scholar': scholar_url,
                    'record_number': record_number
                }
                records.append(record)
                record_number += 1
        
        return records
    
    def _associate_names_with_ids(self, names: List[str], orcids: List[str], 
                                google_scholars: List[str], text: str) -> List[Dict[str, str]]:
        """Associate names with their corresponding ORCID and Google Scholar URLs"""
        
        associations = []
        
        if not names and not orcids and not google_scholars:
            return associations
        
        # If we have only one of each, associate them
        if len(names) == 1 and len(orcids) <= 1 and len(google_scholars) <= 1:
            association = {
                'name': names[0] if names else '',
                'orcid': orcids[0] if orcids else '',
                'google_scholar': google_scholars[0] if google_scholars else ''
            }
            associations.append(association)
            return associations
        
        # Try to find associations by proximity in text
        text_lower = text.lower()
        
        for name in names:
            name_pos = text_lower.find(name.lower())
            if name_pos == -1:
                continue
            
            best_orcid = self._find_closest_id(name, name_pos, orcids, text_lower, 'orcid')
            best_scholar = self._find_closest_id(name, name_pos, google_scholars, text_lower, 'scholar')
            
            association = {
                'name': name,
                'orcid': best_orcid,
                'google_scholar': best_scholar
            }
            associations.append(association)
        
        return associations
    
    def _find_closest_id(self, name: str, name_pos: int, ids: List[str], 
                        text: str, id_type: str) -> str:
        """Find the closest ORCID or Google Scholar URL to a name in the text"""
        
        if not ids:
            return ''
        
        closest_id = ''
        min_distance = float('inf')
        
        for id_value in ids:
            # Find all occurrences of this ID in the text
            id_positions = []
            search_term = id_value.lower()
            
            # For ORCID, also search for just the ID part
            if id_type == 'orcid' and 'orcid.org/' in search_term:
                id_part = search_term.split('orcid.org/')[-1]
                id_positions.extend([m.start() for m in re.finditer(re.escape(id_part), text)])
            
            # Search for the full ID
            id_positions.extend([m.start() for m in re.finditer(re.escape(search_term), text)])
            
            # Find the closest position to the name
            for id_pos in id_positions:
                distance = abs(id_pos - name_pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_id = id_value
        
        # Only return if reasonably close (within 1000 characters)
        return closest_id if min_distance < 1000 else ''
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\-@.:/?=&]', ' ', text)
        return text.strip()
    
    def _extract_all_names(self, text: str) -> List[str]:
        """Extract all possible names from text"""
        names = []
        seen_names = set()
        
        # Try each name pattern
        for pattern_name, pattern in self.patterns['name'].items():
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                candidate = match.strip() if isinstance(match, str) else match[0].strip()
                if self._is_valid_name(candidate) and candidate.lower() not in seen_names:
                    names.append(candidate)
                    seen_names.add(candidate.lower())
                    logger.debug(f"Found name using pattern '{pattern_name}': {candidate}")
        
        return names
    
    def _extract_all_orcids(self, text: str) -> List[str]:
        """Extract all ORCID IDs from text"""
        orcids = []
        seen_orcids = set()
        
        for pattern_name, pattern in self.patterns['orcid'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                orcid_id = self._normalize_orcid(match)
                if orcid_id and orcid_id not in seen_orcids:
                    orcids.append(orcid_id)
                    seen_orcids.add(orcid_id)
                    logger.debug(f"Found ORCID using pattern '{pattern_name}': {orcid_id}")
        
        return orcids
    
    def _extract_all_google_scholars(self, text: str) -> List[str]:
        """Extract all Google Scholar URLs from text"""
        scholar_urls = []
        seen_urls = set()
        
        for pattern_name, pattern in self.patterns['google_scholar'].items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                url = self._normalize_url(match)
                if self._is_valid_google_scholar_url(url) and url not in seen_urls:
                    scholar_urls.append(url)
                    seen_urls.add(url)
                    logger.debug(f"Found Google Scholar using pattern '{pattern_name}': {url}")
        
        return scholar_urls
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate if extracted text is a reasonable name"""
        if not name or len(name) < 2:
            return False
        
        # Check if it contains at least some letters
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        # Avoid common false positives
        false_positives = ['email', 'phone', 'address', 'university', 'department', 
                          'orcid', 'scholar', 'google', 'http', 'www', 'com']
        if any(fp in name.lower() for fp in false_positives):
            return False
        
        # Skip very long strings (likely not names)
        if len(name) > 100:
            return False
        
        # Must contain at least one space (first + last name)
        if ' ' not in name.strip():
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
