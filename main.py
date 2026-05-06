import asyncio
import os
import json
import argparse
import traceback
import sys
import time
from datetime import datetime, timedelta

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
        self.stats = {"new": 0, "updated": 0, "unchanged": 0, "deleted": 0}

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

            print("\n[4/5] Processing products with smart upsert...", flush=True)
            sys.stdout.flush()

            existing_products = self.supabase_client.get_all_products()
            print(f"Found {len(existing_products)} existing products in DB", flush=True)

            processed_urls = set()
            batch_records = []
            batch_size = 50
            retry_count = {}
            max_retries = 3

            for i, product in enumerate(self.products_data):
                print(f"  Processing {i+1}/{len(self.products_data)}: {product.get('title', 'Unknown')[:40]}...", flush=True)
                sys.stdout.flush()

                product_url = product.get("product_url")
                processed_urls.add(product_url)

                existing = existing_products.get(product_url)
                needs_embedding = True
                should_insert = True

                if existing:
                    if self._has_changed(existing, product):
                        self.stats["updated"] += 1
                        print(f"    -> Updated", flush=True)
                    else:
                        self.stats["unchanged"] += 1
                        should_insert = False
                        needs_embedding = False
                        print(f"    -> Unchanged (skipped)", flush=True)
                else:
                    self.stats["new"] += 1
                    print(f"    -> New", flush=True)

                if should_insert:
                    try:
                        image_embedding = None
                        if needs_embedding and product.get("image_url"):
                            image_embedding = self.embedding_generator.get_image_embedding(product["image_url"])
                            await asyncio.sleep(0.5)

                        info_embedding = self.embedding_generator.get_info_embedding(product)
                        if needs_embedding:
                            await asyncio.sleep(0.5)

                        record = self.supabase_client.prepare_product_record(
                            product, image_embedding, info_embedding
                        )

                        batch_records.append(record)

                        if len(batch_records) >= batch_size:
                            success = self._insert_batch(batch_records, retry_count, max_retries)
                            if success:
                                print(f"    -> Inserted batch of {len(batch_records)}", flush=True)
                            batch_records = []

                    except Exception as e:
                        print(f"    -> Error: {str(e)[:50]}", flush=True)

            if batch_records:
                success = self._insert_batch(batch_records, retry_count, max_retries)
                if success:
                    print(f"    -> Inserted final batch of {len(batch_records)}", flush=True)

            print("\n[5/5] Cleaning stale products...", flush=True)
            sys.stdout.flush()
            stale_count = self.supabase_client.cleanup_stale_products(processed_urls, self.stats["deleted"])
            self.stats["deleted"] = stale_count
            print(f"Deleted {stale_count} stale products", flush=True)

            final_output = "products_with_embeddings.json"
            with open(final_output, "w") as f:
                json.dump([r for r in batch_records if r.get("image_embedding")], f, indent=2, default=str)
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
        print(f"\n--- SUMMARY ---", flush=True)
        print(f"New products: {self.stats['new']}", flush=True)
        print(f"Updated: {self.stats['updated']}", flush=True)
        print(f"Unchanged (skipped): {self.stats['unchanged']}", flush=True)
        print(f"Deleted stale: {self.stats['deleted']}", flush=True)
        print("=" * 60, flush=True)

        return self.products_data

    def _has_changed(self, existing: dict, new_product: dict) -> bool:
        if existing.get("title") != new_product.get("title"):
            return True
        if existing.get("price") != new_product.get("price"):
            return True
        if existing.get("sale") != new_product.get("sale"):
            return True
        if existing.get("image_url") != new_product.get("image_url"):
            return True
        if existing.get("additional_images") != new_product.get("additional_images"):
            return True
        if existing.get("description") != new_product.get("description"):
            return True
        if existing.get("metadata") != new_product.get("metadata"):
            return True
        return False

    def _insert_batch(self, batch, retry_count, max_retries):
        batch_key = ",".join([r.get("product_url", "") for r in batch[:3]])
        if batch_key not in retry_count:
            retry_count[batch_key] = 0

        result = self.supabase_client.insert_batch(batch)

        if result.get("success"):
            return True

        retry_count[batch_key] += 1
        if retry_count[batch_key] < max_retries:
            print(f"    -> Batch retry {retry_count[batch_key]}/{max_retries}", flush=True)
            time.sleep(2)
            result = self.supabase_client.insert_batch(batch)
            if result.get("success"):
                return True

        failed_urls = [r.get("product_url") for r in batch]
        with open("failed_products.log", "a") as f:
            f.write(f"Failed batch: {failed_urls}\n")
        print(f"    -> Batch failed after {max_retries} retries", flush=True)
        return False


async def main():
    parser = argparse.ArgumentParser(description='Pool House NY Scraper')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of products to scrape')
    args = parser.parse_args()

    orchestrator = PoolHouseOrchestrator(limit=args.limit)
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())