import os
import clip

from pathlib import Path
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    CLIPTokenizer,
    CLIPModel,
)

CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", "/app/models"))


def download_clip(model_name="ViT-B/32"):
    print(f"Downloading CLIP image model: {model_name}")
    clip.load(model_name, download_root=str(CACHE_DIR))


def download_text_clip(model_name="openai/clip-vit-base-patch32"):
    print(f"Downloading Text CLIP model: {model_name}")
    CLIPModel.from_pretrained(model_name, cache_dir=CACHE_DIR)
    CLIPTokenizer.from_pretrained(model_name, cache_dir=CACHE_DIR)


def download_blip(model_name="Salesforce/blip-image-captioning-base"):
    print(f"Downloading BLIP model: {model_name}")
    BlipProcessor.from_pretrained(model_name, cache_dir=CACHE_DIR)
    BlipForConditionalGeneration.from_pretrained(
        model_name, cache_dir=CACHE_DIR
    )


if __name__ == "__main__":
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    download_clip()
    download_text_clip()
    download_blip()

    print("✅ All models downloaded to", CACHE_DIR)
