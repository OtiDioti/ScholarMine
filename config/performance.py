"""
Performance optimization configuration.
"""

# Base optimization configuration
OPTIMIZATION_CONFIG = {
    # Parallel processing
    'executor_type': 'process',
    'max_workers': None,  # Auto-detect
    'timeout_per_file': 60,
    'chunk_size': 1,
    
    # Memory management
    'memory_limit_mb': 512,
    'cleanup_interval': 50,  # Clean up every N files
    
    # Caching
    'enable_cache': False,
    'cache_size': 1000,
    'cache_ttl': 3600,
    
    # Early termination
    'early_termination': False,
    'early_stop_threshold': 3,
    
    # Page processing
    'page_parallel': False,
    'max_pages_to_process': 30,
    'priority_pages': [0, 1, 2],
    'min_text_per_page': 100,
    
    # Pattern matching
    'pattern_cache_size': 500,
    'validation_cache_size': 1000,
    
    # File processing
    'max_file_size_mb': 100,
    'skip_empty_files': True,
    'skip_corrupted_files': True,
    
    # Output
    'max_entries_per_file': 20,
    'deduplicate_results': True,
}

# Resource-based optimization thresholds
RESOURCE_THRESHOLDS = {
    'cpu_usage_high': 80,        # Reduce workers if CPU > 80%
    'memory_usage_high': 85,     # Reduce workers if memory > 85%
    'disk_usage_high': 90,       # Warn if disk > 90%
    'load_average_high': 2.0,    # Reduce workers if load > 2.0
}

# Adaptive optimization settings
ADAPTIVE_CONFIG = {
    'monitor_resources': True,
    'adjust_workers_dynamically': True,
    'enable_gc_optimization': True,
    'profile_performance': False,
}
