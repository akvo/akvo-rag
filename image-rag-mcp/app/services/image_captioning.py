import clip
import torch
from PIL import Image
import logging
import numpy as np

from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    CLIPTokenizer,
    CLIPModel,
)

logger = logging.getLogger(__name__)


class ImageCaptioning:
    """
    Image captioning and embedding service.

    This class:
    - Generates image captions using BLIP.
    - Produces image and text embeddings using CLIP.
    - Optionally fuses image and text embeddings for multimodal search.

    Intended for tasks like:
    - Image search
    - Multimodal RAG (image + text queries)
    - Dataset labeling / enrichment
    """

    def __init__(
        self,
        clip_model_name="ViT-B/32",
        text_clip_model_name="openai/clip-vit-base-patch32",
        blip_model_name="Salesforce/blip-image-captioning-base",
        device=None,
    ):
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info(f"Using device: {self.device}")

        self._load_clip(clip_model_name)
        self._load_text_clip(text_clip_model_name)
        self._load_blip(blip_model_name)

    def _load_clip(self, model_name):
        try:
            self.clip_model, self.preprocess = clip.load(model_name)
            self.clip_model.to(self.device)
            logger.info(f"CLIP model '{model_name}' loaded successfully.")
        except Exception as e:
            logger.exception(f"Failed to load CLIP model '{model_name}': {e}")
            raise

    def _load_text_clip(self, model_name):
        try:
            self.text_clip_model = CLIPModel.from_pretrained(model_name).to(
                self.device
            )
            self.text_clip_tokenizer = CLIPTokenizer.from_pretrained(
                model_name
            )
            logger.info(f"Text CLIP model '{model_name}' loaded successfully.")
        except Exception as e:
            logger.exception(
                f"Failed to load text CLIP model '{model_name}': {e}"
            )
            raise

    def _load_blip(self, model_name):
        try:
            self.blip_processor = BlipProcessor.from_pretrained(model_name)
            self.blip_model = BlipForConditionalGeneration.from_pretrained(
                model_name
            ).to(self.device)
            logger.info(f"BLIP model '{model_name}' loaded successfully.")
        except Exception as e:
            logger.exception(f"Failed to load BLIP model '{model_name}': {e}")
            raise

    def get_image_embedding(self, image_file):
        """Generate CLIP image embedding."""
        try:
            image = Image.open(image_file).convert("RGB")
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                embedding = self.clip_model.encode_image(image_input)
            return embedding[0].cpu().numpy()
        except Exception as e:
            logger.exception(f"Failed to generate image embedding: {e}")
            raise

    def get_text_embedding(self, text):
        """Generate CLIP text embedding."""
        inputs = self.text_clip_tokenizer(
            text, return_tensors="pt", truncation=True
        ).to(self.device)
        with torch.no_grad():
            outputs = self.text_clip_model.get_text_features(**inputs)
        return outputs[0].cpu().numpy()

    def generate_caption(self, image_file, max_new_tokens=50):
        """Generate image caption with BLIP."""
        try:
            image = Image.open(image_file).convert("RGB")
            inputs = self.blip_processor(image, return_tensors="pt").to(
                self.device
            )
            with torch.no_grad():
                out = self.blip_model.generate(
                    **inputs, max_new_tokens=max_new_tokens
                )
            return self.blip_processor.decode(out[0], skip_special_tokens=True)
        except Exception as e:
            logger.exception(f"Failed to generate caption: {e}")
            return "No caption"

    @staticmethod
    def normalize(vec):
        """Normalize a vector to unit length."""
        return vec / np.linalg.norm(vec)

    def get_fused_embedding(
        self, image_file=None, text=None, image_weight=0.5, text_weight=0.5
    ):
        """Generate fused embedding from image and/or text."""
        image_emb = (
            self.normalize(self.get_image_embedding(image_file))
            if image_file
            else None
        )
        text_emb = (
            self.normalize(self.get_text_embedding(text)) if text else None
        )

        if image_emb is not None and text_emb is not None:
            return self.normalize(
                image_weight * image_emb + text_weight * text_emb
            ).tolist()
        elif image_emb is not None:
            return image_emb.tolist()
        elif text_emb is not None:
            return text_emb.tolist()
        else:
            raise ValueError("At least one of image or text must be provided.")
