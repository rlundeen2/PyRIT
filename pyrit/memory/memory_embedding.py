# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
from pyrit.embedding.azure_text_embedding import AzureTextEmbedding
from pyrit.interfaces import EmbeddingSupport
from pyrit.memory.memory_models import PromptMemoryEntry, EmbeddingData


class MemoryEmbedding:
    """
    The MemoryEmbedding class is responsible for encoding the memory embeddings.

    Attributes:
        embedding_model (EmbeddingSupport): An instance of a class that supports embedding generation.
    """

    def __init__(self, *, embedding_model: EmbeddingSupport):
        if embedding_model is None:
            raise ValueError("embedding_model must be set.")
        self.embedding_model = embedding_model

    def generate_embedding_memory_data(self, *, chat_memory: PromptMemoryEntry) -> EmbeddingData:
        """
        Generates metadata for a chat memory entry.

        Args:
            chat_memory (ConversationData): The chat memory entry.

        Returns:
            ConversationMemoryEntryMetadata: The generated metadata.
        """
        if chat_memory.converted_prompt_data_type == "text":
            embedding_data = EmbeddingData(
                embedding=self.embedding_model.generate_text_embedding(text=chat_memory.converted_prompt_text)
                .data[0]
                .embedding,
                embedding_type_name=self.embedding_model.__class__.__name__,
                id=chat_memory.id,
            )
            return embedding_data

        raise ValueError("Only text data is supported for embedding.")


def default_memory_embedding_factory(embedding_model: EmbeddingSupport = None) -> MemoryEmbedding | None:
    if embedding_model:
        return MemoryEmbedding(embedding_model=embedding_model)

    api_key = os.environ.get("AZURE_OPENAI_EMBEDDING_KEY")
    api_base = os.environ.get("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    if api_key and api_base and deployment:
        model = AzureTextEmbedding(api_key=api_key, endpoint=api_base, deployment=deployment)
        return MemoryEmbedding(embedding_model=model)
    else:
        return None
