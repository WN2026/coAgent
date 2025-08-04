import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def load_mc_law_links(file_path="data/mc_laws.txt"):
    links = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if "#" in line:
                url, name = line.strip().split(" #", 1)
                links.append((url, name))
    return links


def extract_articles(container):
    articles = []

    for art in container.select(".rules-article-container"):
        # Handle both modified and unmodified containers
        article_number = "بدون رقم"

        # Try known patterns for number
        h4 = art.find("h4")
        if h4:
            span_num = (
                h4.find("span", class_="col-md-5") or
                h4.find("span", class_="col-xs-9")
            )
            if span_num:
                article_number = span_num.get_text(strip=True)

        # Always get the actual visible amended/current text from <p>
        p = art.find("p")
        article_text = p.get_text("\n", strip=True) if p else ""

        articles.append({
            "article_number": article_number,
            "text": article_text
        })

    return articles
def extract_structured_content(container):
    structure = []
    part_tags = container.select("div.accordion > h3")

    if part_tags:
        for part_tag in part_tags:
            part_title = part_tag.get_text(strip=True)
            part_div = part_tag.find_next_sibling("div", class_="ui-accordion-content")
            part = {"part_title": part_title, "chapters": [], "articles": []}

            chapter_tags = part_div.select("div.accordion > h3")
            if chapter_tags:
                for chapter_tag in chapter_tags:
                    chapter_title = chapter_tag.get_text(strip=True)
                    chapter_div = chapter_tag.find_next_sibling("div", class_="ui-accordion-content")
                    chapter = {
                        "chapter_title": chapter_title,
                        "articles": extract_articles(chapter_div)
                    }
                    part["chapters"].append(chapter)
            else:
                part["articles"] = extract_articles(part_div)

            structure.append(part)
    else:
        chapter_tags = container.select("div.accordion > h3")
        if chapter_tags:
            for chapter_tag in chapter_tags:
                chapter_title = chapter_tag.get_text(strip=True)
                chapter_div = chapter_tag.find_next_sibling("div", class_="ui-accordion-content")
                structure.append({
                    "part_title": "بدون باب",
                    "chapters": [{
                        "chapter_title": chapter_title,
                        "articles": extract_articles(chapter_div)
                    }],
                    "articles": []
                })
        else:
            structure.append({
                "part_title": "بدون باب",
                "chapters": [],
                "articles": extract_articles(container)
            })

    return structure


def expand_all_accordions(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".accordion h3"))
        )
        headers = driver.find_elements(By.CSS_SELECTOR, ".accordion h3")
        for h in headers:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", h)
                h.click()
                time.sleep(0.2)
            except Exception:
                continue
    except Exception:
        print("⚠️ Accordion headers not found.")


def scrape_law_sections(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    expand_all_accordions(driver)

    time.sleep(1)  # Final wait for content to load
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    title = soup.find("h2").get_text(strip=True) if soup.find("h2") else "بدون عنوان"
    result = {
        "title": title,
        "url": url,
        "law_id": url.split("lawId=")[-1],
        "rules": [],
        "regulations": []
    }

    rule_container = soup.find("div", class_="rule-container")
    if rule_container:
        result["rules"] = extract_structured_content(rule_container)

    reg_container = soup.find("div", class_="regulation-container")
    if reg_container:
        result["regulations"] = extract_structured_content(reg_container)

    return result


def process_all_mc_laws():
    links = load_mc_law_links()
    all_data = []

    for i, (url, name) in enumerate(links):
        print(f"🔍 [{i+1}/{len(links)}] Scraping: {name}")
        try:
            law_data = scrape_law_sections(url)
            all_data.append(law_data)
        except Exception as e:
            print(f"❌ Error scraping {name}: {e}")
        time.sleep(2)

    output_path = "data/mc_laws_detailed.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ تم حفظ جميع القوانين في: {output_path}")


if __name__ == "__main__":
    process_all_mc_laws()