"""
Pattern definitions for extracting information from PDFs
"""

PATTERNS = {
    'orcid': {
        # ORCID URL patterns
        'orcid_url': r'(?:https?://)?(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_field': r'(?:ORCID\s*[:\-]?\s*)(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_id': r'ORCID[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_bare': r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        # Additional ORCID patterns for better detection
        'orcid_doi': r'(?:doi\.org/|DOI:?\s*)?(?:https?://)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_parentheses': r'\((?:ORCID:?\s*)?(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\)',
    },
    
    'google_scholar': {
        # Google Scholar URL patterns
        'scholar_full_url': r'(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_citations': r'(scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_user': r'(https?://scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        'scholar_field': r'(?:Google\s*Scholar\s*[:\-]?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        # Additional patterns for better detection
        'scholar_profile': r'(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]*user=[A-Za-z0-9_-]+[^)\s]*)',
        'scholar_parentheses': r'\((https?://scholar\.google\.[a-z.]+/citations\?[^)]+)\)',
        'scholar_bare': r'(scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
    }
}

# Additional configuration
CONFIG = {
    'supported_extensions': ['.pdf'],
    'output_encoding': 'utf-8',
    'max_entries_per_file': 50,  # Prevent runaway extraction
    'min_url_length': 10,
}

# Parallel processing configuration
PARALLEL_CONFIG = {
    'default_executor': 'process',  # 'process' or 'thread'
    'max_workers_multiplier': 2,   # multiplier for CPU count
    'max_absolute_workers': 16,    # hard limit on workers
    'chunk_size': 1,               # files per worker batch
    'timeout_per_file': 30,        # seconds per file timeout
    'memory_limit_mb': 512,        # memory limit per worker (MB)
}

# Performance tuning based on file characteristics
PERFORMANCE_PROFILES = {
    'fast': {
        'pdf_library_preference': ['pymupdf', 'pypdf2', 'pdfplumber'],
        'max_workers': 8,
        'timeout': 15
    },
    'accurate': {
        'pdf_library_preference': ['pdfplumber', 'pymupdf', 'pypdf2'],
        'max_workers': 4,
        'timeout': 60
    },
    'balanced': {
        'pdf_library_preference': ['pymupdf', 'pdfplumber', 'pypdf2'],
        'max_workers': 6,
        'timeout': 30
    }
}
