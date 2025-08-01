import json
import os
import sys
from azure_ocr import process_pdf_url
from json_converter import convert_text_to_json_structure  

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.zatca.scraper_pdf_urls import extract_pdf_links




def clean_code_block_markers(text: str) -> str:
    """
    تنظف ```json و ``` من النص لو موجودة
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def split_text_by_chapter(text: str) -> list[str]:
    """
    تقسم النص إلى دفعات بناءً على 3 أسطر فارغة، كل دفعة تمثل فصل مستقل.
    """
    return [chunk.strip() for chunk in text.split("\n\n\n") if chunk.strip()]


def main():
    url_pairs = extract_pdf_links()  
    output_file = "data\zatca_data.json"
    all_laws = []

    for idx, (page_url, pdf_url) in enumerate(url_pairs, 1):
        print(f"\n [{idx}] معالجة صفحة: {page_url}")
        print(f"   معالجة ملف PDF: {pdf_url}")

        extracted_text = process_pdf_url(pdf_url)
        if not extracted_text.strip():
            print(" لا يوجد نص مستخرج.")
            continue

        chunks = split_text_by_chapter(extracted_text)
        if not chunks:
            print(" لم يتم العثور على فصول.")
            continue

        combined_law = {
            "name": None,
            "url": page_url,   
            "metadata": {},
            "chapters": []
        }

        for part_num, chunk in enumerate(chunks, 1):
            print(f" إرسال الفصل {part_num} للمودل...")
            response = convert_text_to_json_structure(chunk)
            if not response.strip():
                print(" لم يتم توليد JSON لهذا الفصل.")
                continue

            cleaned = clean_code_block_markers(response)

            try:
                parsed = json.loads(cleaned)
                if part_num == 1:
                    combined_law["name"] = parsed.get("name", "")
                    combined_law["metadata"] = parsed.get("metadata", {})
                combined_law["chapters"].extend(parsed.get("chapters", []))
                print(f" تم تحليل الفصل {part_num}")
            except json.JSONDecodeError as e:
                print(f"خطأ في تحويل JSON للفصل {part_num}: {e}")
                continue

        if combined_law["chapters"]:
            all_laws.append(combined_law)
            print(f" تم تجميع القانون رقم {idx} بنجاح.")


    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"laws": all_laws}, f, ensure_ascii=False, indent=2)

    print(f"\n تم حفظ كل القوانين في {output_file}")


if __name__ == "__main__":
    main()
