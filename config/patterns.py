"""
Pattern definitions for extracting information from PDFs
"""

PATTERNS = {
    'name': {
        # Common CV patterns
        'header_name': r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'name_field': r'(?:Name\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'applicant_name': r'(?:Applicant\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'full_name': r'(?:Full\s*Name\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        # First line name (common in CVs)
        'first_line': r'^([A-Z][A-Za-z\-\']+(?:\s+[A-Z][A-Za-z\-\']+)+)',
    },
    
    'orcid': {
        # ORCID URL patterns
        'orcid_url': r'(?:https?://)?(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_field': r'(?:ORCID\s*[:\-]?\s*)(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_id': r'ORCID[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_bare': r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
    },
    
    'google_scholar': {
        # Google Scholar URL patterns
        'scholar_full_url': r'(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_citations': r'(scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_user': r'(https?://scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        'scholar_field': r'(?:Google\s*Scholar\s*[:\-]?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
    }
}

# Additional configuration
CONFIG = {
    'max_name_words': 5,
    'min_name_length': 2,
    'supported_extensions': ['.pdf'],
    'output_encoding': 'utf-8'
}
