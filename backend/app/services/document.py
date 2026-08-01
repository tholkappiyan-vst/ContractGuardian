import io
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from PIL import Image
import pytesseract


async def extract_text(content: bytes, file_type: str) -> dict:
    """Extract text from document bytes. Returns {text, page_count, ocr_used, ocr_confidence}."""
    if file_type == "pdf":
        return _extract_pdf(content)
    elif file_type == "docx":
        return _extract_docx(content)
    elif file_type in ("png", "jpg", "jpeg", "tiff"):
        return _extract_image(content)
    raise ValueError(f"Unsupported file type: {file_type}")


def _extract_pdf(content: bytes) -> dict:
    doc = fitz.open(stream=content, filetype="pdf")
    pages_text = []
    has_text = False

    for page in doc:
        text = page.get_text()
        if text.strip():
            has_text = True
        pages_text.append(text)

    if has_text:
        return {
            "text": "\n\n".join(pages_text),
            "page_count": len(pages_text),
            "ocr_used": False,
            "ocr_confidence": None,
        }

    # Scanned PDF — fall back to OCR
    all_text = []
    confidences = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        page_text = " ".join(w for w in data["text"] if w.strip())
        all_text.append(page_text)
        confs = [int(c) for c in data["conf"] if int(c) > 0]
        if confs:
            confidences.append(sum(confs) / len(confs))

    avg_conf = (sum(confidences) / len(confidences) / 100) if confidences else 0.0
    return {
        "text": "\n\n".join(all_text),
        "page_count": len(pages_text),
        "ocr_used": True,
        "ocr_confidence": round(avg_conf, 3),
    }


def _extract_docx(content: bytes) -> dict:
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return {
        "text": "\n\n".join(paragraphs),
        "page_count": None,
        "ocr_used": False,
        "ocr_confidence": None,
    }


def _extract_image(content: bytes) -> dict:
    img = Image.open(io.BytesIO(content))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    text = " ".join(w for w in data["text"] if w.strip())
    confs = [int(c) for c in data["conf"] if int(c) > 0]
    avg_conf = (sum(confs) / len(confs) / 100) if confs else 0.0
    return {
        "text": text,
        "page_count": 1,
        "ocr_used": True,
        "ocr_confidence": round(avg_conf, 3),
    }
