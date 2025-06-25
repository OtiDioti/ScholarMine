"""
Enhanced utility functions with better error handling and logging.
"""

import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from multiprocessing import current_process, cpu_count
import time

def setup_logging(level: str = 'INFO') -> None:
    """Setup enhanced logging for parallel processing."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter if level == 'INFO' else detailed_formatter)
    handlers.append(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler('pdf_extractor.log', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )

def process_single_pdf(pdf_file: Path) -> Dict[str, Any]:
    """
    Enhanced single PDF processing function for parallel execution.
    
    Args:
        pdf_file: Path to the PDF file
        
    Returns:
        Dict with success status, data, error info, and stats
    """
    from extractor.pdf_processor import PDFProcessor
    from extractor.pattern_matcher import PatternMatcher
    
    logger = logging.getLogger(f"worker.{current_process().name}")
    start_time = time.time()
    
    result = {
        'success': False,
        'data': None,
        'error': None,
        'filename': pdf_file.name,
        'processing_time': 0,
        'stats': {}
    }
    
    try:
        logger.debug(f"🔄 Processing {pdf_file.name}")
        
        # Check file accessibility
        if not pdf_file.exists() or not pdf_file.is_file():
            raise FileNotFoundError(f"File not accessible: {pdf_file}")
        
        if pdf_file.stat().st_size == 0:
            raise ValueError("File is empty")
        
        # Initialize processors
        pdf_processor = PDFProcessor()
        pattern_matcher = PatternMatcher()
        
        # Extract text and hyperlinks
        text, hyperlinks = pdf_processor.extract_text_and_links(pdf_file)
        
        # Get extraction stats
        stats = {
            'text_length': len(text) if text else 0,
            'hyperlinks_found': len(hyperlinks) if hyperlinks else 0,
            'file_size_mb': pdf_file.stat().st_size / (1024 * 1024)
        }
        
        # Extract structured information
        entries = pattern_matcher.extract_info(text, pdf_file.name, hyperlinks)
        
        # Update stats
        stats.update({
            'entries_created': len(entries),
            'has_orcid': any(entry.get('orcid') for entry in entries),
            'has_scholar': any(entry.get('google_scholar') for entry in entries)
        })
        
        result.update({
            'success': True,
            'data': entries,
            'stats': stats
        })
        
        logger.debug(f"✅ {pdf_file.name}: {len(entries)} entries, "
                    f"{stats['text_length']} chars, {stats['hyperlinks_found']} links")
        
    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        result['data'] = [{
            'filename': pdf_file.name,
            'orcid': '',
            'google_scholar': ''
        }]
        logger.error(f"❌ {pdf_file.name}: {error_msg}")
    
    finally:
        result['processing_time'] = time.time() - start_time
    
    return result

def get_optimal_workers(num_files: int, max_workers: Optional[int] = None) -> int:
    """
    Calculate optimal number of workers based on system resources and workload.
    
    Args:
        num_files: Number of files to process
        max_workers: Maximum workers limit
        
    Returns:
        Optimal number of workers
    """
    cpu_cores = cpu_count()
    
    # Base calculation: consider I/O-bound nature of PDF processing
    if num_files <= 5:
        optimal = min(num_files, 2)
    elif num_files <= 20:
        optimal = min(num_files, cpu_cores)
    else:
        optimal = min(num_files, cpu_cores * 2)
    
    # Apply limits
    if max_workers:
        optimal = min(optimal, max_workers)
    
    # Absolute maximum to prevent resource exhaustion
    optimal = min(optimal, 16)
    
    return max(1, optimal)

def validate_files(file_paths: List[Path]) -> List[Path]:
    """Enhanced file validation with detailed reporting."""
    valid_files = []
    invalid_count = 0
    
    for file_path in file_paths:
        try:
            if not file_path.exists():
                logging.warning(f"❌ File not found: {file_path}")
                invalid_count += 1
                continue
            
            if not file_path.is_file():
                logging.warning(f"❌ Not a file: {file_path}")
                invalid_count += 1
                continue
            
            if file_path.suffix.lower() != '.pdf':
                logging.debug(f"⏭️ Skipping non-PDF: {file_path}")
                invalid_count += 1
                continue
            
            if file_path.stat().st_size == 0:
                logging.warning(f"❌ Empty file: {file_path}")
                invalid_count += 1
                continue
            
            valid_files.append(file_path)
            
        except Exception as e:
            logging.error(f"❌ Error checking {file_path}: {e}")
            invalid_count += 1
    
    if invalid_count > 0:
        logging.info(f"📋 Validation: {len(valid_files)} valid, {invalid_count} invalid files")
    
    return valid_files

def estimate_processing_time(num_files: int, workers: int, 
                           avg_time_per_file: float = 2.5) -> Dict[str, float]:
    """
    Estimate processing time with confidence intervals.
    
    Returns:
        Dict with time estimates
    """
    if workers <= 0 or num_files <= 0:
        return {'estimated_time': 0, 'min_time': 0, 'max_time': 0}
    
    # Base estimate
    base_time = (num_files * avg_time_per_file) / workers
    
    # Add overhead for parallel processing
    overhead = min(10, num_files * 0.1)  # Up to 10 seconds overhead
    
    estimated_time = base_time + overhead
    min_time = estimated_time * 0.7  # Best case
    max_time = estimated_time * 1.5  # Worst case
    
    return {
        'estimated_time': estimated_time,
        'min_time': min_time,
        'max_time': max_time,
        'files_per_second': workers / avg_time_per_file
    }

def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def get_system_info() -> Dict[str, Any]:
    """Get system information for optimization."""
    import psutil
    
    try:
        return {
            'cpu_count': cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'disk_free_gb': psutil.disk_usage('.').free / (1024**3),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
    except ImportError:
        return {
            'cpu_count': cpu_count(),
            'memory_gb': 'unknown',
            'disk_free_gb': 'unknown',
            'load_average': None
        }
