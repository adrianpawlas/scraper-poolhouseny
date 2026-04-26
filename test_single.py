import asyncio
from scraper import PoolHouseScraper
from embeddings import EmbeddingGenerator
from supabase_client import SupabaseClient
import json


SUPABASE_URL = "https://yqawmzggcgpeyaaynrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxYXdtemdnY2dwZXlhYXlucmprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTAxMDkyNiwiZXhwIjoyMDcwNTg2OTI2fQ.XtLpxausFriraFJeX27ZzsdQsFv3uQKXBBggoz6P4D4"

TEST_URL = "https://poolhousenewyork.com/collections/mens/products/the-tokyo-dad-jeans-copy"


async def main():
    print("Testing single product scrape...")

    scraper = PoolHouseScraper()
    await scraper.init_browser()

    print(f"Scraping: {TEST_URL}")
    product = await scraper.get_product_data(TEST_URL)

    await scraper.close()

    if product:
        print(f"\nTitle: {product.get('title')}")
        print(f"Price: {product.get('price')}")
        print(f"Category: {product.get('category')}")
        print(f"Image URL: {product.get('image_url')}")

        print("\nGenerating embeddings...")
        embedding_gen = EmbeddingGenerator()
        embedding_gen.load_model()

        image_embedding = None
        if product.get("image_url"):
            image_embedding = embedding_gen.get_image_embedding(product["image_url"])
            print(f"Image embedding shape: {image_embedding.shape}")

        info_embedding = embedding_gen.get_info_embedding(product)
        print(f"Info embedding shape: {info_embedding.shape}")

        embedding_gen.close()

        print("\nImporting to Supabase...")
        supabase_client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
        record = supabase_client.prepare_product_record(product, image_embedding, info_embedding)

        success = supabase_client.insert_product(record)
        print(f"Import successful: {success}")

        with open("single_product_test.json", "w") as f:
            json.dump(record, f, indent=2, default=str)
        print("\nData saved to single_product_test.json")

        print("\n=== SUCCESS ===")
    else:
        print("Failed to scrape product")


if __name__ == "__main__":
    asyncio.run(main())