# utils_scrape.py
# -*- coding: utf-8 -*-
"""
أدوات السحب والتنظيف لبوابة الأنظمة السعودية (BOE)
--------------------------------------------------
* جلسة CloudScraper تتجاوز حماية Cloudflare.
* إعادة المحاولة التلقائيـة مع back-off أسّي.
* دوال مساعدة:
    • extract_urls(text)        → قائمة كل الروابط في نص حر
    • clean_text(text)          → إزالة الفراغات والأسطر الزائدة
    • fetch_html(url)           → جلب HTML خام مع Timeout كبير
    • extract_visible_text(html)→ النص المرئي فقط
    • robust_scrape(url)        → جلب + تنظيف مع إعادة المحاولة
"""

from __future__ import annotations

import random, re, time
from typing import List, Tuple

import cloudscraper
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup


def _make_session() -> cloudscraper.CloudScraper:
    """تهيئة CloudScraper مع سياسة إعادة المحاولة."""
    sess = cloudscraper.create_scraper()
    retry_strategy = Retry(
        total=5,                   
        backoff_factor=2,               
        status_forcelist=[429, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess


SESSION = _make_session()


def extract_urls(text: str) -> List[str]:
    """استخراج كل روابط http/https من نص."""
    return re.findall(r"https?://[^\s)>\]\"'<>]+", text)


def clean_text(text: str) -> str:
    """تنظيف الفراغات والأسطر المكرّرة."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text).strip()
    return text


def fetch_html(url: str, *, timeout: int = 60) -> str:
    """
    جلب الصفحة مع مهلة 60 ثانية (افتراضيًا).  
    تـُرفع استثناءات requests عند الفشل.
    """
    resp = SESSION.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_visible_text(html: str) -> str:
    """حذف <script> و <style> … إلخ، ثم إرجاع النص النظيف."""
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        bad.decompose()
    return clean_text(soup.get_text(separator="\n"))


