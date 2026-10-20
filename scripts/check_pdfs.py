import sys
sys.path.insert(0, '.')
from backend.ingestion.pdf_parser import PDFParser
from pathlib import Path

parser = PDFParser()
raw_dir = Path('data/raw')

for pdf in sorted(raw_dir.glob('*.pdf')):
    result = parser.parse_pdf(pdf)
    full = result['full_text'].strip()
    print("=== " + pdf.name + " ===")
    print("  Regulator : " + result["regulator"])
    print("  Code      : " + result["circular_code"])
    print("  Date      : " + result["circular_date"])
    print("  Pages     : " + str(result["total_pages"]))
    print("  Chars     : " + str(len(full)))
    print("  Preview   :")
    print(full[:400])
    print()
