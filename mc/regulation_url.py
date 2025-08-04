from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def scrape_rule_clickable_parts():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://mc.gov.sa/ar/Regulations/Pages/default.aspx")

    # Wait and scroll to ensure all dynamic content is loaded
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    base_url = "https://mc.gov.sa/ar/Regulations/Pages/"
    laws = []

    for a in soup.select("a.rule-clickable-part"):
        href = a.get("href")
        title = a.get_text(strip=True).replace("\n", " ")
        if href and title:
            full_url = base_url + href
            laws.append(f"{full_url} #{title}")

    with open("data/mc_laws.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(laws))

    print(f"✅ Found and saved {len(laws)} laws to mc_laws.txt")

scrape_rule_clickable_parts()