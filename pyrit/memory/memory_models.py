# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import uuid

from typing import Dict

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, DateTime, Float, JSON, ForeignKey, Index, INTEGER, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

from pyrit.models.models import ChatMessageRole
from pyrit.models import PromptRequestPiece, PromptDataType


Base = declarative_base()


class PromptMemoryEntry(Base):  # type: ignore
    """
    Represents the prompt data.

    Because of the nature of database and sql alchemy, type ignores are abundant :)

    Attributes:
        __tablename__ (str): The name of the database table.
        __table_args__ (dict): Additional arguments for the database table.
        id (UUID): The unique identifier for the memory entry.
        role (PromptType): system, assistant, user
        conversation_id (str): The identifier for the conversation which is associated with a single target.
        sequence (int): The order of the conversation within a conversation_id.
            Can be the same number for multi-part requests or multi-part responses.
        timestamp (DateTime): The timestamp of the memory entry.
        labels (Dict[str, str]): The labels associated with the memory entry. Several can be standardized.
        prompt_metadata (JSON): The metadata associated with the prompt. This can be specific to any scenarios.
            Because memory is how components talk with each other, this can be component specific.
            e.g. the URI from a file uploaded to a blob store, or a document type you want to upload.
        converters (list[PromptConverter]): The converters for the prompt.
        prompt_target (PromptTarget): The target for the prompt.
        orchestrator (Orchestrator): The orchestrator for the prompt.
        original_prompt_data_type (PromptDataType): The data type of the original prompt (text, image)
        original_prompt_text (str): The text of the original prompt. If prompt is an image, it's a link.
        original_prompt_data_sha256 (str): The SHA256 hash of the original prompt data.
        converted_prompt_data_type (PromptDataType): The data type of the converted prompt (text, image)
        converted_prompt_text (str): The text of the converted prompt. If prompt is an image, it's a link.
        converted_prompt_data_sha256 (str): The SHA256 hash of the original prompt data.
        idx_conversation_id (Index): The index for the conversation ID.

    Methods:
        __str__(): Returns a string representation of the memory entry.
    """

    __tablename__ = "PromptMemoryEntries"
    __table_args__ = {"extend_existing": True}
    id = Column(UUID(as_uuid=True), nullable=False, primary_key=True)
    role: "Column[ChatMessageRole]" = Column(String, nullable=False)  # type: ignore # noqa
    conversation_id = Column(String, nullable=False)
    sequence = Column(INTEGER, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    labels: Column[Dict[str, str]] = Column(JSON)  # type: ignore
    prompt_metadata = Column(JSON)
    converters: "Column[list[PromptConverter]]" = Column(JSON)  # type: ignore # noqa
    prompt_target: "Column[PromptTarget]" = Column(JSON)  # type: ignore # noqa
    orchestrator: "Column[Orchestrator]" = Column(JSON)  # type: ignore # noqa
    response_error: str = Column(String, nullable=True)

    original_prompt_data_type: PromptDataType = Column(String, nullable=False)  # type: ignore
    original_prompt_text = Column(String, nullable=False)
    original_prompt_data_sha256 = Column(String)

    converted_prompt_data_type: PromptDataType = Column(String, nullable=False)  # type: ignore
    converted_prompt_text = Column(String)
    converted_prompt_data_sha256 = Column(String)

    idx_conversation_id = Index("idx_conversation_id", "conversation_id")

    def __init__(self, *, entry: PromptRequestPiece):
        self._entry = entry

        self.id = entry.id
        self.role = entry.role
        self.conversation_id = entry.conversation_id
        self.sequence = entry.sequence
        self.timestamp = entry.timestamp
        self.labels = entry.labels
        self.prompt_metadata = entry.prompt_metadata
        self.converters = entry.converters
        self.prompt_target = entry.prompt_target
        self.orchestrator = entry.orchestrator

        self.original_prompt_text = entry.original_prompt_text
        self.original_prompt_data_type = entry.original_prompt_data_type
        self.original_prompt_data_sha256 = entry.original_prompt_data_sha256

        self.converted_prompt_data_type = entry.converted_prompt_data_type
        self.converted_prompt_text = entry.converted_prompt_text
        self.converted_prompt_data_sha256 = entry.converted_prompt_data_sha256

        self.response_error = entry.response_error

    def get_prompt_reqest_piece(self) -> PromptRequestPiece:
        return self._entry

    def __str__(self):
        return str(self._entry)


class EmbeddingData(Base):  # type: ignore
    """
    Represents the embedding data associated with conversation entries in the database.
    Each embedding is linked to a specific conversation entry via an id

    Attributes:
        uuid (UUID): The primary key, which is a foreign key referencing the UUID in the MemoryEntries table.
        embedding (ARRAY(Float)): An array of floats representing the embedding vector.
        embedding_type_name (String): The name or type of the embedding, indicating the model or method used.
    """

    __tablename__ = "EmbeddingData"
    # Allows table redefinition if already defined.
    __table_args__ = {"extend_existing": True}
    id = Column(UUID(as_uuid=True), ForeignKey(f"{PromptMemoryEntry.__tablename__}.id"), primary_key=True)
    embedding = Column(ARRAY(Float))
    embedding_type_name = Column(String)

    def __str__(self):
        return f"{self.id}"


class ConversationMessageWithSimilarity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    content: str
    metric: str
    score: float = 0.0


class EmbeddingMessageWithSimilarity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uuid: uuid.UUID
    metric: str
    score: float = 0.0
