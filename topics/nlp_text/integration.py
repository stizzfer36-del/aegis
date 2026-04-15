"""NLP / Text — spaCy / Transformers / LlamaIndex integrations."""
from __future__ import annotations


class NLPTextTopic:
    name = "nlp_text"
    tools = ["spacy", "nltk", "transformers", "langchain", "llamaindex", "haystack", "txtai"]

    def extract_entities(self, text: str) -> list:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
        except (ImportError, OSError):
            return [{"error": "spacy / en_core_web_sm not installed"}]
