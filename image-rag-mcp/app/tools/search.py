import json
import base64
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


async def multimodal_search(
    image_file: Optional[bytes] = None,
    text_query: Optional[str] = None,
    top_k: int = 10,
):
    try:
        if not image_file and not text_query:
            return {"context": None, "note": "No input provided"}

        image_caption = None
        if image_file:
            blip_caption = image_captioning.generate_caption(
                image_file=image_file
            )
            image_caption = caption_enhancer.enhance_caption(blip_caption)
            logger.info(f"Image caption: '{image_caption}'")

        if text_query:
            text_query = query_rephraser.rephrase(
                user_input=text_query, image_caption=image_caption
            )
            logger.info(f"Rephrased query: '{text_query}'")

        intent = intent_classifier.classify(query=text_query)
        logger.info(f"Detected intent: {intent}")

        # Fallback query
        if not image_file and intent in INTENT_FALLBACK_QUERIES:
            fallback_query = INTENT_FALLBACK_QUERIES[intent]
            query_embedding = image_captioning.get_fused_embedding(
                image_file=None, text=fallback_query, text_weight=1.0
            )
        else:
            query_embedding = image_captioning.get_fused_embedding(
                image_file=image_file,
                text=text_query,
                image_weight=0.9 if image_file else 0.5,
                text_weight=0.1 if image_file else 0.5,
            )

        # Vector search
        results = vector_store.similarity_search_by_vector(
            embedding=query_embedding, k=top_k, include=["metadatas"]
        )

        # Encode context
        serializable_context = [
            {"page_content": m.get("description", ""), "metadata": m}
            for m in results["metadatas"][0]
        ]

        base64_context = base64.b64encode(
            json.dumps({"context": serializable_context}).encode()
        ).decode()

        return {"context": base64_context}

    except Exception as e:
        logger.exception("Image RAG search failed")
        return {"context": None, "note": f"Error: {str(e)}"}
