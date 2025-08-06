
from __future__ import annotations

import json
import pathlib
import re
from datetime import datetime
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup, Tag

#  Session
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Apple Silicon) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
)

PART_RE       = re.compile(r"^\s*الباب\s+",  re.I)
CHAP_RE       = re.compile(r"^\s*الفصل\s+", re.I)
CANCEL_CLASSES = {"canceled", "canceled-article"}

# Helpers 
def text(node: Tag | None, sep: str = "\n") -> str:
    return node.get_text(sep, strip=True) if node else ""


def fetch_html(url: str) -> str | None:
    try:
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.RequestException:
        print(f"❌ GET failed → {url}")
        return None


# Metadata extraction 
def extract_metadata(soup: BeautifulSoup) -> Dict[str, str]:
    meta: dict[str, str] = {}

    info = soup.select_one("div.system_info")
    if info:
        for row in info.select("div"):
            lab  = text(row.select_one("label"))
            val  = text(row.select_one("span"), sep=" ")
            if lab:
                meta[lab] = val

    brief = soup.select_one("div.system_brief .HTMLContainer")
    meta["نبذة عن النظام"] = text(brief, sep=" ") if brief else ""
    return meta


#  Article extraction 
def make_article(div: Tag, root: Tag) -> Dict[str, Any]:
    classes   = set(div.get("class", []))
    canceled  = bool(classes & CANCEL_CLASSES)

    title     = text(div.find("h3", class_="center")) or "بدون رقم"
    body      = "" if canceled else text(div.find("div", class_="HTMLContainer"), sep="\n")

    amendments: list[str] = []
    link = div.find("a", class_="ancArticlePrevVersions")
    if link and link.has_attr("data-articleid"):
        aid   = link["data-articleid"]
        popup = root.find("div", class_=f"{aid} popup-list")
        if popup:
            for blk in popup.find_all("div", class_="HTMLContainer"):
                t = text(blk)
                if t:
                    amendments.append(t)

    return {
        "article_number": title,
        "text": body,
        "canceled": canceled or None,
        "amendments": amendments or None,
    }


def build_structure(root: Tag) -> List[Dict[str, Any]]:
    structure: list[dict[str, Any]] = []
    current_part: dict[str, Any] | None = None
    current_chapter: dict[str, Any] | None = None

    for node in root.select("h3.center, div.article_item"):
        if node.name == "h3" and PART_RE.match(node.text):
            current_part = {"part_title": text(node), "chapters": [], "articles": []}
            structure.append(current_part)
            current_chapter = None
            continue

        if node.name == "h3" and CHAP_RE.match(node.text):
            if current_part is None:
                current_part = {
                    "part_title": "بدون باب",
                    "chapters": [],
                    "articles": [],
                }
                structure.append(current_part)

            current_chapter = {"chapter_title": text(node), "articles": []}
            current_part["chapters"].append(current_chapter)
            continue

        if node.name == "div" and "article_item" in node.get("class", []):
            article = make_article(node, root)

            if current_chapter:
                current_chapter["articles"].append(article)
            elif current_part:
                current_part["articles"].append(article)
            else:
                structure.append(
                    {
                        "part_title": "بدون باب",
                        "chapters": [],
                        "articles": [article],
                    }
                )

    return structure


# I/O 
def load_sources(path: str = "data/raw_data/boe_laws.txt") -> List[Dict[str, str]]:
    out = []
    for line in pathlib.Path(path).read_text("utf8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            url, name = map(str.strip, line.split("#"))
            out.append(
                {
                    "law_id": url.rstrip("/").split("/")[-2],
                    "name": name,
                    "url": url,
                }
            )
    return out


# Scraper
def scrape_boe_law(entry: Dict[str, str]) -> Dict[str, Any] | None:
    url  = f"https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/{entry['law_id']}/1"
    html = fetch_html(url)
    if not html:
        return None

    soup  = BeautifulSoup(html, "html.parser")
    meta  = extract_metadata(soup)
    status = meta.get("الحالة", "").strip()

    root = soup.find(id="divLawText") or soup

    rules: list[dict[str, Any]] = []
    if status != "لاغي":       
        rules = build_structure(root)

    return {
        "law_id": entry["law_id"],
        "name":   entry["name"],
        "url":    entry["url"],
        "metadata": meta,
        "rules":  rules,
    }


#  Main 
def main() -> None:
    results: list[dict[str, Any]] = []

    for src in load_sources():
        print(f"📖 Scraping «{src['name']}» …")
        data = scrape_boe_law(src)
        if data:
            results.append(data)

    out_path = pathlib.Path("data/scraped_data/boe_laws_detailed.json")
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf8"
    )

    print(f"\n✅ Saved → {out_path.resolve()}")
    print("🕓 Generated at", datetime.now().isoformat(timespec="seconds"))


if __name__ == "__main__":
    main()