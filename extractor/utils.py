"""
Utility functions for the PDF extractor
"""

import logging
import sys
from pathlib import Path
from typing import List

def setup_logging(level: str = 'INFO'):
    """Setup logging configuration"""
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pdf_extractor.log')
        ]
    )

def validate_files(file_paths: List[Path]) -> List[Path]:
    """Validate that files exist and are readable"""
    
    valid_files = []
    for file_path in file_paths:
        if file_path.exists() and file_path.is_file():
            if file_path.suffix.lower() == '.pdf':
                valid_files.append(file_path)
            else:
                logging.warning(f"Skipping non-PDF file: {file_path}")
        else:
            logging.error(f"File not found or not accessible: {file_path}")
    
    return valid_files

def clean_text_for_csv(text: str) -> str:
    """Clean text for safe CSV storage"""
    if not text:
        return ""
    
    # Remove newlines and excessive whitespace
    text = ' '.join(text.split())
    
    # Escape quotes
    text = text.replace('"', '""')
    
    return text

def format_orcid(orcid: str) -> str:
    """Format ORCID to standard format"""
    if not orcid:
        return ""
    
    # Extract ORCID ID if it's a full URL
    if 'orcid.org/' in orcid:
        orcid = orcid.split('orcid.org/')[-1]
    
    # Ensure proper format
    if len(orcid) == 19 and orcid.count('-') == 3:
        return f"https://orcid.org/{orcid}"
    
    return orcid
