"""
Optimized streaming pattern matcher with early termination and caching.
"""

import re
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs
from itertools import product
from dataclasses import dataclass
from functools import lru_cache

from config.patterns import PATTERNS, CONFIG

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """Container for pattern matching results."""
    orcids: List[str]
    scholars: List[str]
    processing_time: float
    patterns_matched: Dict[str, int]
    early_terminated: bool

class OptimizedPatternMatcher:
    """Optimized pattern matcher with streaming and caching capabilities."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.patterns = PATTERNS
        self.enable_early_termination = config.get('early_termination', False)
        self.early_stop_threshold = config.get('early_stop_threshold', 3)
        
        # Compile patterns for better performance
        self.compiled_patterns = self._compile_patterns()
        
        # Cache for repeated patterns
        self._validation_cache = {}
        
        logger.debug(f"🔍 Pattern matcher initialized with {len(self.compiled_patterns['orcid'])} ORCID patterns")
        logger.debug(f"🔍 Early termination: {self.enable_early_termination}")
    
    def _compile_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Compile all patterns for better performance."""
        compiled = {'orcid': {}, 'google_scholar': {}}
        
        for pattern_type in ['orcid', 'google_scholar']:
            for pattern_name, pattern in self.patterns[pattern_type].items():
                try:
                    compiled[pattern_type][pattern_name] = re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    logger.warning(f"❌ Failed to compile pattern {pattern_name}: {e}")
        
        return compiled
    
    def extract_info_streaming(self, text: str, filename: str, 
                              hyperlinks: List[str] = None) -> Tuple[List[Dict[str, str]], MatchResult]:
        """
        Streaming extraction with early termination and optimization.
        
        Args:
            text: Text content from PDF
            filename: Original filename
            hyperlinks: List of hyperlinks extracted from PDF
            
        Returns:
            Tuple of (entries, match_result)
        """
        start_time = time.time()
        
        if hyperlinks is None:
            hyperlinks = []
        
        # Initialize tracking
        found_orcids = set()
        found_scholars = set()
        patterns_matched = {'orcid': {}, 'google_scholar': {}}
        early_terminated = False
        
        # Process hyperlinks first (usually more reliable)
        link_orcids, link_scholars = self._extract_from_hyperlinks_optimized(hyperlinks)
        found_orcids.update(link_orcids)
        found_scholars.update(link_scholars)
        
        # Check for early termination after hyperlinks
        if self.enable_early_termination and len(found_orcids) + len(found_scholars) >= self.early_stop_threshold:
            early_terminated = True
        else:
            # Process text in chunks for better memory usage
            text_orcids, text_scholars, text_patterns = self._extract_from_text_streaming(text, early_terminated)
            found_orcids.update(text_orcids)
            found_scholars.update(text_scholars)
            
            # Update pattern statistics
            for pattern_type in ['orcid', 'google_scholar']:
                patterns_matched[pattern_type].update(text_patterns.get(pattern_type, {}))
        
        # Deduplicate and validate
        final_orcids = self._deduplicate_and_validate_orcids(list(found_orcids))
        final_scholars = self._deduplicate_and_validate_scholars(list(found_scholars))
        
        # Create match result
        match_result = MatchResult(
            orcids=final_orcids,
            scholars=final_scholars,
            processing_time=time.time() - start_time,
            patterns_matched=patterns_matched,
            early_terminated=early_terminated
        )
        
        # Create entries
        entries = self._create_entries_optimized(filename, final_orcids, final_scholars)
        
        logger.debug(f"📊 {filename}: {len(final_orcids)} ORCIDs, {len(final_scholars)} Scholar URLs "
                    f"(early_stop: {early_terminated})")
        
        return entries, match_result
    
    def _extract_from_hyperlinks_optimized(self, hyperlinks: List[str]) -> Tuple[List[str], List[str]]:
        """Optimized hyperlink extraction."""
        orcids = set()
        scholars = set()
        
        for link in hyperlinks:
            if not link or not isinstance(link, str):
                continue
            
            link_lower = link.lower()
            
            # Fast path for common cases
            if 'orcid.org' in link_lower:
                orcid = self._normalize_orcid_from_link(link)
                if orcid:
                    orcids.add(orcid)
            elif 'scholar.google' in link_lower:
                scholar = self._normalize_scholar_from_link(link)
                if scholar:
                    scholars.add(scholar)
        
        return list(orcids), list(scholars)
    
    def _extract_from_text_streaming(self, text: str, early_terminated: bool) -> Tuple[Set[str], Set[str], Dict]:
        """Stream text processing with early termination."""
        if early_terminated or not text:
            return set(), set(), {}
        
        # Clean text once
        cleaned_text = self._clean_text_optimized(text)
        
        orcids = set()
        scholars = set()
        patterns_matched = {'orcid': {}, 'google_scholar': {}}
        
        # Process ORCID patterns
        for pattern_name, compiled_pattern in self.compiled_patterns['orcid'].items():
            matches = compiled_pattern.findall(cleaned_text)
            patterns_matched['orcid'][pattern_name] = len(matches)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                
                orcid = self._normalize_orcid(match)
                if orcid:
                    orcids.add(orcid)
                    
                    # Early termination check
                    if self.enable_early_termination and len(orcids) >= self.early_stop_threshold:
                        break
        
        # Process Scholar patterns if not early terminated
        if not (self.enable_early_termination and len(orcids) >= self.early_stop_threshold):
            for pattern_name, compiled_pattern in self.compiled_patterns['google_scholar'].items():
                matches = compiled_pattern.findall(cleaned_text)
                patterns_matched['google_scholar'][pattern_name] = len(matches)
                
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                    
                    scholar = self._normalize_scholar_url(match)
                    if scholar:
                        scholars.add(scholar)
                        
                        # Early termination check
                        if self.enable_early_termination and len(orcids) + len(scholars) >= self.early_stop_threshold:
                            break
        
        return orcids, scholars, patterns_matched
    
    def _clean_text_optimized(self, text: str) -> str:
        """Optimized text cleaning."""
        if not text:
            return ""
        
        # More efficient cleaning
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-@.:/?=&_]', ' ', text)
        return text.strip()
    
    @lru_cache(maxsize=1000)
    def _normalize_orcid(self, orcid_text: str) -> str:
        """Cached ORCID normalization."""
        if not orcid_text:
            return ""
        
        # Extract ORCID ID pattern
        orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_text.upper())
        if orcid_match:
            orcid_id = orcid_match.group(1)
            return f"https://orcid.org/{orcid_id}"
        
        return ""
    
    def _normalize_orcid_from_link(self, link: str) -> str:
        """Normalize ORCID from hyperlink."""
        if not link:
            return ""
        
        # Extract ORCID ID from URL
        orcid_match = re.search(r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', link, re.IGNORECASE)
        if orcid_match:
            return f"https://orcid.org/{orcid_match.group(1)}"
        
        return ""
    
    @lru_cache(maxsize=1000)
    def _normalize_scholar_url(self, url_text: str) -> str:
        """Cached Scholar URL normalization."""
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
            url = url.split('#')[0]  # Remove fragments
            return url
        
        return ""
    
    def _normalize_scholar_from_link(self, link: str) -> str:
        """Normalize Scholar URL from hyperlink."""
        if not link or 'scholar.google' not in link.lower() or 'citations' not in link.lower():
            return ""
        
        # Clean up the URL
        url = link.split('#')[0]  # Remove fragments
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def _deduplicate_and_validate_orcids(self, orcids: List[str]) -> List[str]:
        """Deduplicate and validate ORCID URLs."""
        if not orcids:
            return []
        
        validated = set()
        for orcid in orcids:
            if self._is_valid_orcid_cached(orcid):
                validated.add(orcid)
        
        return sorted(list(validated))
    
    def _deduplicate_and_validate_scholars(self, scholars: List[str]) -> List[str]:
        """Deduplicate and validate Scholar URLs."""
        if not scholars:
            return []
        
        validated = set()
        for scholar in scholars:
            if self._is_valid_scholar_url_cached(scholar):
                validated.add(scholar)
        
        return sorted(list(validated))
    
    @lru_cache(maxsize=500)
    def _is_valid_orcid_cached(self, orcid: str) -> bool:
        """Cached ORCID validation."""
        if not orcid or not orcid.startswith('https://orcid.org/'):
            return False
        
        orcid_id = orcid.replace('https://orcid.org/', '')
        return bool(re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', orcid_id))
    
    @lru_cache(maxsize=500)
    def _is_valid_scholar_url_cached(self, url: str) -> bool:
        """Cached Scholar URL validation."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            if 'scholar.google' not in parsed.netloc:
                return False
            
            if 'citations' not in parsed.path:
                return False
            
            query_params = parse_qs(parsed.query)
            return bool(query_params.get('user') or query_params.get('hl'))
            
        except Exception:
            return False
    
    def _create_entries_optimized(self, filename: str, orcids: List[str], 
                                scholars: List[str]) -> List[Dict[str, str]]:
        """Create entries with optimization and limits."""
        entries = []
        max_entries = self.config.get('max_entries_per_file', 20)
        
        if orcids and scholars:
            # Limit combinations to prevent explosion
            max_combinations = min(len(orcids) * len(scholars), max_entries)
            combinations = list(product(orcids, scholars))[:max_combinations]
            
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
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get caching statistics."""
        return {
            'orcid_cache_size': self._normalize_orcid.cache_info().currsize,
            'scholar_cache_size': self._normalize_scholar_url.cache_info().currsize,
            'orcid_validation_cache_size': self._is_valid_orcid_cached.cache_info().currsize,
            'scholar_validation_cache_size': self._is_valid_scholar_url_cached.cache_info().currsize,
        }
