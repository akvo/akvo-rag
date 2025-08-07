import os
from tqdm import tqdm
import logging
import hashlib

from app.services.caption_enhancer import CaptionEnhancer
from app.services.image_captioning import ImageCaptioning
from app.services.chroma_vector_store import ChromaVectorStore
from app.services.embedding_factory import EmbeddingsFactory


# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

caption_enhancer = CaptionEnhancer()
image_captioning = ImageCaptioning()
embedding = EmbeddingsFactory.create()

vector_store = ChromaVectorStore(
    collection_name="pest_disease", embedding_function=embedding
)


# --- Dataset path ---
DATA_DIR = "./dataset/pest_disease"


# --- Indexing ---
def generate_image_id(file_path: str) -> str:
    return hashlib.md5(file_path.encode()).hexdigest()


def normalize_label(path: str) -> str:
    # Convert path like "Tomato_Blight-Leaf" -> "tomato blight leaf"
    return path.replace("_", " ").replace("-", " ").lower()


def index_images():
    logger.info(f"📂 Indexing images from: {DATA_DIR}")

    for root, _, files in os.walk(DATA_DIR):
        for file in tqdm(files, desc="Indexing images"):
            if not file.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            file_path = os.path.join(root, file)
            try:
                label = normalize_label(os.path.relpath(root, DATA_DIR))
                shared_id = generate_image_id(file_path=file_path)

                # Delete any previous entries for this image
                vector_store.delete(
                    [
                        f"{shared_id}_img",
                        f"{shared_id}_caption",
                        f"{shared_id}_label",
                        f"{shared_id}_aug",
                    ]
                )

                with open(file_path, "rb") as img_file:
                    embedding_img = image_captioning.get_image_embedding(
                        image_file=img_file
                    )
                    img_file.seek(0)  # rewind file before reusing
                    blip_caption = image_captioning.generate_caption(
                        image_file=img_file
                    )

                # Combine BLIP + label into a better caption
                combined_caption = (
                    f"{blip_caption}. This image shows symptoms of {label}."
                )
                logger.info(f"📝 Combined caption: {combined_caption}")

                # enhance combined caption
                caption = caption_enhancer.enhance(caption=combined_caption)
                logger.info(f"📝 Enhanced caption: {caption}")

                embedding_text = image_captioning.get_text_embedding(
                    text=caption
                )
                # Embedding just the label
                embedding_label = image_captioning.get_text_embedding(
                    text=label
                )
                # Embedding a natural query-style sentence
                augmented_caption = f"Show me an example of {label} disease"
                embedding_augmented = image_captioning.get_text_embedding(
                    text=augmented_caption
                )

                # --- Store image embedding ---
                vector_store.add_embeddings(
                    ids=[f"{shared_id}_img"],
                    embeddings=[embedding_img.tolist()],
                    metadatas=[
                        {
                            "group_id": shared_id,
                            "type": "image",
                            "label": label,
                            "path": file_path,
                            "caption": caption,
                        }
                    ],
                    documents=[""],
                )

                # --- Store caption embedding ---
                vector_store.add_embeddings(
                    ids=[f"{shared_id}_caption"],
                    embeddings=[embedding_text.tolist()],
                    metadatas=[
                        {
                            "group_id": shared_id,
                            "type": "caption",
                            "label": label,
                            "path": file_path,
                            "caption": caption,
                        }
                    ],
                    documents=[caption],
                )

                # --- Store label embedding ---
                vector_store.add_embeddings(
                    ids=[f"{shared_id}_label"],
                    embeddings=[embedding_label.tolist()],
                    metadatas=[
                        {
                            "group_id": shared_id,
                            "type": "label",
                            "label": label,
                            "path": file_path,
                            "caption": caption,
                        }
                    ],
                    documents=[label],
                )

                # --- Store augmented natural sentence embedding ---
                vector_store.add_embeddings(
                    ids=[f"{shared_id}_aug"],
                    embeddings=[embedding_augmented.tolist()],
                    metadatas=[
                        {
                            "group_id": shared_id,
                            "type": "sentence",
                            "label": label,
                            "path": file_path,
                            "caption": caption,
                        }
                    ],
                    documents=[augmented_caption],
                )

                logger.info(f"✅ Indexed: {file_path} [label: {label}]")

            except Exception as e:
                logger.warning(f"⚠️ Failed to process {file_path}: {e}")


if __name__ == "__main__":
    index_images()
    logger.info("🎉 Indexing completed.")
