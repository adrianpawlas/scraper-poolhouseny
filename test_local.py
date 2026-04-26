import asyncio
from scraper import PoolHouseScraper

async def main():
    scraper = PoolHouseScraper()

    print("Init browser...")
    await scraper.init_browser()
    print("Browser ready")

    page = await scraper.context.new_page()

    print("Loading collection page...")
    url = "https://poolhousenewyork.com/collections/mens"
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    print("Page loaded")

    await asyncio.sleep(2)

    print("Scrolling...")
    product_links = await page.query_selector_all("a[href*='/products/']")
    print(f"Found {len(product_links)} initial links")

    for i in range(5):
        await page.evaluate("window.scrollBy(0, 600)")
        await asyncio.sleep(1.5)
        product_links = await page.query_selector_all("a[href*='/products/']")
        print(f"After scroll {i+1}: {len(product_links)} links")

    urls = []
    seen = set()
    for link in product_links:
        href = await link.get_attribute("href")
        if href and '/products/' in href and 'gift-card' not in href:
            full_url = f"https://poolhousenewyork.com{href}" if not href.startswith('http') else href
            if full_url not in seen:
                seen.add(full_url)
                urls.append(full_url)

    print(f"Total unique product URLs: {len(urls)}")
    print(f"First 5: {urls[:5]}")

    await scraper.close()
    print("Done!")

asyncio.run(main())