import asyncio
import os
import json
import argparse
import traceback
import sys

from scraper import PoolHouseScraper
from embeddings import EmbeddingGenerator
from supabase_client import SupabaseClient


SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yqawmzggcgpeyaaynrjk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxYXdtemdnY2dwZXlhYXlucmprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTAxMDkyNiwiZXhwIjoyMDcwNTg2OTI2fQ.XtLpxausFriraFJeX27ZzsdQsFv3uQKXBBggoz6P4D4")


class PoolHouseOrchestrator:
    def __init__(self, limit=0):
        self.scraper = PoolHouseScraper()
        self.embedding_generator = None
        self.supabase_client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
        self.products_data = []
        self.output_file = "products_output.json"
        self.limit = limit

    async def run(self):
        print("=" * 60, flush=True)
        print("Pool House New York Scraper Starting", flush=True)
        print("=" * 60, flush=True)
        sys.stdout.flush()

        try:
            print("\n[1/5] Initializing browser and scraping collection pages...", flush=True)
            sys.stdout.flush()

            product_urls = await self.scraper.scrape_all_collections()
            if self.limit > 0:
                product_urls = product_urls[:self.limit]
            print(f"Found {len(product_urls)} unique product URLs", flush=True)
            sys.stdout.flush()

            print("\n[2/5] Scraping individual product pages...", flush=True)
            sys.stdout.flush()

            for i, url in enumerate(product_urls):
                print(f"  Scraping {i+1}/{len(product_urls)}: {url[:50]}...", flush=True)
                sys.stdout.flush()
                try:
                    product_data = await self.scraper.get_product_data(url)
                    if product_data:
                        self.products_data.append(product_data)
                        print(f"    -> {product_data.get('title', 'Unknown')[:40]}", flush=True)
                except Exception as e:
                    print(f"    -> Error: {str(e)[:50]}", flush=True)
                await asyncio.sleep(0.5)

            print(f"Successfully scraped {len(self.products_data)} products", flush=True)

            with open(self.output_file, "w") as f:
                json.dump(self.products_data, f, indent=2, default=str)
            print(f"Products saved to {self.output_file}", flush=True)

            await self.scraper.close()

            print("\n[3/5] Loading embedding model...", flush=True)
            sys.stdout.flush()
            self.embedding_generator = EmbeddingGenerator()
            self.embedding_generator.load_model()

            print("\n[4/5] Generating embeddings and preparing records...", flush=True)
            sys.stdout.flush()
            records = []
            for i, product in enumerate(self.products_data):
                print(f"  Processing {i+1}/{len(self.products_data)}: {product.get('title', 'Unknown')[:40]}...", flush=True)
                sys.stdout.flush()

                try:
                    image_url = product.get("image_url")
                    image_embedding = None
                    if image_url:
                        image_embedding = self.embedding_generator.get_image_embedding(image_url)

                    info_embedding = self.embedding_generator.get_info_embedding(product)

                    record = self.supabase_client.prepare_product_record(
                        product, image_embedding, info_embedding
                    )
                    records.append(record)
                except Exception as e:
                    print(f"    -> Embedding error: {str(e)[:50]}", flush=True)

            print(f"Prepared {len(records)} records", flush=True)

            print("\n[5/5] Importing to Supabase...", flush=True)
            sys.stdout.flush()
            batch_size = 10
            total_imported = 0
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                result = self.supabase_client.insert_batch(batch)
                if result.get("success"):
                    total_imported += len(batch)
                    print(f"  Imported batch {i//batch_size + 1}: {len(batch)} products", flush=True)
                else:
                    print(f"  Failed batch {i//batch_size + 1}: {result.get('error')}", flush=True)

            print(f"\nTotal imported: {total_imported} products", flush=True)

            final_output = "products_with_embeddings.json"
            with open(final_output, "w") as f:
                json.dump(records, f, indent=2, default=str)
            print(f"Data saved to {final_output}", flush=True)

        except Exception as e:
            print(f"Error in orchestrator: {e}", flush=True)
            traceback.print_exc()
            with open("error_log.txt", "w") as f:
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
        finally:
            if self.embedding_generator:
                self.embedding_generator.close()

        print("\n" + "=" * 60, flush=True)
        print("Scraping Complete!", flush=True)
        print("=" * 60, flush=True)

        return self.products_data


async def main():
    parser = argparse.ArgumentParser(description='Pool House NY Scraper')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of products to scrape')
    args = parser.parse_args()

    orchestrator = PoolHouseOrchestrator(limit=args.limit)
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())