import supabase
from supabase import create_client
import json
import hashlib
from typing import Optional
import numpy as np


class SupabaseClient:
    def __init__(self, url: str, api_key: str):
        self.client = create_client(url, api_key)
        print(f"Connected to Supabase: {url}")

    def generate_product_id(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"phny_{url_hash}"

    def prepare_product_record(self, product_data: dict, image_embedding: np.ndarray, info_embedding: np.ndarray) -> dict:
        record = {
            "id": self.generate_product_id(product_data.get("product_url", "")),
            "source": product_data.get("source", "scraper-poolhouseny"),
            "brand": product_data.get("brand", "Pool House New York"),
            "product_url": product_data.get("product_url"),
            "image_url": product_data.get("image_url"),
            "additional_images": product_data.get("additional_images"),
            "title": product_data.get("title", "Unknown"),
            "description": product_data.get("description"),
            "category": product_data.get("category"),
            "gender": product_data.get("gender", "man"),
            "second_hand": False,
            "metadata": product_data.get("metadata"),
            "price": product_data.get("price"),
            "sale": product_data.get("sale"),
            "created_at": "now()",
            "image_embedding": image_embedding.tolist() if image_embedding is not None else None,
            "info_embedding": info_embedding.tolist() if info_embedding is not None else None,
            "country": "US",
            "tags": []
        }

        return record

    def insert_product(self, record: dict) -> bool:
        try:
            data, count = self.client.table("products").upsert(
                record,
                on_conflict="source,product_url"
            ).execute()
            return True
        except Exception as e:
            print(f"Error inserting product: {e}")
            return False

    def insert_batch(self, records: list) -> dict:
        try:
            data, count = self.client.table("products").upsert(
                records,
                on_conflict="source,product_url"
            ).execute()
            return {"success": True, "count": count}
        except Exception as e:
            print(f"Error inserting batch: {e}")
            return {"success": False, "error": str(e)}

    def get_existing_products(self) -> set:
        try:
            response = self.client.table("products").select("product_url").execute()
            return set(item["product_url"] for item in response.data)
        except Exception as e:
            print(f"Error fetching existing products: {e}")
            return set()

    def delete_product(self, product_url: str) -> bool:
        try:
            self.client.table("products").delete().eq("product_url", product_url).execute()
            return True
        except Exception as e:
            print(f"Error deleting product: {e}")
            return False