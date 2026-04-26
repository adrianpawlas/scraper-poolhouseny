import asyncio
from playwright.async_api import async_playwright

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            url = "https://poolhousenewyork.com/collections/mens/products/the-tokyo-dad-jeans-copy"
            print(f"Loading: {url}")

            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            print(f"Title: {await page.title()}")

            # Try different selectors for title
            title = await page.query_selector("h1")
            if title:
                print(f"H1: {await title.inner_text()}")

            # Try to find price
            price_el = await page.query_selector(".price")
            if price_el:
                print(f"Price element: {await price_el.inner_text()}")

            # Try product form
            product_form = await page.query_selector(".product-form")
            if product_form:
                print("Found product form")

            # Get all text content
            content = await page.content()
            print(f"Page length: {len(content)} chars")

            await browser.close()
            print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())