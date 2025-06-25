# PDF Applicant Information Extractor

A high-performance Python tool for automatically extracting applicant information (ORCID IDs, Google Scholar profiles) from PDF files for PhD and postdoc position applications. Features advanced parallel processing, hyperlink extraction, and robust pattern matching.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Features

### Core Capabilities
- **🔗 Dual Extraction**: Extracts URLs from both visible text AND embedded hyperlinks
- **⚡ Parallel Processing**: Process hundreds of PDFs simultaneously with intelligent worker management
- **📄 Multi-Library Support**: Robust PDF processing with pdfplumber, PyMuPDF, and PyPDF2 fallbacks
- **🎯 Smart Pattern Matching**: Advanced regex patterns for various PDF formats and layouts
- **📊 Comprehensive Reporting**: Detailed statistics and progress tracking
- **🛡️ Production Ready**: Enterprise-grade error handling and recovery

### Advanced Features
- **Performance Profiles**: Optimized presets for different use cases (fast/accurate/balanced)
- **Hyperlink Detection**: Captures URLs that are completely invisible in text-only extraction
- **URL Validation**: Ensures extracted URLs are valid ORCID and Google Scholar profiles
- **Deduplication**: Intelligent removal of duplicate entries across text and hyperlink sources
- **Resource Management**: Automatic CPU and memory optimization

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Performance](#performance)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Installation

### Prerequisites
- Python 3.8 or higher
- At least 2GB RAM (4GB+ recommended for large batches)
- PDF files to process

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-extractor.git
cd pdf-extractor

# Install required packages
pip install -r requirements.txt
```

### PDF Library Installation

The tool supports multiple PDF libraries as fallbacks. Install at least one:

```bash
# Recommended: Install all for maximum compatibility
pip install pdfplumber PyMuPDF PyPDF2

# Or install individually:
pip install pdfplumber     # Best for accuracy
pip install PyMuPDF       # Fastest processing
pip install PyPDF2        # Lightweight fallback
```

## 🚀 Quick Start

### Basic Usage

```bash
# Process all PDFs in a directory
python main.py --input_dir ./pdfs --output_file results.csv
```

### Real-World Example

```bash
# Process 500 PhD application PDFs with 8 parallel workers
python main.py -i ./applications_2024/ -o phd_applicants.csv -w 8 -e process

# Output:
# 🔍 Found 500 PDF files to process
# ⚡ Using 8 workers with process executor
# 📊 Progress: 500/500 (100.0%) - Rate: 12.3 files/s - ETA: 0s
# ✅ Processing complete: 1,247 entries in 40.6s
# 💾 Saved 1,247 records to phd_applicants.csv
```

## 📖 Usage Examples

### Command Line Options

```bash
python main.py [OPTIONS]

Required:
  -i, --input_dir PATH      Directory containing PDF files

Optional:
  -o, --output_file FILE    Output CSV filename (default: applicants.csv)
  -w, --workers N           Number of parallel workers (default: auto-detect)
  -e, --executor TYPE       Executor type: 'process' or 'thread' (default: process)
  -p, --profile PROFILE     Performance profile: fast/accurate/balanced
  -l, --log_level LEVEL     Logging level: DEBUG/INFO/WARNING/ERROR
  -d, --dry_run            Show what would be processed without processing
```

### Performance-Optimized Examples

```bash
# Fast processing for large batches (prioritizes speed)
python main.py -i ./pdfs -o results.csv --profile fast

# Maximum accuracy for important applications
python main.py -i ./pdfs -o results.csv --profile accurate

# Balanced processing (recommended for most use cases)
python main.py -i ./pdfs -o results.csv --profile balanced

# Custom worker configuration
python main.py -i ./pdfs -o results.csv -w 12 -e process

# I/O-bound processing (network storage, many small files)
python main.py -i ./network_pdfs -o results.csv -e thread -w 16

# Debug problematic files
python main.py -i ./problem_pdfs -o debug.csv -l DEBUG -w 1
```

### Advanced Processing

```bash
# Process with custom performance settings
python main.py -i ./pdfs -o results.csv -w 8 --profile accurate -l INFO

# Preview what would be processed
python main.py -i ./pdfs --dry_run

# Monitor system resources during processing
python main.py -i ./pdfs -o results.csv -l DEBUG | tee processing.log
```


### Parallel Processing Models

#### Process Executor (Recommended)
- **Best for**: CPU-intensive PDF processing
- **Advantages**: Memory isolation, better resource utilization
- **Use when**: Processing complex PDFs, large batches

#### Thread Executor  
- **Best for**: I/O-bound operations
- **Advantages**: Lower overhead, shared memory
- **Use when**: Network storage, simple PDFs, small files

## 🔍 Advanced Features

### Hyperlink Extraction

Unlike text-only extraction tools, this extractor captures URLs that are embedded as clickable links:

**Example PDF Content:**
- **Visible text**: "John Smith, PhD Candidate"
- **Hidden hyperlink**: Text "John Smith" links to `https://orcid.org/0000-0002-1825-0097`
- **Another hidden link**: Text "Publications" links to Google Scholar profile

**Traditional tools miss these hidden links entirely!**

### URL Validation

The tool validates extracted URLs to ensure they're legitimate:

```python
# ORCID validation
✅ https://orcid.org/0000-0002-1825-0097  # Valid format and checksum
❌ https://orcid.org/0000-0000-0000-0000  # Invalid checksum
❌ orcid.org/invalid-format              # Invalid format

# Google Scholar validation  
✅ https://scholar.google.com/citations?user=Abc123DEF  # Valid user ID
❌ https://scholar.google.com/search?q=invalid         # Not a profile
```

### Smart Deduplication

Prevents duplicate entries from the same source:

```python
# Input: Same ORCID found in both text and hyperlinks
text_orcid = "https://orcid.org/0000-0002-1825-0097"
link_orcid = "https://orcid.org/0000-0002-1825-0097"

# Output: Single deduplicated entry
final_orcid = "https://orcid.org/0000-0002-1825-0097"
```



## 📈 Real-World Examples

### Academic Job Search

```bash
# Process 300 postdoc applications
python main.py -i ./postdoc_applications/ -o postdoc_results.csv -w 8

# Results: 
# - 300 files processed in 45 seconds
# - 287 successful extractions
# - 156 files had ORCID IDs
# - 203 files had Google Scholar profiles
# - 89 files had both ORCID and Scholar URLs
```

### Conference Paper Processing

```bash
# Extract author information from conference submissions
python main.py -i ./conference_papers/ -o author_info.csv --profile accurate

# Common findings:
# - Multi-author papers create multiple entries per file
# - Collaboration papers often have 5-10 authors
# - Some authors appear in multiple papers
```

### Grant Application Review

```bash
# Process grant applications with maximum accuracy
python main.py -i ./grant_applications/ -o grant_applicants.csv \
  --profile accurate -l INFO

# Typical results:
# - Higher accuracy but slower processing
# - Better detection of edge cases
# - Comprehensive validation of URLs
```




### Adding New Patterns

1. **Identify the pattern** in your PDF files
2. **Add regex pattern** to `config/patterns.py`
3. **Test with sample files**
4. **Submit pull request** with test cases

Example:
```python
# In config/patterns.py
PATTERNS = {
    'orcid': {
        'my_new_pattern': r'Your new regex pattern here',
        # ... existing patterns
    }
}
```


### Reporting Issues

When reporting issues, please include:

1. **System information** (OS, Python version, PDF library versions)
2. **Command used** (full command line)
3. **Error message** (complete error output)
4. **Sample files** (if possible, sanitized examples)
5. **Expected vs actual behavior**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Ready to extract thousands of applicant profiles in minutes? Get started now!**
