
from __future__ import annotations

import json
import pathlib
import sys
import time
import re
from datetime import datetime
from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

PART_SEL    = "div.legislation-content.isParent.is-part"
SECTION_SEL = "div.legislation-content.is-section"
STATUS_MAP  = {
    "is-modified": "modified",
    "is-canceled": "canceled",
    "is-added":    "added",
}


def init_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )
    driver.set_page_load_timeout(120)
    return driver

def lazy_scroll(driver: webdriver.Chrome, pause: float = 0.7) -> None:
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h

def try_click(driver: webdriver.Chrome, elem) -> None:
    try:
        driver.execute_script("arguments[0].click()", elem)
    except WebDriverException:
        pass

def load_full_page(driver: webdriver.Chrome, url: str) -> str:
    driver.get(url)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SECTION_SEL))
    )
    lazy_scroll(driver)
    for hdr in driver.find_elements(By.CSS_SELECTOR, f"{PART_SEL} h3.title"):
        try_click(driver, hdr)
    time.sleep(0.4)
    return driver.page_source


def text(node: Tag | None, sep: str = "\n") -> str:
    return node.get_text(sep, strip=True) if node else ""


def extract_metadata(soup: BeautifulSoup) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for box in soup.select("div.row.mb-4 > div"):
        label = text(box.select_one("h4.label"))
        value = text(box.select_one("p"))
        if label:
            meta[label] = value
    desc = soup.select_one("p.legislation-description")
    if desc:
        meta.setdefault("نبذة عن النظام", text(desc, sep=" "))
    return meta


def detect_status(classes: List[str]) -> str:
    for cls, name in STATUS_MAP.items():
        if cls in classes:
            return name
    return "current"

def clean_title(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("المادة") and re.match(r"^\d+[/\-]", raw) is None:
        raw = "المادة " + raw
    return raw

def make_article(div: Tag) -> Dict[str, Any]:
    status = detect_status(div.get("class", []))
    h3_tag = div.find("h3")
    title_text = h3_tag.find(string=True, recursive=False).strip() if h3_tag else "مادة بدون عنوان"
    title = clean_title(title_text)
    body_div = div.find("div", class_="description")
    body = text(body_div, sep="\n") if body_div and status != "canceled" else ""
    return {
        "article_number": title,
        "text": body,
        "status": status,
    }

def build_structure(container: Tag) -> List[Dict[str, Any]]:
    structure, cur_part = [], None
    for div in container.select(f"{PART_SEL}, {SECTION_SEL}"):
        classes = div.get("class", [])
        if "is-part" in classes:
            cur_part = {
                "part_title": text(div.find("h3")),
                "articles": [],
            }
            structure.append(cur_part)
        elif "is-section" in classes:
            if cur_part is None:
                cur_part = {"part_title": "بدون باب", "articles": []}
                structure.append(cur_part)
            cur_part["articles"].append(make_article(div))
    return structure


def scrape_one(url: str, driver: webdriver.Chrome) -> Dict[str, Any]:
    html = load_full_page(driver, url)
    soup = BeautifulSoup(html, "html.parser")
    name = text(soup.select_one("h1.legislation-title")) or url.split("/")[-1]
    metadata = extract_metadata(soup)
    status_law = metadata.get("حالة التشريع", "").strip()
    container = soup.select_one("div.order-1") or soup
    rules = [] if status_law == "ملغي" else build_structure(container)
    return {
        "law_id": url.rstrip("/").split("/")[-1],
        "name": name,
        "url": url,
        "metadata": metadata,
        "rules": rules,
    }


def main() -> None:
    
    path = pathlib.Path("data/raw_data/moj_laws.txt")
    if not path.exists():
        sys.exit(f"✖ File not found: {path}")

    links: List[str] = []
    for line in path.read_text("utf8").splitlines():
        line = line.strip()
        if line.startswith("http"):
            url = line.split("#")[0].strip()
            links.append(url)

    out: List[Dict[str, Any]] = []
    driver = init_driver()

    for idx, link in enumerate(links, 1):
        print(f"({idx}/{len(links)}) {link}")
        try:
            out.append(scrape_one(link, driver))
        except TimeoutException:
            print("  ❌ Timeout while loading – skipped")
        except Exception as exc:
            print("  ❌", type(exc).__name__, exc)

    driver.quit()

    out_dir = pathlib.Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "scraped_data/moj_laws_detailed.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), "utf8")

    print("✅ Saved to", out_path.resolve())
    print("🕒", datetime.now().isoformat(timespec="seconds"))

if __name__ == "__main__":
    main()