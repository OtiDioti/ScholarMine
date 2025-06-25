"""
Optimized PDF Applicant Information Extractor
Main execution script with advanced parallel processing and optimization.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import signal

from extractor.utils import setup_logging, process_single_pdf_optimized, get_optimal_workers
from extractor.cache_manager import CacheManager
from config.patterns import PERFORMANCE_PROFILES
from config.performance import OPTIMIZATION_CONFIG

class PDFExtractorOptimized:
    """Optimized PDF extractor with advanced parallel processing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_manager = CacheManager(config.get('cache_size', 1000))
        self.logger = logging.getLogger(__name__)
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def process_files_optimized(self, pdf_files: List[Path]) -> tuple:
        """
        Process PDF files with optimized parallel processing and early termination.
        
        Returns:
            tuple: (results, failed_files, processing_stats)
        """
        max_workers = self.config.get('max_workers', get_optimal_workers(len(pdf_files)))
        executor_type = self.config.get('executor_type', 'process')
        
        results = []
        failed_files = []
        processing_stats = {
            'total_files': len(pdf_files),
            'successful_files': 0,
            'total_entries': 0,
            'files_with_orcid': 0,
            'files_with_scholar': 0,
            'processing_time': 0,
            'cache_hits': 0,
            'early_terminations': 0,
            'pages_processed': 0,
            'pages_skipped': 0
        }
        
        start_time = time.time()
        
        # Group files by size for optimal processing
        file_groups = self._group_files_by_size(pdf_files)
        
        try:
            # Process files in groups with different strategies
            for group_name, group_files in file_groups.items():
                if self.shutdown_requested:
                    self.logger.info("🛑 Shutdown requested, stopping processing")
                    break
                
                self.logger.info(f"📂 Processing {group_name} group: {len(group_files)} files")
                
                group_results, group_failed, group_stats = await self._process_file_group(
                    group_files, max_workers, executor_type
                )
                
                results.extend(group_results)
                failed_files.extend(group_failed)
                
                # Update stats
                for key in ['successful_files', 'total_entries', 'files_with_orcid', 
                           'files_with_scholar', 'cache_hits', 'early_terminations',
                           'pages_processed', 'pages_skipped']:
                    processing_stats[key] += group_stats.get(key, 0)
                
                # Memory cleanup between groups
                await self._cleanup_memory()
        
        except Exception as e:
            self.logger.error(f"💥 Processing failed: {str(e)}")
            raise
        
        processing_stats['processing_time'] = time.time() - start_time
        
        # Cache statistics
        cache_stats = self.cache_manager.get_stats()
        processing_stats.update(cache_stats)
        
        return results, failed_files, processing_stats
    
    def _group_files_by_size(self, pdf_files: List[Path]) -> Dict[str, List[Path]]:
        """Group files by size for optimal processing strategies."""
        small_files = []  # < 1MB
        medium_files = []  # 1MB - 10MB
        large_files = []  # > 10MB
        
        for pdf_file in pdf_files:
            try:
                size_mb = pdf_file.stat().st_size / (1024 * 1024)
                if size_mb < 1:
                    small_files.append(pdf_file)
                elif size_mb < 10:
                    medium_files.append(pdf_file)
                else:
                    large_files.append(pdf_file)
            except Exception:
                medium_files.append(pdf_file)  # Default to medium
        
        return {
            'small': small_files,
            'medium': medium_files,
            'large': large_files
        }
    
    async def _process_file_group(self, files: List[Path], max_workers: int, 
                                 executor_type: str) -> tuple:
        """Process a group of files with appropriate strategy."""
        if not files:
            return [], [], {}
        
        # Adjust workers based on file size group
        if len(files) <= 5:  # Small group
            workers = min(max_workers, len(files))
        else:
            workers = max_workers
        
        executor_class = ProcessPoolExecutor if executor_type == 'process' else ThreadPoolExecutor
        
        results = []
        failed_files = []
        stats = {
            'successful_files': 0,
            'total_entries': 0,
            'files_with_orcid': 0,
            'files_with_scholar': 0,
            'cache_hits': 0,
            'early_terminations': 0,
            'pages_processed': 0,
            'pages_skipped': 0
        }
        
        with executor_class(max_workers=workers) as executor:
            # Submit tasks with configuration
            future_to_file = {
                executor.submit(process_single_pdf_optimized, pdf_file, self.config): pdf_file
                for pdf_file in files
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_file), 1):
                if self.shutdown_requested:
                    break
                
                pdf_file = future_to_file[future]
                
                try:
                    result = future.result(timeout=self.config.get('timeout_per_file', 60))
                    
                    if result['success'] and result['data']:
                        file_results = result['data']
                        if isinstance(file_results, list):
                            results.extend(file_results)
                            stats['total_entries'] += len(file_results)
                        else:
                            results.append(file_results)
                            stats['total_entries'] += 1
                        
                        stats['successful_files'] += 1
                        
                        # Update detailed stats
                        file_stats = result.get('stats', {})
                        for key in ['cache_hits', 'early_terminations', 'pages_processed', 'pages_skipped']:
                            stats[key] += file_stats.get(key, 0)
                        
                        # Track content types
                        has_orcid = any(entry.get('orcid') for entry in 
                                      (file_results if isinstance(file_results, list) else [file_results]))
                        has_scholar = any(entry.get('google_scholar') for entry in 
                                        (file_results if isinstance(file_results, list) else [file_results]))
                        
                        if has_orcid:
                            stats['files_with_orcid'] += 1
                        if has_scholar:
                            stats['files_with_scholar'] += 1
                        
                        entry_count = len(file_results) if isinstance(file_results, list) else 1
                        processing_info = f"📄 {entry_count} entries"
                        
                        if file_stats.get('early_terminated'):
                            processing_info += " (early stop)"
                        if file_stats.get('cache_hit'):
                            processing_info += " (cached)"
                        
                        self.logger.info(f"[{i}/{len(files)}] ✅ {pdf_file.name} - {processing_info}")
                        
                    else:
                        failed_files.append({
                            'filename': pdf_file.name,
                            'error': result.get('error', 'Unknown error')
                        })
                        self.logger.warning(f"[{i}/{len(files)}] ❌ {pdf_file.name}: {result.get('error')}")
                
                except TimeoutError:
                    failed_files.append({
                        'filename': pdf_file.name,
                        'error': 'Processing timeout'
                    })
                    self.logger.error(f"[{i}/{len(files)}] ⏰ {pdf_file.name}: Processing timeout")
                
                except Exception as e:
                    failed_files.append({
                        'filename': pdf_file.name,
                        'error': str(e)
                    })
                    self.logger.error(f"[{i}/{len(files)}] 💥 {pdf_file.name}: {str(e)}")
                
                # Progress updates
                if i % 10 == 0 or i == len(files):
                    elapsed = time.time() - time.time()  # This should be properly tracked
                    self.logger.info(f"📊 Group progress: {i}/{len(files)} ({i/len(files)*100:.1f}%)")
        
        return results, failed_files, stats
    
    async def _cleanup_memory(self):
        """Clean up memory between processing groups."""
        import gc
        self.cache_manager.cleanup_expired()
        gc.collect()
        await asyncio.sleep(0.1)  # Allow other tasks to run

def print_enhanced_summary(stats: Dict[str, Any], failed_files: List[Dict]) -> None:
    """Print enhanced processing summary with optimization metrics."""
    print(f"\n📋 Processing Summary:")
    print(f"{'='*60}")
    print(f"Total files processed: {stats['total_files']}")
    print(f"Successful: {stats['successful_files']}")
    print(f"Failed: {len(failed_files)}")
    print(f"Total entries extracted: {stats['total_entries']}")
    print(f"Files with ORCID: {stats['files_with_orcid']}")
    print(f"Files with Google Scholar: {stats['files_with_scholar']}")
    print(f"Processing time: {stats['processing_time']:.2f} seconds")
    
    print(f"\n🚀 Optimization Metrics:")
    print(f"Cache hits: {stats.get('cache_hits', 0)}")
    print(f"Early terminations: {stats.get('early_terminations', 0)}")
    print(f"Pages processed: {stats.get('pages_processed', 0)}")
    print(f"Pages skipped: {stats.get('pages_skipped', 0)}")
    
    if stats['total_files'] > 0:
        print(f"Average time per file: {stats['processing_time']/stats['total_files']:.2f} seconds")
        print(f"Files per second: {stats['total_files']/stats['processing_time']:.2f}")
        
        if stats['successful_files'] > 0:
            print(f"Average entries per file: {stats['total_entries']/stats['successful_files']:.2f}")
        
        if stats.get('pages_processed', 0) > 0:
            skip_rate = stats.get('pages_skipped', 0) / (stats['pages_processed'] + stats.get('pages_skipped', 0)) * 100
            print(f"Page skip rate: {skip_rate:.1f}%")
    
    if failed_files:
        print(f"\n❌ Failed Files ({len(failed_files)}):")
        for failed in failed_files[:10]:
            print(f"  - {failed['filename']}: {failed['error']}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")

async def main():
    parser = argparse.ArgumentParser(
        description='Optimized PDF Applicant Information Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -i ./pdfs -o results.csv
  python main.py -i ./pdfs -o results.csv --profile fast
  python main.py -i ./pdfs -o results.csv --enable-cache --early-stop
        """
    )
    
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--output_file', '-o', type=str, default='applicants.csv',
                       help='Output CSV file name (default: applicants.csv)')
    parser.add_argument('--log_level', '-l', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--profile', '-p', type=str, default='balanced',
                       choices=['fast', 'accurate', 'balanced'],
                       help='Performance profile (default: balanced)')
    parser.add_argument('--enable-cache', action='store_true',
                       help='Enable result caching')
    parser.add_argument('--early-stop', action='store_true',
                       help='Enable early termination when sufficient data found')
    parser.add_argument('--page-parallel', action='store_true',
                       help='Enable page-level parallelization')
    parser.add_argument('--workers', '-w', type=int, default=None,
                       help='Number of parallel workers (default: auto-detect)')
    parser.add_argument('--dry_run', '-d', action='store_true',
                       help='Show what would be processed without actually processing')
    parser.add_argument('--benchmark', '-b', action='store_true',
                       help='Run benchmark mode with detailed timing')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists() or not input_path.is_dir():
        logger.error(f"❌ Input directory {input_path} does not exist or is not a directory")
        sys.exit(1)
    
    # Get PDF files
    pdf_files = list(input_path.glob('*.pdf'))
    if not pdf_files:
        logger.error(f"❌ No PDF files found in {input_path}")
        sys.exit(1)
    
    # Build configuration
    profile = PERFORMANCE_PROFILES[args.profile]
    config = {
        **OPTIMIZATION_CONFIG,
        **profile,
        'enable_cache': args.enable_cache,
        'early_termination': args.early_stop,
        'page_parallel': args.page_parallel,
        'benchmark_mode': args.benchmark,
    }
    
    if args.workers:
        config['max_workers'] = args.workers
    
    logger.info(f"🔍 Found {len(pdf_files)} PDF files to process")
    logger.info(f"🎯 Using '{args.profile}' profile")
    logger.info(f"⚡ Optimizations: Cache={args.enable_cache}, EarlyStop={args.early_stop}, PageParallel={args.page_parallel}")
    
    if args.dry_run:
        print(f"🔍 Dry run - would process {len(pdf_files)} files:")
        for pdf_file in pdf_files[:10]:
            print(f"  - {pdf_file.name}")
        if len(pdf_files) > 10:
            print(f"  ... and {len(pdf_files) - 10} more")
        return
    
    # Initialize extractor
    extractor = PDFExtractorOptimized(config)
    
    # Process files
    try:
        results, failed_files, stats = await extractor.process_files_optimized(pdf_files)
        
        # Save results
        if results:
            df = pd.DataFrame(results)
            df.to_csv(args.output_file, index=False)
            logger.info(f"💾 Saved {len(results)} records to {args.output_file}")
            
            # Print summary
            print_enhanced_summary(stats, failed_files)
            
        else:
            logger.error("❌ No data extracted from any files")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Processing failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
