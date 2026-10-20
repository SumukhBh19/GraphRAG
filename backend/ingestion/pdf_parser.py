import re
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

class PDFParser:
    """
    Extracts text page by page from SEBI and RBI circulars using PyMuPDF (fitz).
    Strips headers, footers, and page numbers, and extracts document metadata.
    """

    def __init__(self):
        # ---------------------------------------------------------------
        # Circular code patterns
        #   SEBI: SEBI/HO/IMD/DF3/CIR/P/2020/172  (may contain hyphens)
        #   RBI : RBI/FIDD/2020-21/72 or RBI/FED/2018-19/67
        # ---------------------------------------------------------------
        self.sebi_pattern = re.compile(
            r"SEBI/[A-Z0-9_/\-]+(?:/\d{4}/\d+)",
            re.IGNORECASE
        )
        self.rbi_pattern = re.compile(
            r"RBI/[A-Z0-9_/\-]+(?:/\d{2,4}(?:-\d{2,4})?/\d+)",
            re.IGNORECASE
        )
        # "Circular Ref:" prefix often appears in our generated PDFs — capture full code from that line
        self.ref_line_pattern = re.compile(
            r"Circular\s+Ref\s*:\s*([A-Z][A-Z0-9_/\-]+)",
            re.IGNORECASE
        )
        # "Date:" prefix line — grab the human-readable date that follows
        self.date_line_pattern = re.compile(
            r"Date\s*:\s*("
            r"(?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+\d{1,2},\s+\d{4}"
            r")",
            re.IGNORECASE
        )
        # Fallback: month-name date anywhere in text
        self.date_fallback_pattern = re.compile(
            r"(?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            re.IGNORECASE
        )

    def parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Parses a PDF file and returns cleaned text with per-page tracking and metadata.
        """
        file_path = Path(file_path)
        doc = fitz.open(str(file_path))

        pages_content: List[Dict[str, Any]] = []
        full_text_list: List[str] = []
        detected_code = None
        detected_date = None
        regulator = (
            "SEBI" if "sebi" in file_path.name.lower()
            else ("RBI" if "rbi" in file_path.name.lower() else "UNKNOWN")
        )

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")

            # ── Extract metadata from the first two pages only ──────────
            if page_idx < 2:
                # Priority 1: "Circular Ref:" line (exact match from our generated format)
                if not detected_code:
                    ref_m = self.ref_line_pattern.search(text)
                    if ref_m:
                        detected_code = ref_m.group(1).strip().rstrip("/")
                        if "sebi" in detected_code.lower():
                            regulator = "SEBI"
                        elif "rbi" in detected_code.lower():
                            regulator = "RBI"

                # Priority 2: inline SEBI / RBI code patterns
                if not detected_code:
                    sebi_m = self.sebi_pattern.search(text)
                    rbi_m  = self.rbi_pattern.search(text)
                    if sebi_m:
                        detected_code = sebi_m.group(0).strip().rstrip("/")
                        regulator = "SEBI"
                    elif rbi_m:
                        detected_code = rbi_m.group(0).strip().rstrip("/")
                        regulator = "RBI"

                # Priority 1 for date: "Date: <month> DD, YYYY" explicit line
                if not detected_date:
                    date_line_m = self.date_line_pattern.search(text)
                    if date_line_m:
                        detected_date = date_line_m.group(1).strip()

                # Priority 2 for date: any month-name date in text
                if not detected_date:
                    date_fb_m = self.date_fallback_pattern.search(text)
                    if date_fb_m:
                        detected_date = date_fb_m.group(0).strip()

            clean_page_text = self._clean_text(text)
            if clean_page_text:
                pages_content.append({
                    "page_number": page_idx + 1,
                    "text": clean_page_text
                })
                full_text_list.append(clean_page_text)

        total_pages = len(doc)
        doc.close()

        return {
            "file_name":     file_path.name,
            "file_path":     str(file_path),
            "regulator":     regulator,
            "circular_code": detected_code or file_path.stem,
            "circular_date": detected_date or "Unknown",
            "total_pages":   total_pages,
            "pages":         pages_content,
            "full_text":     "\n\n".join(full_text_list)
        }

    def _clean_text(self, text: str) -> str:
        """Strips header/footer patterns, form feeds, and excessive whitespace."""
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            # Drop pure page number lines
            if re.match(r"^(page\s+\d+(\s+of\s+\d+)?|\d+)$", line_str, re.IGNORECASE):
                continue
            # Drop repetitive regulatory body name headers/footers
            if re.match(
                r"^(भारतीय प्रतिभूति और विनिमय बोर्ड"
                r"|Securities and Exchange Board of India"
                r"|Reserve Bank of India)$",
                line_str, re.IGNORECASE
            ):
                continue
            if line_str:
                cleaned_lines.append(line_str)

        return "\n".join(cleaned_lines)
