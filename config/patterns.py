"""
Optimized pattern definitions with performance improvements.
"""

# Highly optimized regex patterns
PATTERNS = {
    'orcid': {
        # Most common patterns first for better performance
        'orcid_url_https': r'https://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_url_http': r'http://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_bare_id': r'(?:^|\s)(\d{4}-\d{4}-\d{4}-\d{3}[\dX])(?:\s|$)',
        'orcid_field_colon': r'ORCID\s*:\s*(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_parentheses': r'\(\s*(?:ORCID:?\s*)?(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\s*\)',
        'orcid_url_no_protocol': r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
    },
    
    'google_scholar': {
        # Most reliable patterns first
        'scholar_user_param': r'(https?://scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        'scholar_full_https': r'(https://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        'scholar_no_protocol': r'(scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        'scholar_parentheses': r'\((https?://scholar\.google\.[a-z.]+/citations\?[^)]+)\)',
        'scholar_field_colon': r'(?:Google\s*Scholar\s*:?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
    }
}

# Optimized configuration
CONFIG = {
    'max_entries_per_file': 10,      # Reduced for better performance
    'min_url_length': 15,
    'max_url_length': 300,           # Reduced to filter out malformed URLs
    'supported_extensions': ['.pdf'],
    'output_encoding': 'utf-8',
    
    # Validation settings
    'validate_orcid_checksum': False,
    'normalize_scholar_urls': True,
    'deduplicate_similar_urls': True,
    
    # Processing limits
    'max_text_length': 500000,       # Reduced for better performance
    'max_hyperlinks': 100,           # Reduced limit
    'min_text_per_page': 50,         # Minimum text to consider page useful
}

# Performance profiles optimized for different use cases
PERFORMANCE_PROFILES = {
    'fast': {
        'description': 'Maximum speed with basic accuracy',
        'pdf_library_preference': ['pymupdf', 'pypdf2'],
        'max_workers': 8,
        'timeout_per_file': 30,
        'max_entries_per_file': 5,
        'early_termination': True,
        'early_stop_threshold': 2,
        'page_parallel': False,
        'max_pages_to_process': 10,
        'priority_pages': [0, 1],
        'enable_cache': True,
        'cache_size': 500,
    },
    'balanced': {
        'description': 'Balanced speed and accuracy',
        'pdf_library_preference': ['pymupdf', 'pdfplumber'],
        'max_workers': 6,
        'timeout_per_file': 60,
        'max_entries_per_file': 10,
        'early_termination': True,
        'early_stop_threshold': 3,
        'page_parallel': True,
        'max_pages_to_process': 25,
        'priority_pages': [0, 1, 2],
        'enable_cache': True,
        'cache_size': 1000,
    },
    'accurate': {
        'description': 'Maximum accuracy with thorough processing',
        'pdf_library_preference': ['pdfplumber', 'pymupdf'],
        'max_workers': 4,
        'timeout_per_file': 120,
        'max_entries_per_file': 20,
        'early_termination': False,
        'early_stop_threshold': 5,
        'page_parallel': True,
        'max_pages_to_process': 50,
        'priority_pages': [0, 1, 2, 3, 4],
        'enable_cache': True,
        'cache_size': 2000,
    }
}
