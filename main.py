"""
PDF Applicant Information Extractor - Updated Version
Main execution script with enhanced parallel processing and error handling.
"""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import time
from typing import List, Dict, Any

from extractor.utils import setup_logging, process_single_pdf, get_optimal_workers
from config.patterns import PERFORMANCE_PROFILES

def process_files_parallel(pdf_files: List[Path], max_workers: int, executor_type: str) -> tuple:
    """
    Process PDF files in parallel with enhanced error handling.
    
    Returns:
        tuple: (results, failed_files, processing_stats)
    """
    executor_class = ProcessPoolExecutor if executor_type == 'process' else ThreadPoolExecutor
    logger = logging.getLogger(__name__)
    
    results = []
    failed_files = []
    processing_stats = {
        'total_files': len(pdf_files),
        'successful_files': 0,
        'total_entries': 0,
        'files_with_orcid': 0,
        'files_with_scholar': 0,
        'processing_time': 0
    }
    
    start_time = time.time()
    
    try:
        with executor_class(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_single_pdf, pdf_file): pdf_file 
                for pdf_file in pdf_files
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_file), 1):
                pdf_file = future_to_file[future]
                
                try:
                    result = future.result(timeout=60)  # 60 second timeout per file
                    
                    if result['success'] and result['data']:
                        file_results = result['data']
                        if isinstance(file_results, list):
                            results.extend(file_results)
                            processing_stats['total_entries'] += len(file_results)
                        else:
                            results.append(file_results)
                            processing_stats['total_entries'] += 1
                        
                        processing_stats['successful_files'] += 1
                        
                        # Track files with specific data
                        has_orcid = any(entry.get('orcid') for entry in (file_results if isinstance(file_results, list) else [file_results]))
                        has_scholar = any(entry.get('google_scholar') for entry in (file_results if isinstance(file_results, list) else [file_results]))
                        
                        if has_orcid:
                            processing_stats['files_with_orcid'] += 1
                        if has_scholar:
                            processing_stats['files_with_scholar'] += 1
                        
                        entry_count = len(file_results) if isinstance(file_results, list) else 1
                        logger.info(f"[{i}/{len(pdf_files)}] ✅ {pdf_file.name} - {entry_count} entries")
                        
                    else:
                        failed_files.append({
                            'filename': pdf_file.name,
                            'error': result.get('error', 'Unknown error')
                        })
                        logger.warning(f"[{i}/{len(pdf_files)}] ❌ {pdf_file.name}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    failed_files.append({
                        'filename': pdf_file.name,
                        'error': str(e)
                    })
                    logger.error(f"[{i}/{len(pdf_files)}] 💥 {pdf_file.name}: {str(e)}")
                
                # Progress updates
                if i % 10 == 0 or i == len(pdf_files):
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (len(pdf_files) - i) / rate if rate > 0 else 0
                    logger.info(f"📊 Progress: {i}/{len(pdf_files)} ({i/len(pdf_files)*100:.1f}%) - "
                              f"Rate: {rate:.1f} files/s - ETA: {eta:.0f}s")
    
    except KeyboardInterrupt:
        logger.info("❌ Processing interrupted by user")
        raise
    except Exception as e:
        logger.error(f"💥 Parallel processing failed: {str(e)}")
        raise
    
    processing_stats['processing_time'] = time.time() - start_time
    return results, failed_files, processing_stats

def print_summary(stats: Dict[str, Any], failed_files: List[Dict]) -> None:
    """Print processing summary statistics."""
    print(f"\n📋 Processing Summary:")
    print(f"{'='*50}")
    print(f"Total files processed: {stats['total_files']}")
    print(f"Successful: {stats['successful_files']}")
    print(f"Failed: {len(failed_files)}")
    print(f"Total entries extracted: {stats['total_entries']}")
    print(f"Files with ORCID: {stats['files_with_orcid']}")
    print(f"Files with Google Scholar: {stats['files_with_scholar']}")
    print(f"Processing time: {stats['processing_time']:.2f} seconds")
    
    if stats['total_files'] > 0:
        print(f"Average time per file: {stats['processing_time']/stats['total_files']:.2f} seconds")
        print(f"Files per second: {stats['total_files']/stats['processing_time']:.2f}")
        print(f"Average entries per file: {stats['total_entries']/stats['successful_files']:.2f}" if stats['successful_files'] > 0 else "Average entries per file: 0")
    
    if failed_files:
        print(f"\n❌ Failed Files ({len(failed_files)}):")
        for failed in failed_files[:10]:  # Show first 10 failures
            print(f"  - {failed['filename']}: {failed['error']}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")

def main():
    parser = argparse.ArgumentParser(
        description='Extract applicant information from PDF files with parallel processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -i ./pdfs -o results.csv
  python main.py -i ./pdfs -o results.csv -w 8 -e process
  python main.py -i ./pdfs -o results.csv --profile fast
        """
    )
    
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--output_file', '-o', type=str, default='applicants.csv',
                       help='Output CSV file name (default: applicants.csv)')
    parser.add_argument('--log_level', '-l', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--workers', '-w', type=int, default=None,
                       help='Number of parallel workers (default: auto-detect)')
    parser.add_argument('--executor', '-e', type=str, default='process',
                       choices=['process', 'thread'],
                       help='Executor type (default: process)')
    parser.add_argument('--profile', '-p', type=str, default=None,
                       choices=['fast', 'accurate', 'balanced'],
                       help='Performance profile (overrides other settings)')
    parser.add_argument('--dry_run', '-d', action='store_true',
                       help='Show what would be processed without actually processing')
    
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
    
    # Apply performance profile if specified
    if args.profile:
        profile = PERFORMANCE_PROFILES[args.profile]
        max_workers = profile['max_workers']
        logger.info(f"🎯 Using '{args.profile}' profile with {max_workers} workers")
    else:
        # Determine number of workers
        if args.workers is None:
            max_workers = get_optimal_workers(len(pdf_files))
        else:
            max_workers = min(args.workers, len(pdf_files))
    
    logger.info(f"🔍 Found {len(pdf_files)} PDF files to process")
    logger.info(f"⚡ Using {max_workers} workers with {args.executor} executor")
    
    if args.dry_run:
        print(f"🔍 Dry run - would process {len(pdf_files)} files:")
        for pdf_file in pdf_files[:10]:
            print(f"  - {pdf_file.name}")
        if len(pdf_files) > 10:
            print(f"  ... and {len(pdf_files) - 10} more")
        return
    
    # Process files
    try:
        results, failed_files, stats = process_files_parallel(
            pdf_files, max_workers, args.executor
        )
        
        # Save results
        if results:
            df = pd.DataFrame(results)
            df.to_csv(args.output_file, index=False)
            logger.info(f"💾 Saved {len(results)} records to {args.output_file}")
            
            # Print summary
            print_summary(stats, failed_files)
            
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
    main()
