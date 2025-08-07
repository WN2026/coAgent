import requests
from bs4 import BeautifulSoup
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open("data\\Procedures_sources", "r", encoding="utf-8") as file:
    lines = [line.strip() for line in file if line.strip()]

categories = {}

for line in lines:
    try:
        main_category, url = [part.strip() for part in line.split("|")]
    except ValueError:
        print(f"*Ignore an invalid line: {line}")
        continue

    print(f"----------Department processing-------------: {main_category} | {url}")

    try:
        response = requests.get(url, verify=False)
        soup = BeautifulSoup(response.content, "html.parser")

        h4_tag = soup.find("h4", class_="pt-1 h4-oneLine")
        sub_category = h4_tag.get_text(strip=True) if h4_tag else "غير معروف"

        links = []
        for a_tag in soup.select('a.block-link'):
            href = a_tag.get('href')
            if href and href.startswith("/guidelines/details?guidelineJourneyId="):
                full_url = f"https://business.sa{href}"
                links.append(full_url)

        all_steps = []

        for step_url in links:
            print(f"*Processing the step: {step_url}")
            step_resp = requests.get(step_url, verify=False)
            step_soup = BeautifulSoup(step_resp.text, "html.parser")

            step_number = step_soup.select_one("span.step-sort")
            step_name = step_soup.select_one("h4#stepName")
            step_number = step_number.get_text(strip=True) if step_number else ""
            step_name = step_name.get_text(strip=True) if step_name else ""

            desc_div = step_soup.select_one("div.sub3-guidence-result-container.p-3")
            description = desc_div.get_text(strip=True) if desc_div else ""

            requirements_section = step_soup.select_one("#pills-home")
            requirements = {}
            if requirements_section:
                container = requirements_section.select_one("#guidelines-terms")
                if container:
                    children = list(container.children)
                    current_title = "General"
                    requirements[current_title] = []

                    for child in children:
                        if child.name is None:
                            continue
                        if child.name in ["h4", "h5", "strong", "p"]:
                            text = child.get_text(strip=True)
                            if text:
                                current_title = text
                                if current_title not in requirements:
                                    requirements[current_title] = []
                        elif child.name == "ul":
                            lis = child.find_all("li")
                            items = [li.get_text(strip=True) for li in lis if li.get_text(strip=True)]
                            requirements[current_title].extend(items)

                    if len(requirements) == 1 and "General" in requirements:
                        requirements = requirements["General"]

            authority_links = []
            authority_tab = step_soup.select_one("#pills-profile")
            if authority_tab:
                links_auth = authority_tab.select("a[href^='http']")
                for link in links_auth:
                    href = link.get('href')
                    if href and (".sa" in href):
                        if href not in authority_links:
                            authority_links.append(href)
            authority = authority_links if authority_links else []

            additional_info_list = []
            info_ul = step_soup.select_one("div.sub3-guidence-result-container ul.CustomUL")
            if info_ul:
                additional_info_list = [li.get_text(strip=True) for li in info_ul.find_all("li")]

            duration = ""
            cost = []
            items = step_soup.select("div.item")
            for item in items:
                title = item.find("h5")
                content = item.find("div", class_="content")
                if not title or not content:
                    continue
                title_text = title.get_text(strip=True)
                if title_text == "المدة الزمنية":
                    duration = content.get_text(strip=True)
                elif title_text == "المقابل المالي":
                    lis = content.find_all("li")
                    if lis:
                        cost = [li.get_text(strip=True) for li in lis]
                    else:
                        cost = [content.get_text(strip=True)]

            step_data = {
                "step_no": step_number,
                "step_name": step_name,
                "step_description": description,
                "requirements": requirements,
                "authority": authority,
                "additional_info": additional_info_list,
                "cost": cost,
                "duration": duration,
            }

            all_steps.append(step_data)

        sub_item = {
            "type": sub_category,
            "url": url,
            "Procedures": all_steps
        }

        if main_category not in categories:
            categories[main_category] = []

        categories[main_category].append(sub_item)

    except Exception as e:
        print(f"*Error while processing{url}: {e}")

final_json = {
    "categories": [
        {
            "name": name,
            "subcategories": subcats
        } for name, subcats in categories.items()
    ]
}

with open("data\\Procedures.json", "w", encoding="utf-8") as out:
    json.dump(final_json, out, ensure_ascii=False, indent=2)

print("-----------The file has been created---------------: Procedures.json")

