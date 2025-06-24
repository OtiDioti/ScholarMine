"""
PDF Applicant Information Extractor
Main execution script for processing PDF files and extracting applicant data.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import time

from extractor.pdf_processor import PDFProcessor
from extractor.pattern_matcher import PatternMatcher
from extractor.utils import setup_logging, validate_files, process_single_pdf

def main():
    parser = argparse.ArgumentParser(description='Extract applicant info from PDF files')
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--output_file', '-o', type=str, default='applicants.csv',
                       help='Output CSV file name')
    parser.add_argument('--log_level', '-l', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--workers', '-w', type=int, default=None,
                       help='Number of parallel workers (default: auto-detect)')
    parser.add_argument('--executor', '-e', type=str, default='process',
                       choices=['process', 'thread'],
                       help='Executor type: process (CPU-bound) or thread (I/O-bound)')
    parser.add_argument('--chunk_size', '-c', type=int, default=1,
                       help='Number of files per worker chunk')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists() or not input_path.is_dir():
        logger.error(f"Input directory {input_path} does not exist or is not a directory")
        sys.exit(1)
    
    # Get PDF files
    pdf_files = list(input_path.glob('*.pdf'))
    if not pdf_files:
        logger.error(f"No PDF files found in {input_path}")
        sys.exit(1)
    
    # Determine number of workers
    if args.workers is None:
        max_workers = min(cpu_count(), len(pdf_files))
    else:
        max_workers = min(args.workers, len(pdf_files))
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    logger.info(f"Using {max_workers} workers with {args.executor} executor")
    
    # Choose executor type
    executor_class = ProcessPoolExecutor if args.executor == 'process' else ThreadPoolExecutor
    
    # Process files in parallel
    start_time = time.time()
    results = []
    failed_files = []
    
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
                    result = future.result()
                    if result['success']:
                        # Handle multiple entries per file
                        file_results = result['data']
                        if isinstance(file_results, list):
                            results.extend(file_results)
                            logger.info(f"[{i}/{len(pdf_files)}] Successfully processed {pdf_file.name} - {len(file_results)} entries found")
                        else:
                            results.append(file_results)
                            logger.info(f"[{i}/{len(pdf_files)}] Successfully processed {pdf_file.name} - 1 entry found")
                    else:
                        failed_files.append(pdf_file.name)
                        logger.warning(f"[{i}/{len(pdf_files)}] Failed to process {pdf_file.name}: {result['error']}")
                        
                except Exception as e:
                    failed_files.append(pdf_file.name)
                    logger.error(f"[{i}/{len(pdf_files)}] Exception processing {pdf_file.name}: {str(e)}")
                
                # Progress update
                if i % 10 == 0 or i == len(pdf_files):
                    logger.info(f"Progress: {i}/{len(pdf_files)} files processed")
    
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Parallel processing failed: {str(e)}")
        sys.exit(1)
    
    processing_time = time.time() - start_time
    
    # Create DataFrame and save results
    if results:
        df = pd.DataFrame(results)
        df.to_csv(args.output_file, index=False)
        logger.info(f"Saved {len(results)} records to {args.output_file}")
        
        # Print summary
        print(f"\nProcessing Summary:")
        print(f"Total files: {len(pdf_files)}")
        print(f"Successfully processed files: {len([r for r in results if r])}")
        print(f"Total entries extracted: {len(results)}")
        print(f"Failed: {len(failed_files)}")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Average time per file: {processing_time/len(pdf_files):.2f} seconds")
        print(f"Files per second: {len(pdf_files)/processing_time:.2f}")
        print(f"Average entries per file: {len(results)/len(pdf_files):.2f}")
        
        if failed_files:
            print(f"Failed files: {', '.join(failed_files)}")
    else:
        logger.error("No data extracted from any files")
        sys.exit(1)

if __name__ == "__main__":
    main()
