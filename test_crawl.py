"""
Test script to verify web crawling functionality
"""
from agents.web_scraper import get_web_scraper_agent

# Test URL
test_url = "https://www.akbankinvestorrelations.com/tr/"

# Get the scraper agent
scraper = get_web_scraper_agent()

print("=" * 80)
print("TEST 1: SCRAPE MODE (Single Page Only)")
print("=" * 80)
result_scrape = scraper(
    question="Akbank'ın sürdürülebilirlik hedefleri nelerdir?",
    manual_urls=[test_url],
    use_crawl=False  # Only scrape the main page
)
print(result_scrape)

print("\n\n")
print("=" * 80)
print("TEST 2: CRAWL MODE (Multiple Pages)")
print("=" * 80)
result_crawl = scraper(
    question="Akbank'ın sürdürülebilirlik hedefleri nelerdir?",
    manual_urls=[test_url],
    use_crawl=True,  # Crawl sub-pages
    max_depth=2,
    limit=5  # Limit to 5 pages for testing
)
print(result_crawl)
