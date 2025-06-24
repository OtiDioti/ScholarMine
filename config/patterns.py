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
        # Supervisor/Reference patterns (for multi-person documents)
        'supervisor_name': r'(?:Supervisor\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'advisor_name': r'(?:Advisor\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'reference_name': r'(?:Reference\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'co_author': r'(?:Co-author\s*[:\-]?\s*)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        # Dr./Prof. titles
        'dr_name': r'(?:Dr\.?\s+)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'prof_name': r'(?:Prof\.?\s+)([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        # Publication author patterns
        'author_list': r'([A-Z][a-z]+,\s*[A-Z]\.(?:\s*[A-Z]\.)*)',  # Last, F.M. format
        'and_author': r'(?:and\s+)([A-Z][a-z]+ [A-Z][a-z]+)',
    },
    
    'orcid': {
        # ORCID URL patterns
        'orcid_url': r'(?:https?://)?(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_field': r'(?:ORCID\s*[:\-]?\s*)(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_id': r'ORCID[:\s]*(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        'orcid_bare': r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
        # Additional ORCID patterns
        'orcid_parentheses': r'\((?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\)',
        'orcid_bracket': r'\[(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\]',
    },
    
    'google_scholar': {
        # Google Scholar URL patterns
        'scholar_full_url': r'(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_citations': r'(scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        'scholar_user': r'(https?://scholar\.google\.[a-z.]+/citations\?user=[A-Za-z0-9_-]+)',
        'scholar_field': r'(?:Google\s*Scholar\s*[:\-]?\s*)(https?://scholar\.google\.[a-z.]+/citations\?[^)\s]+)',
        # Additional Scholar patterns
        'scholar_parentheses': r'\((https?://scholar\.google\.[a-z.]+/citations\?[^)]+)\)',
        'scholar_bracket': r'\[(https?://scholar\.google\.[a-z.]+/citations\?[^\]]+)\]',
    }
}

# Additional configuration
CONFIG = {
    'max_name_words': 5,
    'min_name_length': 2,
    'supported_extensions': ['.pdf'],
    'output_encoding': 'utf-8'
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
