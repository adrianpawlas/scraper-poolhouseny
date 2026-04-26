import asyncio
from scraper import PoolHouseScraper

async def main():
    scraper = PoolHouseScraper()
    await scraper.init_browser()

    url = "https://poolhousenewyork.com/collections/mens/products/the-tokyo-dad-jeans-copy"
    print(f"Testing: {url}")

    product = await scraper.get_product_data(url)

    if product:
        print("\n--- Product Data ---")
        print(f"Title: {product.get('title')}")
        print(f"Price: {product.get('price')}")
        print(f"Sale: {product.get('sale')}")
        print(f"Category: {product.get('category')}")
        print(f"Image URL: {product.get('image_url')}")
        print(f"Additional Images: {product.get('additional_images')}")
        print(f"Description: {product.get('description')[:200] if product.get('description') else 'None'}...")
        print(f"Metadata: {product.get('metadata')[:200] if product.get('metadata') else 'None'}...")
    else:
        print("Failed to scrape product")

    await scraper.close()

asyncio.run(main())