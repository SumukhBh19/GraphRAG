from typing import List, Dict, Any

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter


class RegulatoryChunker:
    """
    Sentence-aware chunking optimized for legal and regulatory texts.
    Maintains provenance to page numbers, circular code, and document date.

    Dual-splitter strategy:
    - SEBI circulars: 2800 chars (~700 tokens) to preserve numbered paragraphs intact
    - All others (RBI, generic): 900 chars (~225 tokens) for fine-grained retrieval
    """

    SEPARATORS = ["\n\n", "\n", r"(?<=[\.!\?])\s+", " ", ""]

    def __init__(
        self,
        chunk_size: int = 900,
        chunk_overlap: int = 150,
        sebi_chunk_size: int = 2800,
        sebi_chunk_overlap: int = 350,
    ):
        # Default splitter for RBI and other documents
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.SEPARATORS,
            keep_separator=True,
        )
        # SEBI-specific splitter: 600-800 tokens (~2800 chars) to preserve structured paragraphs intact
        self.sebi_splitter = RecursiveCharacterTextSplitter(
            chunk_size=sebi_chunk_size,
            chunk_overlap=sebi_chunk_overlap,
            separators=self.SEPARATORS,
            keep_separator=True,
        )

    def _get_splitter(self, regulator: str, circular_code: str):
        """Choose the right splitter based on document origin."""
        r = (regulator or "").upper()
        c = (circular_code or "").upper()
        if "SEBI" in r or "SEBI" in c:
            return self.sebi_splitter
        return self.default_splitter

    def chunk_document(self, parsed_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Takes output of PDFParser and chunks each page while preserving metadata.
        """
        chunks: List[Dict[str, Any]] = []
        file_name = parsed_doc["file_name"]
        regulator = parsed_doc.get("regulator", "SEBI")
        circular_code = parsed_doc.get("circular_code", file_name)
        circular_date = parsed_doc.get("circular_date", "Unknown")

        splitter = self._get_splitter(regulator, circular_code)
        global_chunk_idx = 0

        for page in parsed_doc["pages"]:
            page_num = page["page_number"]
            page_text = page["text"]

            page_splits = splitter.split_text(page_text)
            for split_idx, split_text in enumerate(page_splits):
                chunk_id = f"{file_name}#p{page_num}#c{split_idx}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_name": file_name,
                    "regulator": regulator,
                    "circular_code": circular_code,
                    "circular_date": circular_date,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "text": split_text.strip()
                })
                global_chunk_idx += 1

        return chunks
