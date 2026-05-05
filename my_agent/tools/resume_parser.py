"""
Resume Parser Tool
Extracts text content from a PDF resume so the LLM can analyze
the candidate's niche, skills, and interests.
"""

import os
from pypdf import PdfReader


def parse_resume(file_path: str = "") -> dict:
    """
    Extract all text content from a PDF resume file.

    The extracted text is returned as-is for the LLM agent to analyze
    and identify the candidate's niche, skills, interests, and experience.

    Args:
        file_path: Absolute path to the resume PDF file.
                   If empty, falls back to the RESUME_PATH environment variable.

    Returns:
        A dict with:
          - 'text': the full extracted resume text
          - 'pages': number of pages in the PDF
        or an 'error' key if something went wrong.
    """
    try:
        # Resolve file path
        if not file_path:
            file_path = os.environ.get(
                "RESUME_PATH",
                r"file location",
            )

        if not os.path.exists(file_path):
            return {"error": f"Resume file not found at: {file_path}"}

        # Extract text from all pages using pypdf
        reader = PdfReader(file_path)
        page_count = len(reader.pages)

        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

        if not full_text.strip():
            return {
                "error": "Could not extract any text from the PDF. "
                "It might be a scanned/image-based resume."
            }

        return {
            "text": full_text.strip(),
            "pages": page_count,
            "file_path": file_path,
        }

    except Exception as e:
        return {"error": f"Failed to parse resume: {str(e)}"}
