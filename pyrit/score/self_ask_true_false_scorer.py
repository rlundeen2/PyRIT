# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import pathlib
import uuid
import yaml

from dataclasses import dataclass
import enum
from pathlib import Path
from typing import Dict, Union

from pyrit.score import Score, Scorer
from pyrit.models import PromptRequestPiece, PromptRequestResponse, PromptTemplate
from pyrit.prompt_target import PromptChatTarget
from pyrit.common.path import DATASETS_PATH

TRUE_FALSE_QUESIONTS_PATH = pathlib.Path(DATASETS_PATH, "score", "true_false_question").resolve()

class TrueFalseQuestionPaths(enum.Enum):
    CURRENT_EVENTS = Path(TRUE_FALSE_QUESIONTS_PATH, "current_events.yaml").resolve()
    GROUNDED = Path(TRUE_FALSE_QUESIONTS_PATH, "grounded.yaml").resolve()
    PROMPT_INJECTION = Path(TRUE_FALSE_QUESIONTS_PATH, "prompt_injection.yaml").resolve()
    QUESTION_ANSWERING = Path(TRUE_FALSE_QUESIONTS_PATH, "question_answering.yaml").resolve()



class SelfAskTrueFalseScorer(Scorer):
    """A class that represents a self-ask score for scoring.

    """

    def __init__(
        self,
        chat_target: PromptChatTarget,
        true_false_question_path: Path,
    ) -> None:
        self._score_type = "true_false"

        true_false_question_contents = yaml.safe_load(true_false_question_path.read_text(encoding="utf-8"))

        self._category = true_false_question_contents["category"]
        true_category = true_false_question_contents["true_description"]
        false_category = true_false_question_contents["false_description"]

        metadata = true_false_question_contents["metadata"] if "metadata" in true_false_question_contents else ""


        scoring_instructions_template = PromptTemplate.from_yaml_file(
            TRUE_FALSE_QUESIONTS_PATH / "true_false_system_prompt.yaml"
        )

        self._system_prompt = scoring_instructions_template.apply_custom_metaprompt_parameters(
                                true_description=true_category,
                                false_description=false_category,
                                metadata=metadata
                            )

        self._chat_target: PromptChatTarget = chat_target
        self._conversation_id = str(uuid.uuid4())

        self._chat_target.set_system_prompt(
            system_prompt=self._system_prompt,
            conversation_id=self._conversation_id,
            orchestrator_identifier=None,
        )

    async def score(self, request_response: PromptRequestPiece) -> list[Score]:
        """
        Scores the given text using the chat target.

        """

        self.validate(request_response)

        request = PromptRequestResponse(
            [
                PromptRequestPiece(
                    role="user",
                    original_value=request_response.converted_value,
                    conversation_id=self._conversation_id,
                    prompt_target_identifier=self._chat_target.get_identifier(),
                )
            ]
        )

        response = await self._chat_target.send_prompt_async(prompt_request=request)
        response_json = response.request_pieces[0].converted_value

        try:
            parsed_response = json.loads(response_json)


            score = Score(
                score_value=str(parsed_response["value"]),
                score_value_description=parsed_response["description"],
                score_type=self._score_type,
                score_category=self._category,
                score_rationale=parsed_response["rationale"],
                scorer_class_identifier=self.get_identifier(),
                metadata=None,
                prompt_request_response_id=request_response.id,
            )
            return [score]

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from chat target: {response_json}") from e

    def validate(self, request_response: PromptRequestPiece):
        pass