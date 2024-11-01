# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import re
import uuid

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from jinja2 import Template, StrictUndefined

from pyrit.common.yaml_loadable import YamlLoadable
from pyrit.models.literals import PromptDataType


@dataclass
class SeedPrompt(YamlLoadable):
    """Represents a seed prompt with various attributes and metadata."""

    id: Optional[uuid.UUID]
    template: str
    data_type: PromptDataType
    name: Optional[str]
    dataset_name: Optional[str]
    harm_categories: Optional[List[str]]
    description: Optional[str]
    authors: Optional[List[str]]
    groups: Optional[List[str]]
    source: Optional[str]
    date_added: Optional[datetime]
    added_by: Optional[str]
    metadata: Optional[Dict[str, str]]
    parameters: Optional[List[str]]
    prompt_group_id: Optional[uuid.UUID]
    sequence: Optional[int]

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        template: str,
        data_type: PromptDataType,
        name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        harm_categories: Optional[List[str]] = None,
        description: Optional[str] = None,
        authors: Optional[List[str]] = None,
        groups: Optional[List[str]] = None,
        source: Optional[str] = None,
        date_added: Optional[datetime] = datetime.now(),
        added_by: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        parameters: Optional[List[str]] = None,
        prompt_group_id: Optional[uuid.UUID] = None,
        sequence: Optional[int] = None,
    ):
        self.id = id if id else uuid.uuid4()
        self.template = template
        self.data_type = data_type
        self.name = name
        self.dataset_name = dataset_name
        self.harm_categories = harm_categories or []
        self.description = description
        self.authors = authors or []
        self.groups = groups or []
        self.source = source
        self.date_added = date_added
        self.added_by = added_by
        self.metadata = metadata or {}
        self.parameters = parameters or []
        self.prompt_group_id = prompt_group_id
        self.sequence = sequence

    def render(self, **kwargs) -> str:
        """Gets a value, applying provided parameters in kwargs

        Args:
            kwargs:Key-value pairs to replace in the SeedPrompt value.

        Returns:
            A new prompt with the parameters applied.

        Raises:
            ValueError: If parameters are missing or invalid in the template.
        """


        if self.data_type != "text" and self.parameters:
            raise ValueError(f"Cannot apply parameters to a prompt with data type {self.data_type}")

        jinja_template = Template(self.template, undefined=StrictUndefined)

        try:
            return jinja_template.render(**kwargs)
        except Exception as e:
            raise ValueError(f"Error applying parameters: {str(e)}")


class SeedPromptGroup(YamlLoadable):
    """
    A group of prompts that need to be sent together.

    This class is useful when a target requires multiple (multimodal) prompt pieces to be grouped
    and sent together. All prompts in the group should share the same `prompt_group_id`.
    """

    prompts: List[SeedPrompt]

    def __init__(
        self,
        *,
        prompts: List[SeedPrompt],
    ):
        self.prompts = prompts
        if self.prompts and isinstance(self.prompts[0], dict):
            self.prompts = [SeedPrompt(**prompt_args) for prompt_args in self.prompts]  # type: ignore
        else:
            self.prompts = prompts

        # Check sequence and sort the prompts in the same loop
        if len(self.prompts) >= 1:
            self.prompts = sorted(self.prompts, key=lambda prompt: self._validate_and_get_sequence(prompt))

    def _validate_and_get_sequence(self, prompt: SeedPrompt) -> int:
        """
        Validates the sequence of a prompt and returns it.

        Args:
            prompt (SeedPrompt): The prompt whose sequence needs to be validated.

        Returns:
            int: The sequence number of the prompt.

        Raises:
            ValueError: If the prompt does not have a sequence number.
        """
        if prompt.sequence is None:
            raise ValueError("All prompts in a group must have a sequence number.")
        return prompt.sequence

    def __repr__(self):
        return f"<SeedPromptGroup(prompts={len(self.prompts)} prompts)>"


class SeedPromptDataset(YamlLoadable):
    """SeedPromptDataset class helps to read a list of seed prompts, which can be loaded from a YAML file.
    This class manages individual seed prompts, groups them by `prompt_group_id` if specified,
    and provides structured access to grouped prompt data."""

    prompts: List[SeedPrompt]

    def __init__(self, prompts: List[SeedPrompt]):
        if prompts and isinstance(prompts[0], dict):
            self.prompts = [SeedPrompt(**prompt_args) for prompt_args in prompts]  # type: ignore
        else:
            self.prompts = prompts

    @staticmethod
    def group_seed_prompts_by_prompt_group_id(seed_prompts: List[SeedPrompt]) -> List[SeedPromptGroup]:
        """
        Groups the given list of SeedPrompts by their prompt_group_id and creates
        SeedPromptGroup instances.

        Args:
            seed_prompts: A list of SeedPrompt objects.

        Returns:
            A list of SeedPromptGroup objects, with prompts grouped by prompt_group_id.
        """
        # Group seed prompts by `prompt_group_id`
        grouped_prompts = defaultdict(list)
        for prompt in seed_prompts:
            if prompt.prompt_group_id:
                grouped_prompts[prompt.prompt_group_id].append(prompt)

        # Create SeedPromptGroup instances from grouped prompts
        seed_prompt_groups = []
        for group_prompts in grouped_prompts.values():
            if len(group_prompts) > 1:
                group_prompts.sort(key=lambda prompt: prompt.sequence)

            seed_prompt_group = SeedPromptGroup(prompts=group_prompts)
            seed_prompt_groups.append(seed_prompt_group)

        return seed_prompt_groups

    def __repr__(self):
        return f"<SeedPromptDataset(prompts={len(self.prompts)} prompts)>"
