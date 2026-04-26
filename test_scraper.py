import asyncio
from scraper import PoolHouseScraper

async def test():
    scraper = PoolHouseScraper()
    playwright = await scraper.init_browser()
    page = await scraper.context.new_page()

    url = "https://poolhousenewyork.com/collections/mens/products/the-tokyo-dad-jeans-copy"
    print(f"Testing: {url}")

    await page.goto(url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)

    title = await scraper._get_title(page)
    print(f"Title: {title}")

    price = await scraper._get_price(page)
    print(f"Price: {price}")

    sale = await scraper._get_sale_price(page)
    print(f"Sale: {sale}")

    images = await scraper._get_images(page)
    print(f"Images: {len(images)} found")
    if images:
        print(f"First image: {images[0]}")

    description = await scraper._get_description(page)
    print(f"Description: {description[:200] if description else 'None'}...")

    category = await scraper._get_category(page)
    print(f"Category: {category}")

    metadata = await scraper._get_metadata(page)
    print(f"Metadata: {metadata[:200] if metadata else 'None'}...")

    await scraper.browser.close()
    await playwright.stop()

asyncio.run(test())