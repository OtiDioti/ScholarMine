"""
Optimized PDF processor with page-level parallelization and streaming processing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Set, Generator
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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

@dataclass
class PageContent:
    """Container for page content and metadata."""
    page_num: int
    text: str
    hyperlinks: List[str]
    processing_time: float
    size_bytes: int

@dataclass
class ExtractionResult:
    """Container for extraction results with optimization metrics."""
    text: str
    hyperlinks: List[str]
    pages_processed: int
    pages_skipped: int
    total_pages: int
    early_terminated: bool
    cache_hit: bool
    processing_time: float

class OptimizedPDFProcessor:
    """Optimized PDF processor with advanced extraction strategies."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.available_methods = self._get_available_methods()
        self.preferred_method = config.get('pdf_library_preference', ['pymupdf', 'pdfplumber', 'pypdf2'])[0]
        
        # Optimization settings
        self.enable_page_parallel = config.get('page_parallel', False)
        self.enable_early_termination = config.get('early_termination', False)
        self.max_pages_to_process = config.get('max_pages_to_process', 50)
        self.priority_pages = config.get('priority_pages', [0, 1, 2])  # First 3 pages
        
        # Performance thresholds
        self.min_text_per_page = config.get('min_text_per_page', 100)
        self.early_stop_threshold = config.get('early_stop_threshold', 3)  # Stop after finding 3 items
        
        logger.debug(f"📱 PDF Processor initialized with method: {self.preferred_method}")
        logger.debug(f"🔧 Optimizations: PageParallel={self.enable_page_parallel}, EarlyStop={self.enable_early_termination}")
    
    def _get_available_methods(self) -> List[str]:
        """Get available PDF processing methods."""
        methods = []
        if PYMUPDF_AVAILABLE:
            methods.append('pymupdf')
        if PDFPLUMBER_AVAILABLE:
            methods.append('pdfplumber')
        if PYPDF2_AVAILABLE:
            methods.append('pypdf2')
        
        if not methods:
            raise ImportError("No PDF processing library available")
        
        return methods
    
    async def extract_text_and_links_optimized(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract text and hyperlinks with optimization strategies.
        """
        start_time = time.time()
        
        try:
            # Try different extraction strategies based on file characteristics
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb < 1:  # Small files - simple extraction
                return await self._extract_simple(pdf_path, start_time)
            elif file_size_mb > 10:  # Large files - streaming extraction
                return await self._extract_streaming(pdf_path, start_time)
            else:  # Medium files - standard optimized extraction
                return await self._extract_optimized(pdf_path, start_time)
                
        except Exception as e:
            logger.error(f"❌ Failed to extract from {pdf_path.name}: {str(e)}")
            return ExtractionResult(
                text="", hyperlinks=[], pages_processed=0, pages_skipped=0,
                total_pages=0, early_terminated=False, cache_hit=False,
                processing_time=time.time() - start_time
            )
    
    async def _extract_simple(self, pdf_path: Path, start_time: float) -> ExtractionResult:
        """Simple extraction for small files."""
        text, hyperlinks = self._extract_with_method(pdf_path, self.preferred_method)
        
        return ExtractionResult(
            text=text,
            hyperlinks=hyperlinks,
            pages_processed=1,  # Simplified counting
            pages_skipped=0,
            total_pages=1,
            early_terminated=False,
            cache_hit=False,
            processing_time=time.time() - start_time
        )
    
    async def _extract_streaming(self, pdf_path: Path, start_time: float) -> ExtractionResult:
        """Streaming extraction for large files with early termination."""
        total_text = ""
        all_hyperlinks = []
        pages_processed = 0
        pages_skipped = 0
        total_pages = 0
        early_terminated = False
        found_items = 0
        
        try:
            # Get page count first
            with self._open_pdf(pdf_path) as pdf:
                total_pages = self._get_page_count(pdf)
                
                # Process priority pages first
                priority_pages = [p for p in self.priority_pages if p < total_pages]
                remaining_pages = [p for p in range(total_pages) if p not in priority_pages]
                
                # Process pages in order of priority
                for page_num in priority_pages + remaining_pages:
                    if self.enable_early_termination and found_items >= self.early_stop_threshold:
                        early_terminated = True
                        pages_skipped = total_pages - pages_processed
                        break
                    
                    if pages_processed >= self.max_pages_to_process:
                        pages_skipped = total_pages - pages_processed
                        break
                    
                    try:
                        page_content = await self._extract_page_content(pdf, page_num)
                        
                        if len(page_content.text) < self.min_text_per_page:
                            pages_skipped += 1
                            continue
                        
                        total_text += page_content.text + "\n"
                        all_hyperlinks.extend(page_content.hyperlinks)
                        pages_processed += 1
                        
                        # Quick check for early termination
                        if self.enable_early_termination:
                            found_items += self._count_potential_matches(page_content.text, page_content.hyperlinks)
                        
                    except Exception as e:
                        logger.debug(f"❌ Error processing page {page_num}: {str(e)}")
                        pages_skipped += 1
                        continue
        
        except Exception as e:
            logger.error(f"❌ Streaming extraction failed for {pdf_path.name}: {str(e)}")
        
        return ExtractionResult(
            text=total_text,
            hyperlinks=self._clean_hyperlinks(all_hyperlinks),
            pages_processed=pages_processed,
            pages_skipped=pages_skipped,
            total_pages=total_pages,
            early_terminated=early_terminated,
            cache_hit=False,
            processing_time=time.time() - start_time
        )
    
    async def _extract_optimized(self, pdf_path: Path, start_time: float) -> ExtractionResult:
        """Optimized extraction with page-level parallelization."""
        if self.enable_page_parallel:
            return await self._extract_parallel_pages(pdf_path, start_time)
        else:
            return await self._extract_streaming(pdf_path, start_time)
    
    async def _extract_parallel_pages(self, pdf_path: Path, start_time: float) -> ExtractionResult:
        """Extract pages in parallel for medium-sized files."""
        total_text = ""
        all_hyperlinks = []
        pages_processed = 0
        pages_skipped = 0
        total_pages = 0
        early_terminated = False
        
        try:
            # Get page count
            with self._open_pdf(pdf_path) as pdf:
                total_pages = self._get_page_count(pdf)
                
                # Limit concurrent page processing
                max_page_workers = min(4, total_pages)
                
                # Process priority pages first
                priority_pages = [p for p in self.priority_pages if p < total_pages]
                
                # Process priority pages sequentially for better control
                for page_num in priority_pages:
                    try:
                        page_content = await self._extract_page_content_standalone(pdf_path, page_num)
                        
                        if len(page_content.text) >= self.min_text_per_page:
                            total_text += page_content.text + "\n"
                            all_hyperlinks.extend(page_content.hyperlinks)
                            pages_processed += 1
                            
                            # Check for early termination
                            if self.enable_early_termination:
                                found_items = self._count_potential_matches(page_content.text, page_content.hyperlinks)
                                if found_items >= self.early_stop_threshold:
                                    early_terminated = True
                                    pages_skipped = total_pages - pages_processed
                                    break
                        else:
                            pages_skipped += 1
                    
                    except Exception as e:
                        logger.debug(f"❌ Error processing priority page {page_num}: {str(e)}")
                        pages_skipped += 1
                
                # Process remaining pages in parallel if needed
                if not early_terminated and pages_processed < self.max_pages_to_process:
                    remaining_pages = [p for p in range(total_pages) 
                                     if p not in priority_pages and pages_processed < self.max_pages_to_process]
                    
                    if remaining_pages:
                        parallel_results = await self._process_pages_parallel(
                            pdf_path, remaining_pages[:self.max_pages_to_process - pages_processed], 
                            max_page_workers
                        )
                        
                        for page_content in parallel_results:
                            if page_content and len(page_content.text) >= self.min_text_per_page:
                                total_text += page_content.text + "\n"
                                all_hyperlinks.extend(page_content.hyperlinks)
                                pages_processed += 1
                            else:
                                pages_skipped += 1
        
        except Exception as e:
            logger.error(f"❌ Parallel extraction failed for {pdf_path.name}: {str(e)}")
        
        return ExtractionResult(
            text=total_text,
            hyperlinks=self._clean_hyperlinks(all_hyperlinks),
            pages_processed=pages_processed,
            pages_skipped=pages_skipped,
            total_pages=total_pages,
            early_terminated=early_terminated,
            cache_hit=False,
            processing_time=time.time() - start_time
        )
    
    async def _process_pages_parallel(self, pdf_path: Path, page_numbers: List[int], 
                                    max_workers: int) -> List[Optional[PageContent]]:
        """Process multiple pages in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_page = {
                executor.submit(self._extract_page_content_standalone_sync, pdf_path, page_num): page_num
                for page_num in page_numbers
            }
            
            for future in as_completed(future_to_page):
                try:
                    page_content = future.result(timeout=30)
                    results.append(page_content)
                except Exception as e:
                    page_num = future_to_page[future]
                    logger.debug(f"❌ Failed to process page {page_num}: {str(e)}")
                    results.append(None)
        
        # Sort results by page number to maintain order
        results.sort(key=lambda x: x.page_num if x else float('inf'))
        return results
    
    def _extract_page_content_standalone_sync(self, pdf_path: Path, page_num: int) -> Optional[PageContent]:
        """Synchronous wrapper for parallel page processing."""
        try:
            with self._open_pdf(pdf_path) as pdf:
                return self._extract_single_page_sync(pdf, page_num)
        except Exception as e:
            logger.debug(f"❌ Error extracting page {page_num}: {str(e)}")
            return None
    
    async def _extract_page_content_standalone(self, pdf_path: Path, page_num: int) -> Optional[PageContent]:
        """Extract content from a single page (standalone)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_page_content_standalone_sync, pdf_path, page_num)
    
    async def _extract_page_content(self, pdf, page_num: int) -> PageContent:
        """Extract content from a single page."""
        start_time = time.time()
        
        try:
            page_text, page_links = self._extract_single_page(pdf, page_num)
            
            return PageContent(
                page_num=page_num,
                text=page_text,
                hyperlinks=page_links,
                processing_time=time.time() - start_time,
                size_bytes=len(page_text.encode('utf-8'))
            )
        
        except Exception as e:
            logger.debug(f"❌ Error extracting page {page_num}: {str(e)}")
            return PageContent(
                page_num=page_num,
                text="",
                hyperlinks=[],
                processing_time=time.time() - start_time,
                size_bytes=0
            )
    
    def _extract_with_method(self, pdf_path: Path, method: str) -> Tuple[str, List[str]]:
        """Extract using specified method."""
        if method == 'pymupdf':
            return self._extract_with_pymupdf(pdf_path)
        elif method == 'pdfplumber':
            return self._extract_with_pdfplumber(pdf_path)
        elif method == 'pypdf2':
            return self._extract_with_pypdf2(pdf_path)
        else:
            raise ValueError(f"Unknown extraction method: {method}")
    
    def _open_pdf(self, pdf_path: Path):
        """Open PDF with preferred method."""
        if self.preferred_method == 'pymupdf':
            return fitz.open(pdf_path)
        elif self.preferred_method == 'pdfplumber':
            return pdfplumber.open(pdf_path)
        else:
            return open(pdf_path, 'rb')
    
    def _get_page_count(self, pdf) -> int:
        """Get page count from PDF object."""
        if self.preferred_method == 'pymupdf':
            return len(pdf)
        elif self.preferred_method == 'pdfplumber':
            return len(pdf.pages)
        else:
            return len(PyPDF2.PdfReader(pdf).pages)
    
    def _extract_single_page(self, pdf, page_num: int) -> Tuple[str, List[str]]:
        """Extract text and links from a single page."""
        if self.preferred_method == 'pymupdf':
            return self._extract_page_pymupdf(pdf, page_num)
        elif self.preferred_method == 'pdfplumber':
            return self._extract_page_pdfplumber(pdf, page_num)
        else:
            return self._extract_page_pypdf2(pdf, page_num)
    
    def _extract_single_page_sync(self, pdf, page_num: int) -> PageContent:
        """Synchronous single page extraction."""
        start_time = time.time()
        text, links = self._extract_single_page(pdf, page_num)
        
        return PageContent(
            page_num=page_num,
            text=text,
            hyperlinks=links,
            processing_time=time.time() - start_time,
            size_bytes=len(text.encode('utf-8'))
        )
    
    def _extract_page_pymupdf(self, pdf, page_num: int) -> Tuple[str, List[str]]:
        """Extract page content using PyMuPDF."""
        page = pdf[page_num]
        text = page.get_text()
        
        # Extract hyperlinks
        links = []
        for link in page.get_links():
            if isinstance(link, dict) and 'uri' in link:
                links.append(link['uri'])
        
        return text, links
    
    def _extract_page_pdfplumber(self, pdf, page_num: int) -> Tuple[str, List[str]]:
        """Extract page content using pdfplumber."""
        page = pdf.pages[page_num]
        text = page.extract_text() or ""
        
        # Extract hyperlinks
        links = []
        if hasattr(page, 'hyperlinks'):
            for link in page.hyperlinks:
                if isinstance(link, dict) and 'uri' in link:
                    links.append(link['uri'])
        
        return text, links
    
    def _extract_page_pypdf2(self, pdf, page_num: int) -> Tuple[str, List[str]]:
        """Extract page content using PyPDF2."""
        if hasattr(pdf, 'pages'):
            page = pdf.pages[page_num]
        else:
            reader = PyPDF2.PdfReader(pdf)
            page = reader.pages[page_num]
        
        text = page.extract_text()
        
        # Basic hyperlink extraction
        links = []
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
                                    links.append(str(uri))
                    except:
                        continue
        
        return text, links
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using PyMuPDF."""
        text = ""
        hyperlinks = []
        
        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
                
                # Extract hyperlinks
                links = page.get_links()
                for link in links:
                    if isinstance(link, dict) and 'uri' in link:
                        hyperlinks.append(str(link['uri']))
        finally:
            doc.close()
        
        return text, hyperlinks
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using pdfplumber."""
        text = ""
        hyperlinks = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                # Extract hyperlinks
                if hasattr(page, 'hyperlinks'):
                    for link in page.hyperlinks:
                        if isinstance(link, dict) and 'uri' in link:
                            hyperlinks.append(link['uri'])
        
        return text, hyperlinks
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> Tuple[str, List[str]]:
        """Extract using PyPDF2."""
        text = ""
        hyperlinks = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                # Extract hyperlinks
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
                            except:
                                continue
        
        return text, hyperlinks
    
    def _count_potential_matches(self, text: str, hyperlinks: List[str]) -> int:
        """Quick count of potential ORCID/Scholar matches for early termination."""
        count = 0
        
        # Quick regex checks
        if re.search(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', text):
            count += 1
        if re.search(r'scholar\.google', text, re.IGNORECASE):
            count += 1
        
        # Check hyperlinks
        for link in hyperlinks:
            if 'orcid.org' in link.lower():
                count += 1
            elif 'scholar.google' in link.lower():
                count += 1
        
        return count
    
    def _clean_hyperlinks(self, hyperlinks: List[str]) -> List[str]:
        """Clean and deduplicate hyperlinks."""
        if not hyperlinks:
            return []
        
        cleaned = set()
        for link in hyperlinks:
            if not link or not isinstance(link, str):
                continue
            
            link = link.strip()
            if len(link) < 10:
                continue
            
            # Basic URL validation
            if link.startswith(('http://', 'https://')) or any(domain in link.lower() for domain in ['orcid.org', 'scholar.google']):
                cleaned.add(link)
        
        return sorted(list(cleaned))
