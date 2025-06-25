"""
Enhanced PDF text and hyperlink extraction with multiple library support.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Set
import re

# PDF library imports with fallbacks
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
    """Enhanced PDF processor with hyperlink extraction and multiple library support."""
    
    def __init__(self, preferred_method: str = None):
        self.available_methods = []
        
        # Build available methods list
        if PDFPLUMBER_AVAILABLE:
            self.available_methods.append('pdfplumber')
        if PYMUPDF_AVAILABLE:
            self.available_methods.append('pymupdf')
        if PYPDF2_AVAILABLE:
            self.available_methods.append('pypdf2')
        
        if not self.available_methods:
            raise ImportError(
                "No PDF processing library available. "
                "Install at least one: pdfplumber, PyMuPDF, or PyPDF2"
            )
        
        # Set preferred method order
        if preferred_method and preferred_method in self.available_methods:
            self.available_methods.remove(preferred_method)
            self.available_methods.insert(0, preferred_method)
        
        logger.debug(f"Available PDF methods: {', '.join(self.available_methods)}")
    
    def extract_text_and_links(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """
        Extract both text and hyperlinks from PDF using the best available method.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (text_content, list_of_hyperlink_urls)
        """
        text = ""
        hyperlinks = []
        last_error = None
        
        for method in self.available_methods:
            try:
                if method == 'pdfplumber':
                    text, hyperlinks = self._extract_with_pdfplumber(pdf_path)
                elif method == 'pymupdf':
                    text, hyperlinks = self._extract_with_pymupdf(pdf_path)
                elif method == 'pypdf2':
                    text, hyperlinks = self._extract_with_pypdf2(pdf_path)
                
                if text.strip() or hyperlinks:
                    logger.debug(f"✅ Extracted content using {method}: "
                               f"{len(text)} chars, {len(hyperlinks)} links")
                    break
                    
            except Exception as e:
                last_error = e
                logger.debug(f"❌ Failed to extract with {method}: {str(e)}")
                continue
        else:
            # If we get here, all methods failed
            if last_error:
                raise last_error
            else:
                raise RuntimeError("No extraction method succeeded")
        
        # Clean and deduplicate hyperlinks
        hyperlinks = self._clean_hyperlinks(hyperlinks)
        
        return text, hyperlinks
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text only (backward compatibility)."""
        text, _ = self.extract_text_and_links(pdf_path)
        return text
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using pdfplumber with enhanced hyperlink detection."""
        text = ""
        hyperlinks = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Extract hyperlinks - try multiple methods
                    page_links = []
                    
                    # Method 1: page.hyperlinks (if available)
                    if hasattr(page, 'hyperlinks'):
                        for link in page.hyperlinks:
                            if isinstance(link, dict) and 'uri' in link:
                                page_links.append(link['uri'])
                    
                    # Method 2: annotations
                    if hasattr(page, 'annots'):
                        for annot in page.annots:
                            if isinstance(annot, dict):
                                if annot.get('subtype') == 'Link' and 'uri' in annot:
                                    page_links.append(annot['uri'])
                                elif 'A' in annot and isinstance(annot['A'], dict):
                                    action = annot['A']
                                    if action.get('S') == 'URI' and 'URI' in action:
                                        page_links.append(action['URI'])
                    
                    hyperlinks.extend(page_links)
                    
                except Exception as e:
                    logger.debug(f"Error processing page {page_num + 1}: {str(e)}")
                    continue
        
        return text, hyperlinks
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using PyMuPDF with comprehensive hyperlink extraction."""
        text = ""
        hyperlinks = []
        
        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    # Extract text
                    page_text = page.get_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Extract hyperlinks
                    links = page.get_links()
                    for link in links:
                        if isinstance(link, dict):
                            # Try different possible keys
                            for uri_key in ['uri', 'url', 'dest']:
                                if uri_key in link and link[uri_key]:
                                    hyperlinks.append(str(link[uri_key]))
                                    break
                
                except Exception as e:
                    logger.debug(f"Error processing page {page_num + 1}: {str(e)}")
                    continue
                    
        finally:
            doc.close()
        
        return text, hyperlinks
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using PyPDF2 with limited hyperlink support."""
        text = ""
        hyperlinks = []
        
        with open(pdf_path, 'rb') as file:
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        # Extract text
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                        
                        # Extract hyperlinks from annotations
                        if '/Annots' in page:
                            annotations = page['/Annots']
                            if annotations:
                                for annot_ref in annotations:
                                    try:
                                        annot = annot_ref.get_object()
                                        if annot.get('/Subtype') == '/Link':
                                            action = annot.get('/A')
                                            if action and action.get('/S') == '/URI':
                                                uri = action.get('/URI')
                                                if uri:
                                                    hyperlinks.append(str(uri))
                                    except Exception as e:
                                        logger.debug(f"Error extracting annotation: {str(e)}")
                                        continue
                    
                    except Exception as e:
                        logger.debug(f"Error processing page {page_num + 1}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Error reading PDF with PyPDF2: {str(e)}")
                raise
        
        return text, hyperlinks
    
    def _clean_hyperlinks(self, hyperlinks: List[str]) -> List[str]:
        """Clean and deduplicate hyperlinks."""
        if not hyperlinks:
            return []
        
        cleaned = set()
        for link in hyperlinks:
            if not link or not isinstance(link, str):
                continue
            
            # Clean the link
            link = link.strip()
            if not link:
                continue
            
            # Remove common prefixes/suffixes that might be added during extraction
            link = re.sub(r'^["\'\s]+|["\'\s]+$', '', link)
            
            # Only keep valid URLs
            if self._is_valid_url(link):
                cleaned.add(link)
        
        return sorted(list(cleaned))
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and relevant."""
        if not url or len(url) < 10:
            return False
        
        # Must start with http/https or be a recognized domain
        if not (url.startswith(('http://', 'https://')) or 
                any(domain in url.lower() for domain in ['orcid.org', 'scholar.google'])):
            return False
        
        return True
    
    def get_extraction_stats(self, pdf_path: Path) -> Dict[str, int]:
        """Get detailed extraction statistics."""
        text, hyperlinks = self.extract_text_and_links(pdf_path)
        
        stats = {
            'text_length': len(text),
            'total_hyperlinks': len(hyperlinks),
            'orcid_links': 0,
            'scholar_links': 0,
            'other_links': 0
        }
        
        for link in hyperlinks:
            link_lower = link.lower()
            if 'orcid.org' in link_lower:
                stats['orcid_links'] += 1
            elif 'scholar.google' in link_lower:
                stats['scholar_links'] += 1
            else:
                stats['other_links'] += 1
        
        return stats
