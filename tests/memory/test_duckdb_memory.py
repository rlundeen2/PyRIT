# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
from typing import Generator
import pytest
import uuid
from unittest.mock import MagicMock

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from sqlalchemy import String, DateTime, INTEGER, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.sqltypes import NullType

from pyrit.memory.memory_interface import MemoryInterface
from pyrit.memory.memory_models import PromptMemoryEntry, EmbeddingData
from pyrit.models import PromptRequestPiece, Score
from pyrit.orchestrator.orchestrator_class import Orchestrator
from pyrit.prompt_converter.base64_converter import Base64Converter
from pyrit.prompt_target.text_target import TextTarget
from tests.mocks import get_memory_interface
from tests.mocks import get_sample_conversation_entries


@pytest.fixture
def memory_interface() -> Generator[MemoryInterface, None, None]:
    yield from get_memory_interface()


@pytest.fixture
def sample_conversation_entries() -> list[PromptMemoryEntry]:
    return get_sample_conversation_entries()


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = MagicMock()
    session.query = MagicMock()
    session.merge = MagicMock()
    session.rollback = MagicMock()
    return session


def test_conversation_data_schema(memory_interface):
    inspector = inspect(memory_interface.engine)
    columns = inspector.get_columns("PromptMemoryEntries")
    column_names = [col["name"] for col in columns]

    # Expected columns in ConversationData
    expected_columns = [
        "id",
        "role",
        "conversation_id",
        "sequence",
        "timestamp",
        "labels",
        "prompt_metadata",
        "converter_identifiers",
        "prompt_target_identifier",
        "original_value_data_type",
        "original_value",
        "original_value_sha256",
        "converted_value_data_type",
        "converted_value",
        "converted_value_sha256",
    ]

    for column in expected_columns:
        assert column in column_names, f"{column} not found in PromptMemoryEntries schema."


def test_embedding_data_schema(memory_interface):
    inspector = inspect(memory_interface.engine)
    columns = inspector.get_columns("EmbeddingData")
    column_names = [col["name"] for col in columns]

    # Expected columns in EmbeddingData
    expected_columns = ["id", "embedding", "embedding_type_name"]
    for column in expected_columns:
        assert column in column_names, f"{column} not found in EmbeddingData schema."


def test_conversation_data_column_types(memory_interface):
    inspector = inspect(memory_interface.engine)
    columns = inspector.get_columns("PromptMemoryEntries")
    column_types = {col["name"]: type(col["type"]) for col in columns}

    # Expected column types in ConversationData
    expected_column_types = {
        "id": UUID,
        "role": String,
        "conversation_id": String,
        "sequence": INTEGER,
        "timestamp": DateTime,
        "labels": String,
        "prompt_metadata": String,
        "converter_identifiers": String,
        "prompt_target_identifier": String,
        "original_value_data_type": String,
        "original_value": String,
        "original_value_sha256": String,
        "converted_value_data_type": String,
        "converted_value": String,
        "converted_value_sha256": String,
    }

    for column, expected_type in expected_column_types.items():
        if column != "labels":
            assert column in column_types, f"{column} not found in PromptMemoryEntries schema."
            assert issubclass(
                column_types[column], expected_type
            ), f"Expected {column} to be a subclass of {expected_type}, got {column_types[column]} instead."


def test_embedding_data_column_types(memory_interface):
    inspector = inspect(memory_interface.engine)
    columns = inspector.get_columns("EmbeddingData")
    column_types = {col["name"]: col["type"].__class__ for col in columns}

    # Expected column types in EmbeddingData
    expected_column_types = {
        "id": UUID,
        "embedding": ARRAY,
        "embedding_type_name": String,
    }

    for column, expected_type in expected_column_types.items():
        if column != "embedding":
            assert column in column_types, f"{column} not found in EmbeddingStore schema."
            # Allow for flexibility in type representation (String vs. VARCHAR)
            assert issubclass(
                column_types[column], expected_type
            ), f"Expected {column} to be a subclass of {expected_type}, got {column_types[column]} instead."
    # Handle 'embedding' column separately
    assert "embedding" in column_types, "'embedding' column not found in EmbeddingData schema."
    # Check if 'embedding' column type is either NullType (due to reflection issue) or ARRAY
    assert column_types["embedding"] in [
        NullType,
        ARRAY,
    ], f"Unexpected type for 'embedding' column: {column_types['embedding']}"


def test_insert_entry(memory_interface):
    session = memory_interface.get_session()
    entry = PromptMemoryEntry(
        entry=PromptRequestPiece(
            id=uuid.uuid4(),
            conversation_id="123",
            role="user",
            original_value_data_type="text",
            original_value="Hello",
            converted_value="Hello",
        )
    )
    # Use the _insert_entry method to insert the entry into the database
    memory_interface._insert_entry(entry)

    # Now, get a new session to query the database and verify the entry was inserted
    with memory_interface.get_session() as session:
        inserted_entry = session.query(PromptMemoryEntry).filter_by(conversation_id="123").first()
        assert inserted_entry is not None
        assert inserted_entry.role == "user"
        assert inserted_entry.original_value == "Hello"
        sha265 = "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"
        assert inserted_entry.original_value_sha256 == sha265


def test_insert_entry_violates_constraint(memory_interface):
    # Generate a fixed UUID
    fixed_uuid = uuid.uuid4()
    # Create two entries with the same UUID
    entry1 = PromptMemoryEntry(
        entry=PromptRequestPiece(
            id=fixed_uuid,
            conversation_id="123",
            role="user",
            original_value="Hello",
            converted_value="Hello",
        )
    )

    entry2 = PromptMemoryEntry(
        entry=PromptRequestPiece(
            id=fixed_uuid,
            conversation_id="456",
            role="user",
            original_value="Hello again",
            converted_value="Hello again",
        )
    )

    # Insert the first entry
    with memory_interface.get_session() as session:
        session.add(entry1)
        session.commit()

    # Attempt to insert the second entry with the same UUID
    with memory_interface.get_session() as session:
        session.add(entry2)
        with pytest.raises(SQLAlchemyError):
            session.commit()


def test_insert_entries(memory_interface):
    entries = [
        PromptMemoryEntry(
            entry=PromptRequestPiece(
                conversation_id=str(i),
                role="user",
                original_value=f"Message {i}",
                converted_value=f"CMessage {i}",
            )
        )
        for i in range(5)
    ]

    # Now, get a new session to query the database and verify the entries were inserted
    with memory_interface.get_session() as session:
        # Use the _insert_entries method to insert multiple entries into the database
        memory_interface._insert_entries(entries=entries)
        inserted_entries = session.query(PromptMemoryEntry).all()
        assert len(inserted_entries) == 5
        for i, entry in enumerate(inserted_entries):
            assert entry.conversation_id == str(i)
            assert entry.role == "user"
            assert entry.original_value == f"Message {i}"
            assert entry.converted_value == f"CMessage {i}"


def test_insert_embedding_entry(memory_interface):
    # Create a ConversationData entry
    conversation_entry = PromptMemoryEntry(
        entry=PromptRequestPiece(conversation_id="123", role="user", original_value="Hello", converted_value="abc")
    )

    # Insert the ConversationData entry using the _insert_entry method
    memory_interface._insert_entry(conversation_entry)

    # Re-query the ConversationData entry within a new session to ensure it's attached
    with memory_interface.get_session() as session:
        # Assuming uuid is the primary key and is set upon insertion
        reattached_conversation_entry = session.query(PromptMemoryEntry).filter_by(conversation_id="123").one()
        uuid = reattached_conversation_entry.id

    # Now that we have the uuid, we can create and insert the EmbeddingData entry
    embedding_entry = EmbeddingData(id=uuid, embedding=[1, 2, 3], embedding_type_name="test_type")
    memory_interface._insert_entry(embedding_entry)

    # Verify the EmbeddingData entry was inserted correctly
    with memory_interface.get_session() as session:
        persisted_embedding_entry = session.query(EmbeddingData).filter_by(id=uuid).first()
        assert persisted_embedding_entry is not None
        assert persisted_embedding_entry.embedding == [1, 2, 3]
        assert persisted_embedding_entry.embedding_type_name == "test_type"


def test_disable_embedding(memory_interface):
    memory_interface.disable_embedding()

    assert (
        memory_interface.memory_embedding is None
    ), "disable_memory flag was passed, so memory embedding should be disabled."


def test_default_enable_embedding(memory_interface):
    os.environ["AZURE_OPENAI_EMBEDDING_KEY"] = "mock_key"
    os.environ["AZURE_OPENAI_EMBEDDING_ENDPOINT"] = "embedding"
    os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] = "deployment"

    memory_interface.enable_embedding()

    assert (
        memory_interface.memory_embedding is not None
    ), "Memory embedding should be enabled when set with environment variables."


def test_default_embedding_raises(memory_interface):
    os.environ["AZURE_OPENAI_EMBEDDING_KEY"] = ""
    os.environ["AZURE_OPENAI_EMBEDDING_ENDPOINT"] = ""
    os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] = ""

    with pytest.raises(ValueError):
        memory_interface.enable_embedding()


def test_query_entries(memory_interface, sample_conversation_entries):

    for i in range(3):
        sample_conversation_entries[i].conversation_id = str(i)
        sample_conversation_entries[i].original_value = f"Message {i}"
        sample_conversation_entries[i].converted_value = f"Message {i}"

    memory_interface._insert_entries(entries=sample_conversation_entries)

    # Query entries without conditions
    queried_entries = memory_interface.query_entries(PromptMemoryEntry)
    assert len(queried_entries) == 3

    # Query entries with a condition
    specific_entry = memory_interface.query_entries(
        PromptMemoryEntry, conditions=PromptMemoryEntry.conversation_id == "1"
    )
    assert len(specific_entry) == 1
    assert specific_entry[0].original_value == "Message 1"


def test_update_entries(memory_interface):
    # Insert a test entry
    entry = PromptMemoryEntry(
        entry=PromptRequestPiece(conversation_id="123", role="user", original_value="Hello", converted_value="Hello")
    )

    memory_interface._insert_entry(entry)

    # Fetch the entry to update and update its content
    entries_to_update = memory_interface.query_entries(
        PromptMemoryEntry, conditions=PromptMemoryEntry.conversation_id == "123"
    )
    memory_interface.update_entries(entries=entries_to_update, update_fields={"original_value": "Updated Hello"})

    # Verify the entry was updated
    with memory_interface.get_session() as session:
        updated_entry = session.query(PromptMemoryEntry).filter_by(conversation_id="123").first()
        assert updated_entry.original_value == "Updated Hello"


def test_get_all_memory(memory_interface, sample_conversation_entries):

    memory_interface._insert_entries(entries=sample_conversation_entries)

    # Fetch all entries
    all_entries = memory_interface.get_all_prompt_pieces()
    assert len(all_entries) == 3


def test_get_memories_with_json_properties(memory_interface):
    # Define a specific conversation_id
    specific_conversation_id = "test_conversation_id"

    converter_identifiers = [Base64Converter().get_identifier()]
    target = TextTarget()

    # Start a session
    with memory_interface.get_session() as session:
        # Create a ConversationData entry with all attributes filled
        entry = PromptMemoryEntry(
            entry=PromptRequestPiece(
                conversation_id=specific_conversation_id,
                role="user",
                sequence=1,
                original_value="Test content",
                converted_value="Test content",
                labels={"normalizer_id": "id1"},
                converter_identifiers=converter_identifiers,
                prompt_target_identifier=target.get_identifier(),
            )
        )

        # Insert the ConversationData entry
        session.add(entry)
        session.commit()

        # Use the get_memories_with_conversation_id method to retrieve entries with the specific conversation_id
        retrieved_entries = memory_interface.get_conversation(conversation_id=specific_conversation_id)

        # Verify that the retrieved entry matches the inserted entry
        assert len(retrieved_entries) == 1
        retrieved_entry = retrieved_entries[0].request_pieces[0]
        assert retrieved_entry.conversation_id == specific_conversation_id
        assert retrieved_entry.role == "user"
        assert retrieved_entry.original_value == "Test content"
        # For timestamp, you might want to check if it's close to the current time instead of an exact match
        assert abs((retrieved_entry.timestamp - entry.timestamp).total_seconds()) < 10  # Assuming the test runs quickly

        converter_identifiers = retrieved_entry.converter_identifiers
        assert len(converter_identifiers) == 1
        assert converter_identifiers[0]["__type__"] == "Base64Converter"

        prompt_target = retrieved_entry.prompt_target_identifier
        assert prompt_target["__type__"] == "TextTarget"

        labels = retrieved_entry.labels
        assert labels["normalizer_id"] == "id1"


def test_get_memories_with_orchestrator_id(memory_interface: MemoryInterface):
    # Define a specific normalizer_id
    orchestrator1 = Orchestrator()
    orchestrator2 = Orchestrator()

    # Create a list of ConversationData entries, some with the specific normalizer_id
    entries = [
        PromptMemoryEntry(
            entry=PromptRequestPiece(
                conversation_id="123",
                role="user",
                original_value="Hello 1",
                converted_value="Hello 1",
                orchestrator_identifier=orchestrator1.get_identifier(),
            )
        ),
        PromptMemoryEntry(
            entry=PromptRequestPiece(
                conversation_id="456",
                role="user",
                original_value="Hello 2",
                converted_value="Hello 2",
                orchestrator_identifier=orchestrator2.get_identifier(),
            )
        ),
        PromptMemoryEntry(
            entry=PromptRequestPiece(
                conversation_id="789",
                role="user",
                original_value="Hello 3",
                converted_value="Hello 1",
                orchestrator_identifier=orchestrator1.get_identifier(),
            )
        ),
    ]

    # Insert the ConversationData entries using the _insert_entries method within a session
    with memory_interface.get_session() as session:
        memory_interface._insert_entries(entries=entries)
        session.commit()  # Ensure all entries are committed to the database

        orchestrator1_id = orchestrator1.get_identifier()["id"]

        # Use the get_memories_with_normalizer_id method to retrieve entries with the specific normalizer_id
        retrieved_entries = memory_interface.get_prompt_request_piece_by_orchestrator_id(
            orchestrator_id=orchestrator1_id
        )

        # Verify that the retrieved entries match the expected normalizer_id
        assert len(retrieved_entries) == 2  # Two entries should have the specific normalizer_id
        for retrieved_entry in retrieved_entries:
            assert retrieved_entry.orchestrator_identifier["id"] == str(orchestrator1_id)
            assert "Hello" in retrieved_entry.original_value  # Basic check to ensure content is as expected


def test_update_entries_by_conversation_id(memory_interface, sample_conversation_entries):
    # Define a specific conversation_id to update
    specific_conversation_id = "update_test_id"

    sample_conversation_entries[0].conversation_id = specific_conversation_id
    sample_conversation_entries[2].conversation_id = specific_conversation_id

    sample_conversation_entries[1].conversation_id = "other_id"
    original_content = sample_conversation_entries[1].original_value

    # Insert the ConversationData entries using the _insert_entries method within a session
    with memory_interface.get_session() as session:
        memory_interface._insert_entries(entries=sample_conversation_entries)
        session.commit()  # Ensure all entries are committed to the database

        # Define the fields to update for entries with the specific conversation_id
        update_fields = {"original_value": "Updated content", "role": "assistant"}

        # Use the update_entries_by_conversation_id method to update the entries
        update_result = memory_interface.update_entries_by_conversation_id(
            conversation_id=specific_conversation_id, update_fields=update_fields
        )

        assert update_result is True  # Ensure the update operation was reported as successful

        # Verify that the entries with the specific conversation_id were updated
        updated_entries = memory_interface.query_entries(
            PromptMemoryEntry, conditions=PromptMemoryEntry.conversation_id == specific_conversation_id
        )
        for entry in updated_entries:
            assert entry.original_value == "Updated content"
            assert entry.role == "assistant"

        # Verify that the entry with a different conversation_id was not updated
        other_entry = session.query(PromptMemoryEntry).filter_by(conversation_id="other_id").first()
        assert other_entry.original_value == original_content  # Content should remain unchanged


@pytest.mark.parametrize("score_type", ["float_scale", "true_false"])
def test_add_score_get_score(memory_interface, sample_conversation_entries, score_type):
    prompt_id = sample_conversation_entries[0].id

    memory_interface._insert_entries(entries=sample_conversation_entries)

    score_value = str(True) if score_type == "true_false" else "0.8"

    score = Score(
        score_value=score_value,
        score_value_description="High score",
        score_type=score_type,
        score_category="test",
        score_rationale="Test score",
        score_metadata="Test metadata",
        scorer_class_identifier={"__type__": "TestScorer"},
        prompt_request_response_id=prompt_id,
    )

    memory_interface.add_scores_to_memory(scores=[score])

    # Fetch the score we just added
    db_score = memory_interface.get_scores_by_prompt_ids(prompt_request_response_ids=[prompt_id])
    assert db_score
    assert len(db_score) == 1
    assert db_score[0].score_value == score_value
    assert db_score[0].score_value_description == "High score"
    assert db_score[0].score_type == score_type
    assert db_score[0].score_category == "test"
    assert db_score[0].score_rationale == "Test score"
    assert db_score[0].score_metadata == "Test metadata"
    assert db_score[0].scorer_class_identifier == {"__type__": "TestScorer"}
    assert db_score[0].prompt_request_response_id == prompt_id
