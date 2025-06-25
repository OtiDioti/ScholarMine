"""
Enhanced utility functions with optimization support.
"""

import logging
import sys
import os
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from multiprocessing import current_process, cpu_count
from dataclasses import dataclass

from extractor.pdf_processor import OptimizedPDFProcessor
from extractor.pattern_matcher import OptimizedPatternMatcher
from extractor.cache_manager import CacheManager

@dataclass
class ProcessingResult:
    """Result container for optimized processing."""
    success: bool
    data: Any
    error: Optional[str]
    filename: str
    processing_time: float
    stats: Dict[str, Any]

def setup_logging(level: str = 'INFO') -> None:
    """Setup optimized logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler],
        force=True
    )
    
    # Reduce noise from some libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fitz').setLevel(logging.WARNING)

def process_single_pdf_optimized(pdf_file: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimized single PDF processing function.
    
    Args:
        pdf_file: Path to the PDF file
        config: Configuration dictionary
        
    Returns:
        Dict with processing results and optimization metrics
    """
    logger = logging.getLogger(f"worker.{current_process().name}")
    start_time = time.time()
    
    result = {
        'success': False,
        'data': None,
        'error': None,
        'filename': pdf_file.name,
        'processing_time': 0,
        'stats': {
            'cache_hit': False,
            'early_terminated': False,
            'pages_processed': 0,
            'pages_skipped': 0,
            'total_pages': 0,
            'text_length': 0,
            'hyperlinks_found': 0,
            'file_size_mb': 0
        }
    }
    
    try:
        # File validation
        if not pdf_file.exists() or not pdf_file.is_file():
            raise FileNotFoundError(f"File not accessible: {pdf_file}")
        
        file_size = pdf_file.stat().st_size
        if file_size == 0:
            raise ValueError("File is empty")
        
        result['stats']['file_size_mb'] = file_size / (1024 * 1024)
        
        # Check cache if enabled
        cache_manager = None
        cache_key = None
        
        if config.get('enable_cache', False):
            cache_manager = CacheManager(config.get('cache_size', 1000))
            cache_key = f"pdf_{cache_manager.get_file_hash(pdf_file)}"
            
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                result.update(cached_result)
                result['stats']['cache_hit'] = True
                result['processing_time'] = time.time() - start_time
                logger.debug(f"🎯 Cache hit for {pdf_file.name}")
                return result
        
        # Initialize processors
        pdf_processor = OptimizedPDFProcessor(config)
        pattern_matcher = OptimizedPatternMatcher(config)
        
        # Extract text and hyperlinks with optimization
        extraction_result = asyncio.run(pdf_processor.extract_text_and_links_optimized(pdf_file))
        
        # Update stats from extraction
        result['stats'].update({
            'pages_processed': extraction_result.pages_processed,
            'pages_skipped': extraction_result.pages_skipped,
            'total_pages': extraction_result.total_pages,
            'text_length': len(extraction_result.text),
            'hyperlinks_found': len(extraction_result.hyperlinks),
            'early_terminated': extraction_result.early_terminated,
            'cache_hit': extraction_result.cache_hit
        })
        
        # Extract structured information
        entries, match_result = pattern_matcher.extract_info_streaming(
            extraction_result.text, 
            pdf_file.name, 
            extraction_result.hyperlinks
        )
        
        # Update stats from pattern matching
        result['stats'].update({
            'patterns_matched': match_result.patterns_matched,
            'match_early_terminated': match_result.early_terminated
        })
        
        result.update({
            'success': True,
            'data': entries
        })
        
        # Cache result if enabled
        if cache_manager and cache_key:
            cache_data = {
                'success': True,
                'data': entries,
                'stats': result['stats']
            }
            cache_manager.set(cache_key, cache_data, pdf_file)
        
        logger.debug(f"✅ {pdf_file.name}: {len(entries)} entries, "
                    f"Pages: {extraction_result.pages_processed}/{extraction_result.total_pages}, "
                    f"Early stop: {extraction_result.early_terminated}")
        
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
    Calculate optimal number of workers with enhanced logic.
    """
    cpu_cores = cpu_count()
    
    # Enhanced calculation based on workload characteristics
    if num_files <= 2:
        optimal = min(num_files, 2)
    elif num_files <= 10:
        optimal = min(num_files, cpu_cores)
    elif num_files <= 50:
        optimal = min(num_files, cpu_cores * 2)
    else:
        # For large batches, consider I/O limitations
        optimal = min(num_files, cpu_cores * 3, 20)  # Cap at 20
    
    # Apply user limit
    if max_workers:
        optimal = min(optimal, max_workers)
    
    return max(1, optimal)

def estimate_processing_time_optimized(num_files: int, workers: int, 
                                     config: Dict[str, Any]) -> Dict[str, float]:
    """
    Enhanced processing time estimation with optimization factors.
    """
    base_time_per_file = 2.0  # Base time per file
    
    # Adjust based on optimizations
    if config.get('enable_cache', False):
        base_time_per_file *= 0.7  # 30% speedup with cache
    
    if config.get('early_termination', False):
        base_time_per_file *= 0.8  # 20% speedup with early termination
    
    if config.get('page_parallel', False):
        base_time_per_file *= 0.9  # 10% speedup with page parallelization
    
    # Calculate estimates
    base_time = (num_files * base_time_per_file) / workers
    overhead = min(5, num_files * 0.05)  # Reduced overhead
    
    estimated_time = base_time + overhead
    min_time = estimated_time * 0.6  # Better best case
    max_time = estimated_time * 1.3  # Better worst case
    
    return {
        'estimated_time': estimated_time,
        'min_time': min_time,
        'max_time': max_time,
        'files_per_second': workers / base_time_per_file
    }

def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def get_system_resources() -> Dict[str, Any]:
    """Get system resource information for optimization."""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        return {
            'cpu_count': cpu_count(),
            'cpu_usage_percent': cpu_percent,
            'memory_total_gb': memory.total / (1024**3),
            'memory_available_gb': memory.available / (1024**3),
            'memory_usage_percent': memory.percent,
            'disk_free_gb': disk.free / (1024**3),
            'disk_usage_percent': disk.percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
    except ImportError:
        return {
            'cpu_count': cpu_count(),
            'cpu_usage_percent': 'unknown',
            'memory_total_gb': 'unknown',
            'memory_available_gb': 'unknown',
            'memory_usage_percent': 'unknown',
            'disk_free_gb': 'unknown',
            'disk_usage_percent': 'unknown',
            'load_average': None
        }

def optimize_workers_based_on_resources(num_files: int, default_workers: int) -> int:
    """Optimize worker count based on system resources."""
    try:
        resources = get_system_resources()
        
        # Reduce workers if system is under pressure
        if isinstance(resources['cpu_usage_percent'], (int, float)):
            if resources['cpu_usage_percent'] > 80:
                default_workers = max(1, default_workers // 2)
        
        if isinstance(resources['memory_usage_percent'], (int, float)):
            if resources['memory_usage_percent'] > 85:
                default_workers = max(1, default_workers // 2)
        
        return default_workers
    
    except Exception:
        return default_workers
