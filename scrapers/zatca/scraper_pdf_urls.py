# scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_pdf_links():
    urls = []
    try:
        with open("data\\zatca_sources", "r", encoding="utf-8") as f:
            page_urls = [line.strip() for line in f if line.strip()]

        for page_url in page_urls:
            print(f"\n جاري استخراج روابط PDF من: {page_url}")
            response = requests.get(page_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.lower().endswith(".pdf"):
                    full_url = urljoin(page_url, href)
                    print(f" رابط PDF مستخرج: {full_url}")
                    urls.append((page_url, full_url))

    except Exception as e:
        print(f" فشل أثناء استخراج الروابط: {e}")

    return urls
