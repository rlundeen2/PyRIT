# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import pytest
import uuid

from pyrit.models import (
    SeedPrompt,
    SeedPromptTemplate,
    SeedPromptGroup,
    SeedPromptDataset,
)


@pytest.fixture
def seed_prompt_fixture():
    return SeedPrompt(
        value="Test prompt",
        data_type="text",
        name="Test Name",
        dataset_name="Test Dataset",
        harm_categories=["category1", "category2"],
        description="Test Description",
        authors=["Author1"],
        groups=["Group1"],
        source="Test Source",
        added_by="Tester",
        metadata={"key": "value"},
        parameters=["param1"],
        prompt_group_id=uuid.uuid4(),
        sequence=1,
    )


def test_seed_prompt_initialization(seed_prompt_fixture):
    assert isinstance(seed_prompt_fixture.id, uuid.UUID)
    assert seed_prompt_fixture.value == "Test prompt"
    assert seed_prompt_fixture.data_type == "text"
    assert seed_prompt_fixture.parameters == ["param1"]


def test_seed_prompt_to_prompt_template(seed_prompt_fixture):
    template = seed_prompt_fixture.to_prompt_template()
    assert isinstance(template, SeedPromptTemplate)
    assert template.parameters == seed_prompt_fixture.parameters


def test_seed_prompt_template_initialization():
    with pytest.raises(ValueError, match="SeedPromptTemplate must have data_type 'text'."):
        SeedPromptTemplate(
            value="Test Template", data_type="image_path", parameters=["param1"]  # Invalid data_type for template
        )


def test_seed_prompt_template_apply_parameters_success(seed_prompt_fixture):
    seed_prompt_fixture.value = "Test prompt with param1={{ param1 }}"
    template = seed_prompt_fixture.to_prompt_template()
    result = template.apply_parameters(param1="value1")

    # Assert the result is formatted as expected (change expected_output accordingly)
    expected_output = "Test prompt with param1=value1"
    assert result == expected_output


def test_seed_prompt_template_no_match(seed_prompt_fixture):
    seed_prompt_fixture.value = "Test prompt with {{ param1 }}"
    template = seed_prompt_fixture.to_prompt_template()

    with pytest.raises(ValueError, match="Not all parameters were provided."):
        template.apply_parameters(param2="value2")  # Using an invalid param


def test_seed_prompt_template_missing_param(seed_prompt_fixture):
    seed_prompt_fixture.value = "Test prompt with {{ param1 }} and {{ param2 }}"
    seed_prompt_fixture.parameters = ["param1", "param2"]  # Add both parameters
    template = seed_prompt_fixture.to_prompt_template()

    # Attempt to apply only one of the required parameters
    with pytest.raises(ValueError, match="Not all parameters were provided."):
        template.apply_parameters(param1="value1")  # Missing param2


def test_seed_prompt_group_initialization(seed_prompt_fixture):
    group = SeedPromptGroup(prompts=[seed_prompt_fixture])
    assert len(group.prompts) == 1
    assert group.prompts[0].sequence == 1


def test_seed_prompt_group_sequence_validation():
    prompt = SeedPrompt(value="Test prompt", data_type="text")
    with pytest.raises(ValueError, match="All prompts in a group must have a sequence number."):
        SeedPromptGroup(prompts=[prompt])


def test_group_seed_prompts_by_prompt_group_id(seed_prompt_fixture):
    # Grouping two prompts
    prompt_2 = SeedPrompt(
        value="Another prompt", data_type="text", prompt_group_id=seed_prompt_fixture.prompt_group_id, sequence=2
    )

    groups = SeedPromptDataset.group_seed_prompts_by_prompt_group_id([seed_prompt_fixture, prompt_2])
    assert len(groups) == 1
    assert len(groups[0].prompts) == 2
    assert groups[0].prompts[0].sequence < groups[0].prompts[1].sequence


def test_seed_prompt_dataset_initialization(seed_prompt_fixture):
    dataset = SeedPromptDataset(prompts=[seed_prompt_fixture])
    assert len(dataset.prompts) == 1
    assert dataset.prompts[0].value == "Test prompt"
