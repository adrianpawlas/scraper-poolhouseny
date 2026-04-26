import numpy as np
from embeddings import EmbeddingGenerator

gen = EmbeddingGenerator()
gen.load_model()

print("Testing image embedding...")
img_emb = gen.get_image_embedding("https://poolhousenewyork.com/cdn/shop/files/shibuya_pleated_jeans_pants_raw_indigo_wide_leg_flare_pants_jeans_made_in_usa_100_cotton_shopify_ksdk_20x_crop_center.jpg")
print(f"Image embedding shape: {img_emb.shape}")
print(f"Image embedding sample: {img_emb[:5]}")

print("\nTesting text embedding...")
text_emb = gen.get_text_embedding("Tokyo Dad Jeans baggy wide leg made in USA denim")
print(f"Text embedding shape: {text_emb.shape}")
print(f"Text embedding sample: {text_emb[:5]}")

print("\nTesting info embedding...")
product_data = {
    "title": "Tokyo Dad Jeans",
    "brand": "Pool House New York",
    "description": "Made in Los Angeles Heavyweight Black Cone Denim",
    "category": "Jeans",
    "price": "199USD",
    "metadata": "100% Cotton, Baggy Fit",
    "gender": "man"
}
info_emb = gen.get_info_embedding(product_data)
print(f"Info embedding shape: {info_emb.shape}")

gen.close()
print("\nAll embedding tests passed!")