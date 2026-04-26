import torch
import numpy as np
from typing import Union, List
from PIL import Image
import requests
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor


class EmbeddingGenerator:
    def __init__(self, model_name: str = "google/siglip-base-patch16-384"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.executor = ThreadPoolExecutor(max_workers=4)

    def load_model(self):
        from transformers import AutoModel, AutoProcessor

        print(f"Loading model: {self.model_name}")
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()
        print(f"Model loaded on {self.device}")

    def get_image_embedding(self, image_url: str) -> np.ndarray:
        if not self.model:
            self.load_model()

        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")

            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)

            if hasattr(outputs, 'pooler_output'):
                embedding = outputs.pooler_output.cpu().numpy().flatten()
            elif hasattr(outputs, 'last_hidden_state'):
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
            else:
                embedding = outputs.cpu().numpy().flatten()

            return embedding

        except Exception as e:
            print(f"Error generating image embedding for {image_url}: {e}")
            return np.zeros(768)

    def get_text_embedding(self, text: str) -> np.ndarray:
        if not self.model:
            self.load_model()

        try:
            inputs = self.processor(text=text, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.get_text_features(**inputs)

            if hasattr(outputs, 'pooler_output'):
                embedding = outputs.pooler_output.cpu().numpy().flatten()
            elif hasattr(outputs, 'last_hidden_state'):
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
            else:
                embedding = outputs.cpu().numpy().flatten()

            return embedding

        except Exception as e:
            print(f"Error generating text embedding: {e}")
            return np.zeros(768)

    def get_info_embedding(self, product_data: dict) -> np.ndarray:
        text_parts = []

        if product_data.get("title"):
            text_parts.append(product_data["title"])
        if product_data.get("brand"):
            text_parts.append(product_data["brand"])
        if product_data.get("description"):
            text_parts.append(product_data["description"])
        if product_data.get("category"):
            text_parts.append(product_data["category"])
        if product_data.get("price"):
            text_parts.append(product_data["price"])
        if product_data.get("metadata"):
            text_parts.append(product_data["metadata"])
        if product_data.get("gender"):
            text_parts.append(product_data["gender"])

        combined_text = " ".join(text_parts)
        return self.get_text_embedding(combined_text)

    def batch_generate_image_embeddings(self, image_urls: List[str]) -> List[np.ndarray]:
        embeddings = []
        for url in image_urls:
            emb = self.get_image_embedding(url)
            embeddings.append(emb)
        return embeddings

    def close(self):
        if self.executor:
            self.executor.shutdown(wait=False)