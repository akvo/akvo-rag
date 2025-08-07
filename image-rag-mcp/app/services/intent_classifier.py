from langchain_core.prompts import PromptTemplate
from app.services.llm_factory import LLMFactory

INTENT_FALLBACK_QUERIES = {
    "diagnosis": "examples of common plant diseases",
    "health_check": "examples of healthy vs unhealthy plant symptoms",
    "prevention": "how to prevent common plant diseases and pests",
    "treatment": "treatment for common plant diseases",
    "generic": "plant disease and pest examples",
}


class IntentClassifier:
    def __init__(self):
        llm = LLMFactory.create()

        self.prompt = PromptTemplate.from_template(
            """
            Classify the following query into one of these categories:
            - diagnosis
            - health_check
            - prevention
            - treatment
            - generic

            Query: {query}
            Category:
            """
        )

        self.chain = self.prompt | llm | (lambda x: x.content.strip().lower())

    def classify(self, query: str) -> str:
        return self.chain.invoke({"query": query})
