"""
Enhanced pattern definitions and configuration.
"""

# Enhanced regex patterns for better extraction
PATTERNS = {
    'orcid': {
        # Standard ORCID URL patterns
        'orcid_url_https': r'https://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_url_http': r'http://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_url_no_protocol': r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        
        # ORCID field patterns
        'orcid_field_colon': r'ORCID\s*:\s*(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_field_dash': r'ORCID\s*-\s*(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_field_space': r'ORCID\s+(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        
        # ORCID in parentheses
        'orcid_parentheses': r'\(\s*(?:ORCID:?\s*)?(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\s*\)',
        
        # Bare ORCID IDs (more careful matching)
        'orcid_bare_after_name': r'[A-Z][a-z]+\s+[A-Z][a-z]+.*?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_bare_standalone': r'(?:^|\s)(\d{4}-\d{4}-\d{4}-\d{3}[\dX])(?:\s|$)',
        
        # DOI-style ORCID references
        'orcid_doi_style': r'(?:doi\.org/|DOI:?\s*)?(?:https?://)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
    },
    
    'google_scholar': {
        # Full Google Scholar URLs
        'scholar_full_https': r'(https://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        'scholar_full_http': r'(http://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        
        # Scholar URLs without protocol
        'scholar_no_protocol': r'(scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        
        # User-specific patterns
        'scholar_user_param': r'(https?://scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+[^)\s,;]*)',
        'scholar_user_bare': r'(scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        
        # Field patterns
        'scholar_field_colon': r'(?:Google\s*Scholar\s*:?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        'scholar_field_profile': r'(?:Scholar\s*Profile\s*:?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s,;]+)',
        
        # Parentheses patterns
        'scholar_parentheses': r'\((https?://scholar\.google\.[a-z.]+/citations\?[^)]+)\)',
        'scholar_parentheses_no_protocol': r'\((scholar\.google\.[a-z.]+/citations\?[^)]+)\)',
        
        # Clean patterns for common variations
        'scholar_clean_url': r'(https?://scholar\.google\.[a-z.]+/citations\?(?:user=[A-Za-z0-9_-]+|hl=[a-z]+)(?:&(?:user=[A-Za-z0-9_-]+|hl=[a-z]+))*)',
    }
}

# Configuration settings
CONFIG = {
    'max_entries_per_file': 20,      # Limit entries per file to prevent runaway extraction
    'min_url_length': 15,            # Minimum URL length to consider valid
    'max_url_length': 500,           # Maximum URL length to prevent malformed URLs
    'supported_extensions': ['.pdf'],
    'output_encoding': 'utf-8',
    
    # Validation settings
    'validate_orcid_checksum': False,  # Enable ORCID checksum validation
    'normalize_scholar_urls': True,    # Clean up Scholar URLs
    'deduplicate_similar_urls': True,  # Remove very similar URLs
    
    # Processing limits
    'max_text_length': 1000000,       # Skip files with excessive text (1MB)
    'max_hyperlinks': 1000,           # Skip files with excessive hyperlinks
}

# Parallel processing configuration
PARALLEL_CONFIG = {
    'default_executor': 'process',     # 'process' or 'thread'
    'max_workers_multiplier': 2,      # CPU cores * this value
    'max_absolute_workers': 16,       # Hard limit
    'chunk_size': 1,                  # Files per worker batch
    'timeout_per_file': 60,           # Seconds per file
    'memory_limit_mb': 512,           # Memory limit per worker
    'retry_failed_files': False,      # Retry failed files with different method
}

# Performance profiles for different use cases
PERFORMANCE_PROFILES = {
    'fast': {
        'description': 'Fast processing with minimal accuracy checks',
        'pdf_library_preference': ['pymupdf', 'pypdf2', 'pdfplumber'],
        'max_workers': 8,
        'timeout': 30,
        'validate_urls': False,
        'max_entries_per_file': 10,
    },
    'accurate': {
        'description': 'Thorough processing with maximum accuracy',
        'pdf_library_preference': ['pdfplumber', 'pymupdf', 'pypdf2'],
        'max_workers': 4,
        'timeout': 120,
        'validate_urls': True,
        'max_entries_per_file': 50,
    },
    'balanced': {
        'description': 'Balanced speed and accuracy',
        'pdf_library_preference': ['pymupdf', 'pdfplumber', 'pypdf2'],
        'max_workers': 6,
        'timeout': 60,
        'validate_urls': True,
        'max_entries_per_file': 20,
    }
}

# URL normalization rules
URL_NORMALIZATION = {
    'orcid': {
        'force_https': True,
        'remove_www': True,
        'standardize_format': True,
    },
    'scholar': {
        'force_https': True,
        'clean_parameters': True,
        'remove_tracking': True,
    }
}
