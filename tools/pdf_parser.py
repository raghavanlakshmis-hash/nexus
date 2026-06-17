import fitz  # PyMuPDF
from pathlib import Path

def parse_discharge_pdf(file_path: str) -> dict:
    """
    Extract raw text from discharge summary PDF.
    Returns dict with success status and extracted text.
    """
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        page_count = len(doc)  # save before close — doc.close() makes len(doc) fail
        doc.close()

        if not full_text.strip():
            return {
                "success": False,
                "error": "PDF appears to be scanned or image-based. Text extraction failed.",
                "text": None
            }

        return {
            "success": True,
            "text": full_text,
            "page_count": page_count,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"PDF parse failed: {str(e)}",
            "text": None
        }