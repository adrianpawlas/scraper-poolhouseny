import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = "https://poolhousenewyork.com/collections/mens"
        print(f"Testing collection: {url}")

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        # Get page content to understand structure
        content = await page.content()

        # Find product links
        product_links = await page.query_selector_all("a[href*='/products/']")
        print(f"Found {len(product_links)} product links")

        for i, link in enumerate(product_links[:5]):
            href = await link.get_attribute("href")
            print(f"  {i+1}: {href}")

        await browser.close()

asyncio.run(test())