from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from app.services.llm_factory import LLMFactory


class CaptionEnhancer:
    def __init__(self):
        llm = LLMFactory.create()

        # Prompt template for refining captions
        self.prompt = PromptTemplate.from_template(
            "You are an expert in plant pathology. "
            "Improve this image caption by making it more specific and helpful"
            " for identifying plant diseases:\n\n"
            "Original: {caption}\n\nImproved:"
        )

        self.chain = self.prompt | llm | RunnableLambda(lambda x: x.content)

    def enhance(self, caption: str) -> str:
        """
        Enhances the input caption using the configured LLM.

        Args:
            caption (str): The original image caption.

        Returns:
            str: Improved caption.
        """
        return self.chain.invoke({"caption": caption})
