"""
Example script demonstrating different parallel processing scenarios
"""

import argparse
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import pandas as pd

from extractor.utils import process_single_pdf, setup_logging, get_optimal_workers
from config.patterns import PARALLEL_CONFIG, PERFORMANCE_PROFILES

def benchmark_processing(pdf_files, max_workers=None):
    """Benchmark different processing approaches"""
    
    print(f"\n🔍 Benchmarking Processing Performance")
    print(f"Files to process: {len(pdf_files)}")
    
    results = {}
    
    # Sequential processing
    print("\n📊 Sequential Processing...")
    start_time = time.time()
    sequential_results = []
    for pdf_file in pdf_files[:5]:  # Test with first 5 files
        result = process_single_pdf(pdf_file)
        sequential_results.append(result)
    sequential_time = time.time() - start_time
    results['sequential'] = {
        'time': sequential_time,
        'files_per_second': len(sequential_results) / sequential_time,
        'results': sequential_results
    }
    
    # Parallel processing with different configurations
    for executor_type in ['thread', 'process']:
        for workers in [2, 4, 8]:
            if workers > len(pdf_files):
                continue
                
            print(f"\n⚡ Parallel Processing - {executor_type.title()} Executor ({workers} workers)...")
            
            executor_class = ThreadPoolExecutor if executor_type == 'thread' else ProcessPoolExecutor
            
            start_time = time.time()
            parallel_results = []
            
            with executor_class(max_workers=workers) as executor:
                future_to_file = {
                    executor.submit(process_single_pdf, pdf_file): pdf_file 
                    for pdf_file in pdf_files[:5]
                }
                
                for future in as_completed(future_to_file):
                    result = future.result()
                    parallel_results.append(result)
            
            parallel_time = time.time() - start_time
            
            results[f'{executor_type}_{workers}'] = {
                'time': parallel_time,
                'files_per_second': len(parallel_results) / parallel_time,
                'speedup': sequential_time / parallel_time,
                'results': parallel_results
            }
    
    # Print benchmark results
    print(f"\n📈 Benchmark Results:")
    print(f"{'Method':<20} {'Time (s)':<10} {'Files/s':<10} {'Speedup':<10}")
    print("-" * 50)
    
    for method, data in results.items():
        speedup = data.get('speedup', 1.0)
        print(f"{method:<20} {data['time']:<10.2f} {data['files_per_second']:<10.2f} {speedup:<10.2f}x")
    
    return results

def process_with_profile(pdf_files, profile_name='balanced'):
    """Process files using a predefined performance profile"""
    
    profile = PERFORMANCE_PROFILES.get(profile_name, PERFORMANCE_PROFILES['balanced'])
    
    print(f"\n🎯 Processing with '{profile_name}' profile")
    print(f"Max workers: {profile['max_workers']}")
    print(f"Timeout: {profile['timeout']}s")
    
    start_time = time.time()
    results = []
    failed_files = []
    
    with ProcessPoolExecutor(max_workers=profile['max_workers']) as executor:
        future_to_file = {
            executor.submit(process_single_pdf, pdf_file): pdf_file 
            for pdf_file in pdf_files
        }
        
        for future in as_completed(future_to_file, timeout=profile['timeout']):
            pdf_file = future_to_file[future]
            try:
                result = future.result()
                if result['success']:
                    results.append(result['data'])
                else:
                    failed_files.append(pdf_file.name)
            except Exception as e:
                print(f"❌ Error processing {pdf_file.name}: {str(e)}")
                failed_files.append(pdf_file.name)
    
    processing_time = time.time() - start_time
    
    print(f"\n✅ Profile Processing Complete:")
    print(f"Processed: {len(results)}/{len(pdf_files)} files")
    print(f"Time: {processing_time:.2f} seconds")
    print(f"Rate: {len(pdf_files)/processing_time:.2f} files/second")
    
    return results, failed_files

def adaptive_processing(pdf_files):
    """Adaptively choose processing parameters based on workload"""
    
    print(f"\n🧠 Adaptive Processing")
    
    num_files = len(pdf_files)
    optimal_workers = get_optimal_workers(num_files)
    
    # Choose executor type based on file count
    if num_files < 10:
        executor_type = 'thread'
        workers = min(4, optimal_workers)
    elif num_files < 50:
        executor_type = 'process'
        workers = optimal_workers
    else:
        executor_type = 'process'
        workers = min(optimal_workers, PARALLEL_CONFIG['max_absolute_workers'])
    
    print(f"Detected workload: {num_files} files")
    print(f"Chosen strategy: {executor_type} executor with {workers} workers")
    
    executor_class = ThreadPoolExecutor if executor_type == 'thread' else ProcessPoolExecutor
    
    start_time = time.time()
    results = []
    
    with executor_class(max_workers=workers) as executor:
        future_to_file = {
            executor.submit(process_single_pdf, pdf_file): pdf_file 
            for pdf_file in pdf_files
        }
        
        for i, future in enumerate(as_completed(future_to_file), 1):
            try:
                result = future.result()
                if result['success']:
                    results.append(result['data'])
                
                # Progress updates
                if i % 10 == 0 or i == num_files:
                    elapsed = time.time() - start_time
                    rate = i / elapsed
                    eta = (num_files - i) / rate if rate > 0 else 0
                    print(f"Progress: {i}/{num_files} ({i/num_files*100:.1f}%) - "
                          f"Rate: {rate:.1f} files/s - ETA: {eta:.0f}s")
                          
            except Exception as e:
                print(f"❌ Processing error: {str(e)}")
    
    processing_time = time.time() - start_time
    print(f"\n✅ Adaptive processing complete: {len(results)} files in {processing_time:.2f}s")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Batch processing examples')
    parser.add_argument('--input_dir', '-i', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--mode', '-m', type=str, default='adaptive',
                       choices=['benchmark', 'profile', 'adaptive'],
                       help='Processing mode')
    parser.add_argument('--profile', '-p', type=str, default='balanced',
                       choices=['fast', 'accurate', 'balanced'],
                       help='Performance profile (for profile mode)')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging('INFO')
    input_path = Path(args.input_dir)
    pdf_files = list(input_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {input_path}")
        return
    
    print(f"🔍 Found {len(pdf_files)} PDF files")
    
    # Run processing based on mode
    if args.mode == 'benchmark':
        benchmark_processing(pdf_files)
    elif args.mode == 'profile':
        results, failed = process_with_profile(pdf_files, args.profile)
        if results:
            df = pd.DataFrame(results)
            output_file = f"batch_results_{args.profile}.csv"
            df.to_csv(output_file, index=False)
            print(f"💾 Saved results to {output_file}")
    elif args.mode == 'adaptive':
        results = adaptive_processing(pdf_files)
        if results:
            df = pd.DataFrame(results)
            df.to_csv("adaptive_results.csv", index=False)
            print(f"💾 Saved results to adaptive_results.csv")

if __name__ == "__main__":
    main()
