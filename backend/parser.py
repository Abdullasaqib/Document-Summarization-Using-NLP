import fitz  # PyMuPDF
import docx
import io
import pytesseract
from PIL import Image
import sys
import os

# Set Tesseract path if on Windows and not in PATH (common issue)
# Try standard locations
possible_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\HP\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
]
for p in possible_paths:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        break

def parse_pdf(file_bytes: bytes) -> str:
    """Extracts text from a PDF file using Hybrid approach (Text -> OCR)."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    
    # Strategy 1: Fast Text Extraction
    for page in doc:
        text += page.get_text()
    
    cleaned_text = clean_text(text)
    
    # Strategy 2: OCR Fallback if text is too short (likely scanned)
    if len(cleaned_text) < 50:
        print("DEBUG: Text too short or empty. Switching to OCR...")
        text = ocr_pdf(doc)
        cleaned_text = clean_text(text)
        
    return cleaned_text

def ocr_pdf(doc) -> str:
    """Renders PDF pages as images and runs OCR."""
    text = ""
    print(f"DEBUG: Running OCR on {len(doc)} pages...")
    for i, page in enumerate(doc):
        # Render page to image (zoom=2 for better quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Run Tesseract
        page_text = pytesseract.image_to_string(img)
        text += page_text + "\n"
        print(f"DEBUG: OCR Page {i+1} complete.")
        
    return text

def parse_docx(file_bytes: bytes) -> str:
    """Extracts text from a DOCX file."""
    doc = docx.Document(io.BytesIO(file_bytes))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return clean_text(text)

def clean_text(text: str) -> str:
    """Basic text cleaning."""
    # Remove excessive whitespace
    text = " ".join(text.split())
    return text

def parse_document(filename: str, file_bytes: bytes) -> str:
    """Dispatches to the correct parser based on filename extension."""
    if filename.lower().endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif filename.lower().endswith(".docx"):
        return parse_docx(file_bytes)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
