"""
PDF text extraction module
Handles different PDF libraries and extraction strategies
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles PDF text extraction using multiple libraries as fallbacks"""
    
    def __init__(self):
        self.available_methods = []
        
        if PDFPLUMBER_AVAILABLE:
            self.available_methods.append('pdfplumber')
        if PYMUPDF_AVAILABLE:
            self.available_methods.append('pymupdf')
        if PYPDF2_AVAILABLE:
            self.available_methods.append('pypdf2')
        
        if not self.available_methods:
            raise ImportError("No PDF processing library available. Install pdfplumber, PyMuPDF, or PyPDF2")
        
        logger.info(f"Available PDF processing methods: {', '.join(self.available_methods)}")
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF using available methods"""
        text = ""
        
        # Try each method until one works
        for method in self.available_methods:
            try:
                if method == 'pdfplumber':
                    text = self._extract_with_pdfplumber(pdf_path)
                elif method == 'pymupdf':
                    text = self._extract_with_pymupdf(pdf_path)
                elif method == 'pypdf2':
                    text = self._extract_with_pypdf2(pdf_path)
                
                if text.strip():
                    logger.debug(f"Successfully extracted text using {method}")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to extract with {method}: {str(e)}")
                continue
        
        return text
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> str:
        """Extract text using pdfplumber"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> str:
        """Extract text using PyMuPDF"""
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> str:
        """Extract text using PyPDF2"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
