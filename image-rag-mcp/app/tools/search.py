import logging

from typing import Optional
from app.services.image_captioning import ImageCaptioning
from app.services.query_rephraser import QueryRephraser
from app.services.caption_enhancer import CaptionEnhancer
from app.services.intent_classifier import (
    IntentClassifier,
    INTENT_FALLBACK_QUERIES,
)
from app.services.chroma_vector_store import ChromaVectorStore
from app.services.embedding_factory import EmbeddingsFactory


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
image_captioning = ImageCaptioning()
query_rephraser = QueryRephraser()
caption_enhancer = CaptionEnhancer()
intent_classifier = IntentClassifier()
embedding = EmbeddingsFactory.create()

vector_store = ChromaVectorStore(
    collection_name="pest_disease", embedding_function=embedding
)


def multimodal_search(
    image_file: Optional[bytes] = None,
    text_query: Optional[str] = None,
    top_k: int = 10,
) -> dict:
    """
    Perform multimodal search (image + text) on pest/disease collection.
    Returns top similar results from ChromaDB.
    """
    if not image_file and not text_query:
        raise ValueError(
            "At least one of image_file or text_query must be provided."
        )

    try:
        image_caption = None
        if image_file:
            blip_image_caption = image_captioning.generate_caption(
                image_file=image_file
            )
            image_caption = caption_enhancer.enhance_caption(
                caption=blip_image_caption
            )
            logger.info(f"Image caption: '{image_caption}'")

        if text_query:
            original_query = text_query
            text_query = query_rephraser.rephrase(
                user_input=text_query, image_caption=image_caption
            )
            logger.info(f"Rephrased: '{original_query}' → '{text_query}'")

        intent = intent_classifier.classify(query=text_query)
        logger.info(f"Intent detected: {intent}")

        # Fallback if needed
        if not image_file and intent in INTENT_FALLBACK_QUERIES:
            fallback_query = INTENT_FALLBACK_QUERIES[intent]
            fallback_embedding = image_captioning.get_fused_embedding(
                image_file=None, text=fallback_query, text_weight=1.0
            )
            results = vector_store.similarity_search_by_vector(
                embedding=fallback_embedding,
                k=top_k,
                include=["distances", "metadatas"],
            )

            return {"intent": intent, "results": results}

        # Main search
        query_embedding = image_captioning.get_fused_embedding(
            image_file=image_file,
            text=text_query,
            image_weight=0.9 if image_file else 0.5,
            text_weight=0.1 if image_file else 0.5,
        )
        distance_threshold = 0.1 if image_file else 0.2

        results = vector_store.similarity_search_by_vector(
            embedding=query_embedding,
            k=top_k,
            include=["distances", "metadatas"],
        )
        distances = results["distances"][0]

        if all(d > distance_threshold for d in distances):
            return {
                "warning": "No close matches found",
                "distances": distances,
            }

        return {"intent": intent, "results": results}

    except Exception as e:
        logger.exception("Search failed")
        return {"error": str(e)}
