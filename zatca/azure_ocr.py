# azure_ocr.py
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import re
import os
import tempfile
import requests

ENDPOINT = "**********************************"
KEY = "***************************************"

client = DocumentAnalysisClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))

def extract_text_from_pdf(file_path: str) -> list[str]:
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", document=f)
    result = poller.result()

    lines = []
    for page in result.pages:
        for line in page.lines:
            text = line.content.strip()
            if not text:
                continue
            if re.fullmatch(r"\d+", text):
                continue
            if re.search(r"(محتويات|فهرس|صفحة)", text):
                continue
            lines.append(text)
    return lines

def remove_consecutive_fasl_lines(lines: list[str]) -> list[str]:
    cleaned_lines = []
    i = 0
    while i < len(lines):
        current_line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        next_next_line = lines[i + 2].strip() if i + 2 < len(lines) else ""

        if current_line.startswith("الفصل") and next_line.startswith("الفصل"):
            print(f"🗑️ حذف سطر 'الفصل' المكرر: '{lines[i]}'")
            i += 1
            continue

        if current_line.startswith("الفصل") and next_line.startswith("المادة") and next_next_line.startswith("المادة"):
            print(f"🗑️ حذف المقطع الذي يبدأ من: '{lines[i]}' حتى نصل إلى فصل جديد")
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith("الفصل"):
                    break
                i += 1
            continue  

        cleaned_lines.append(lines[i])
        i += 1

    return cleaned_lines


def structure_legal_text(lines: list[str]) -> str:
    structured_text = ""
    buffer = ""
    for line in lines:
        if re.match(r"^(المادة|الفصل)\b", line):
            if buffer:
                structured_text += buffer.strip() + "\n\n"
            if line.startswith("الفصل"):
                structured_text += "\n\n\n"
            buffer = line + "\n"
        else:
            buffer += line + " "
    if buffer:
        structured_text += buffer.strip()
    print(structured_text)
    return structured_text



def process_pdf_url(pdf_url: str) -> str:
    """
    ينزّل PDF من رابط، ويستخرج النص منه ويعيد النص القانوني المنسق.
    """
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
    except Exception as e:
        print(f" فشل تحميل الملف: {e}")
        return ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(response.content)
        tmp_path = tmp_file.name

    try:
        lines = extract_text_from_pdf(tmp_path)
        cleaned_text=remove_consecutive_fasl_lines(lines)
        final_text = structure_legal_text(cleaned_text)
        return final_text
    except Exception as e:
        print(f" فشل استخراج النص: {e}")
        return ""
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

