"""
PDF Applicant Information Extractor
Main execution script for processing PDF files and extracting applicant data.
"""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd

from extractor.pdf_processor import PDFProcessor
from extractor.pattern_matcher import PatternMatcher
from extractor.utils import setup_logging, validate_files

def main():
    parser = argparse.ArgumentParser(description='Extract applicant info from PDF files')
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--output_file', '-o', type=str, default='applicants.csv',
                       help='Output CSV file name')
    parser.add_argument('--log_level', '-l', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
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
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize processors
    pdf_processor = PDFProcessor()
    pattern_matcher = PatternMatcher()
    
    # Process files
    results = []
    failed_files = []
    
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing {pdf_file.name}")
            
            # Extract text from PDF
            text = pdf_processor.extract_text(pdf_file)
            if not text.strip():
                logger.warning(f"No text extracted from {pdf_file.name}")
                failed_files.append(pdf_file.name)
                continue
            
            # Extract information
            extracted_info = pattern_matcher.extract_info(text, pdf_file.name)
            results.append(extracted_info)
            
            logger.info(f"Successfully processed {pdf_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
            failed_files.append(pdf_file.name)
    
    # Create DataFrame and save results
    if results:
        df = pd.DataFrame(results)
        df.to_csv(args.output_file, index=False)
        logger.info(f"Saved {len(results)} records to {args.output_file}")
        
        # Print summary
        print(f"\nProcessing Summary:")
        print(f"Total files: {len(pdf_files)}")
        print(f"Successfully processed: {len(results)}")
        print(f"Failed: {len(failed_files)}")
        
        if failed_files:
            print(f"Failed files: {', '.join(failed_files)}")
    else:
        logger.error("No data extracted from any files")
        sys.exit(1)

if __name__ == "__main__":
    main()
