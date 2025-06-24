"""
Utility functions for the PDF extractor
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from multiprocessing import current_process

def setup_logging(level: str = 'INFO'):
    """Setup logging configuration for parallel processing"""
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure logging for parallel processing
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pdf_extractor.log')
        ],
        force=True  # Override any existing configuration
    )

def process_single_pdf(pdf_file: Path) -> Dict[str, Any]:
    """
    Process a single PDF file - designed for parallel execution
    
    Args:
        pdf_file: Path to the PDF file to process
        
    Returns:
        Dict containing success status, data (list of records), and error information
    """
    from extractor.pdf_processor import PDFProcessor
    from extractor.pattern_matcher import PatternMatcher
    
    # Setup minimal logging for worker process
    logger = logging.getLogger(f"worker.{current_process().name}")
    
    result = {
        'success': False,
        'data': [],  # Now a list of records instead of a single record
        'error': None,
        'filename': pdf_file.name,
        'record_count': 0
    }
    
    try:
        # Initialize processors (each worker gets its own instances)
        pdf_processor = PDFProcessor()
        pattern_matcher = PatternMatcher()
        
        logger.debug(f"Starting processing of {pdf_file.name}")
        
        # Extract text from PDF
        text = pdf_processor.extract_text(pdf_file)
        if not text.strip():
            result['error'] = "No text extracted from PDF"
            return result
        
        # Extract information - now returns a list of records
        extracted_records = pattern_matcher.extract_info(text, pdf_file.name)
        
        result['success'] = True
        result['data'] = extracted_records
        result['record_count'] = len(extracted_records)
        logger.debug(f"Successfully processed {pdf_file.name} - found {len(extracted_records)} records")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error processing {pdf_file.name}: {str(e)}")
    
    return result

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

def get_optimal_workers(num_files: int, max_workers: int = None) -> int:
    """
    Calculate optimal number of workers based on system and workload
    
    Args:
        num_files: Number of files to process
        max_workers: Maximum workers to use (default: auto-detect)
        
    Returns:
        Optimal number of workers
    """
    import multiprocessing
    
    cpu_cores = multiprocessing.cpu_count()
    
    if max_workers is None:
        # Use CPU cores as baseline, but consider I/O-bound nature
        optimal = min(cpu_cores * 2, num_files)
        # Cap at reasonable maximum to avoid resource exhaustion
        optimal = min(optimal, 16)
    else:
        optimal = min(max_workers, num_files)
    
    return max(1, optimal)

def estimate_processing_time(num_files: int, workers: int, avg_time_per_file: float = 2.0) -> float:
    """
    Estimate total processing time
    
    Args:
        num_files: Number of files to process
        workers: Number of parallel workers
        avg_time_per_file: Average processing time per file in seconds
        
    Returns:
        Estimated processing time in seconds
    """
    return (num_files * avg_time_per_file) / workers

def create_progress_callback(total_files: int, logger: logging.Logger):
    """Create a progress callback for monitoring parallel execution"""
    
    def callback(future):
        # This would be called when each future completes
        # Can be used for more sophisticated progress tracking
        pass
    
    return callback
