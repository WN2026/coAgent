# openai_json_converter.py
import os
from openai import OpenAI

client = OpenAI(api_key="*****************************************")

system_prompt = """
أنت مساعد قانوني ذكي. 

مهمتك:
- اقرأ النص كاملاً كما هو من ملف نصي.
- لا تعدل، لا تلخص، لا تغير أي كلمة.
-يجب عليك ان لا تتخطى اي فصل او مادة مهما كان السبب
- استخرج الميتا بدقة:
  -الاسم 
  - تاريخ الإصدار الهجري (تاريخ الاصدار)
  - رقم القرار (رقم القرار)
- استخرج الفصول (chapters) والعناوين والمواد (articles) كما في النص بالضبط.
- اعطيني الناتج بصيغة JSON مثل المثال التالي:

{
  "name": "عنوان النظام",
  "url"="...",

  "metadata": {
    " الاسم":"عنوان النظام",
    "تاريخ الاصدار": "...",
    "رقم القرار":"..."
  },
  "chapters": [
    {
      "chapter_title": "عنوان الفصل",
      "articles": [
        {
          "title": "عنوان المادة",
          "content": "نص المادة كاملاً كما هو"
        }
      ]
    }
  ]
}

""".strip()

def convert_text_to_json_structure(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}  
            ],
            temperature=0.2
        )
        print(response.choices[0].message.content)
        return response.choices[0].message.content
    except Exception as e:
        print(f" فشل تحويل النص إلى JSON: {e}")
        return ""

