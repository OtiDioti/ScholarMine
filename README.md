# PDF Applicant Information Extractor

A Python tool for automatically extracting applicant information (Name, ORCID, Google Scholar links) from PDF files for PhD and postdoc position applications.

## Features

- Handles PDFs with varying formats and structures
- Multiple PDF processing libraries for maximum compatibility
- Robust pattern matching for information extraction
- CSV output for easy data management
- Comprehensive logging and error handling
- Configurable extraction patterns

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

### Command Line Options
- `--input_dir` / `-i`: Directory containing PDF files (required)
- `--output_file` / `-o`: Output CSV filename (default: applicants.csv)
- `--log_level` / `-l`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Example
```bash
python main.py -i /path/to/applications -o results.csv -l DEBUG
```

## Output Format

The tool generates a CSV file with the following columns:
- `filename`: Original PDF filename
- `name`: Extracted applicant name
- `orcid`: ORCID identifier (full URL format)
- `google_scholar`: Google Scholar profile URL

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

### Supported PDF Libraries
The tool supports multiple PDF processing libraries as fallbacks:
- `pdfplumber` (recommended)
- `PyMuPDF` (fast alternative)
- `PyPDF2` (backup option)

## Troubleshooting

### Common Issues
1. **No text extracted**: Some PDFs are image-based. Consider OCR preprocessing.
2. **Incorrect information**: Adjust patterns in `config/patterns.py`
3. **Performance issues**: Use `PyMuPDF` for faster processing of large files

### Logging
Check `pdf_extractor.log` for detailed processing information and errors.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new patterns
4. Submit a pull request
