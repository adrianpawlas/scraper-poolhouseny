import asyncio
from playwright.async_api import async_playwright

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            print("Loading collection page...")
            response = await page.goto("https://poolhousenewyork.com/collections/mens", timeout=90000, wait_until="domcontentloaded")
            print(f"Response status: {response.status}")

            print("Waiting a bit for content...")
            await asyncio.sleep(10)

            print(f"Page title: {await page.title()}")

            product_links = await page.query_selector_all("a[href*='/products/']")
            print(f"Found {len(product_links)} product links")

            for i, link in enumerate(product_links[:10]):
                href = await link.get_attribute("href")
                print(f"  {i+1}: {href}")

            # Now try scrolling
            print("\nScrolling...")
            for _ in range(10):
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(2)

                product_links = await page.query_selector_all("a[href*='/products/']")
                print(f"After scroll: {len(product_links)} product links")

            await browser.close()
            print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())