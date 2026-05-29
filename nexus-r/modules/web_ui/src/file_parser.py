import io
from fastapi import UploadFile

async def extract_file_content(file: UploadFile) -> str:
    """Extracts text content from uploaded files (PDF, DOCX, TXT)."""
    filename = file.filename.lower()
    content = await file.read()
    
    if filename.endswith(".pdf"):
        return _extract_pdf(content)
    elif filename.endswith(".docx"):
        return _extract_docx(content)
    else:
        # Fallback to plain text for unknown/text types
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

def _extract_pdf(content: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "[Error: PyMuPDF not installed. Cannot parse PDF.]"
        
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text() + "\n"
        pdf.close()
        return text.strip()
    except Exception as e:
        return f"[Error parsing PDF: {str(e)}]"

def _extract_docx(content: bytes) -> str:
    try:
        import docx
    except ImportError:
        return "[Error: python-docx not installed. Cannot parse DOCX.]"
        
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        return f"[Error parsing DOCX: {str(e)}]"
