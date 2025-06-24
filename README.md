# PDF Applicant Information Extractor

A Python tool for automatically extracting applicant information (Name, ORCID, Google Scholar links) from PDF files for PhD and postdoc position applications with **parallel processing** for high performance.

## Features

- **🚀 Parallel Processing**: Process multiple PDFs simultaneously for faster extraction
- **📄 Format Flexibility**: Handles PDFs with varying formats and structures
- **🔧 Multiple PDF Libraries**: Support for pdfplumber, PyMuPDF, and PyPDF2
- **🎯 Robust Pattern Matching**: Advanced regex patterns for information extraction
- **📊 CSV Output**: Clean, structured data export
- **📝 Comprehensive Logging**: Detailed logging with parallel execution tracking
- **⚙️ Configurable**: Customizable patterns and processing parameters

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python main.py --input_dir ./pdfs --output_file applicants.csv
```

### Parallel Processing Options
```bash
# Use 8 parallel workers
python main.py -i ./pdfs -o applicants.csv --workers 8

# Use thread-based parallelism (better for I/O-bound processing)
python main.py -i ./pdfs -o applicants.csv --executor thread --workers 4

# Auto-detect optimal worker count (default)
python main.py -i ./pdfs -o applicants.csv
```

### Command Line Options
- `--input_dir` / `-i`: Directory containing PDF files (required)
- `--output_file` / `-o`: Output CSV filename (default: applicants.csv)
- `--workers` / `-w`: Number of parallel workers (default: auto-detect)
- `--executor` / `-e`: Executor type - 'process' or 'thread' (default: process)
- `--chunk_size` / `-c`: Files per worker chunk (default: 1)
- `--log_level` / `-l`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Performance Examples
```bash
# For CPU-intensive processing (complex PDFs)
python main.py -i ./pdfs -e process -w 8

# For I/O-bound processing (simple PDFs, network storage)
python main.py -i ./pdfs -e thread -w 16

# Debug mode with detailed logging
python main.py -i ./pdfs -l DEBUG -w 2
```

## Performance Benefits

### Processing Speed Comparison
- **Sequential**: ~2-5 seconds per PDF
- **Parallel (4 workers)**: ~4x faster for CPU-bound tasks
- **Parallel (8 workers)**: Up to ~8x faster with sufficient resources

### Scalability
- **Small datasets** (< 10 files): Minimal benefit
- **Medium datasets** (10-100 files): 3-5x speedup
- **Large datasets** (100+ files): Up to 8x speedup

## Output Format

The tool generates a CSV file with the following columns:
- `filename`: Original PDF filename
- `name`: Extracted applicant name
- `orcid`: ORCID identifier (full URL format)
- `google_scholar`: Google Scholar profile URL

## Architecture

### Parallel Processing Design
```
Main Process
├── Worker 1 → PDF A, B, C
├── Worker 2 → PDF D, E, F
├── Worker 3 → PDF G, H, I
└── Worker N → PDF X, Y, Z
```

### Executor Types
- **ProcessPoolExecutor**: Best for CPU-intensive PDF processing
- **ThreadPoolExecutor**: Best for I/O-bound operations or simple PDFs

## Customization

### Adding New Patterns
Edit `config/patterns.py` to add new regex patterns for different PDF formats:

```python
PATTERNS = {
    'name': {
        'your_pattern_name': r'your_regex_pattern',
        # ... existing patterns
    }
}
```

### Tuning Performance
```python
# In your code or config
optimal_workers = min(cpu_count() * 2, number_of_files)
```

### Supported PDF Libraries
The tool supports multiple PDF processing libraries as fallbacks:
- `pdfplumber` (recommended for accuracy)
- `PyMuPDF` (fastest option)
- `PyPDF2` (backup option)

## Troubleshooting

### Performance Issues
1. **Too many workers**: Reduce `--workers` if system becomes unresponsive
2. **Memory usage**: Use process executor for memory isolation
3. **I/O bottleneck**: Switch to thread executor for network storage

### Common Issues
1. **No text extracted**: Some PDFs are image-based. Consider OCR preprocessing.
2. **Incorrect information**: Adjust patterns in `config/patterns.py`
3. **Parallel processing errors**: Check log file for worker-specific errors

### Memory Management
- **Process executor**: Each worker has isolated memory (~50-100MB per worker)
- **Thread executor**: Shared memory, lower overhead but potential conflicts

### Logging in Parallel Mode
- Main log: `pdf_extractor.log`
- Process names included in log entries for debugging
- Use `-l DEBUG` to see detailed worker activity

## Examples

### Process 100 PDF applications with 8 workers
```bash
python main.py -i applications_2024/ -o results_2024.csv -w 8 -e process
```

### Quick processing with thread executor
```bash
python main.py -i ./small_batch/ -o quick_results.csv -e thread -w 4
```

### Debug a problematic batch
```bash
python main.py -i ./problem_pdfs/ -o debug.csv -l DEBUG -w 1
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new patterns
4. Test parallel processing with various workloads
5. Submit a pull request

## License
MIT License
