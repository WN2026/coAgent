import requests
from bs4 import BeautifulSoup
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open("data\services_sources", "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]

services = []

for url in urls:
    print(f"Processing: {url}")
    try:
        response = requests.get(url, verify=False, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")

        def extract_text(selector):
            tag = soup.select_one(selector)
            return tag.get_text(strip=True) if tag else ""

        def extract_list_items(selector):
            ul = soup.select_one(selector)
            return [li.get_text(strip=True) for li in ul.find_all("li")] if ul else []

        def extract_fees(selector):
            fees_div = soup.select_one(selector)
            if not fees_div:
                return []
            li_elements = fees_div.find_all("li")
            if li_elements:
                return [li.get_text(strip=True) for li in li_elements]
            text = fees_div.get_text(strip=True)
            return [text] if text else []

        service = {
            "url": url,
            "service_name": extract_text("#service-title"),
            "description": extract_text("#service-description"),
            "requirements": extract_list_items("#service-terms ul"),
            "execution_duration": extract_text("#service-durations"),
            "service_fee": extract_fees("#service-fees")
        }

        services.append(service)

    except Exception as e:
        print(f"فشل في {url}\n السبب: {e}")

with open("data\services.json", "w", encoding="utf-8") as f:
    json.dump({"services": services}, f, ensure_ascii=False, indent=2)

print("\n The data has been extracted and saved in services.json")
