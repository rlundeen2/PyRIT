import json
import logging
import uuid
import pathlib

from pyrit.prompt_converter import PromptConverter
from pyrit.models import PromptTemplate
from pyrit.common.path import DATASETS_PATH
from pyrit.prompt_target import PromptChatTarget
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class VariationConverter(PromptConverter):
    def __init__(self, *, converter_target: PromptChatTarget, prompt_template: PromptTemplate = None):
        self.converter_target = converter_target

        # set to default strategy if not provided
        prompt_template = (
            prompt_template
            if prompt_template
            else PromptTemplate.from_yaml_file(
                pathlib.Path(DATASETS_PATH) / "prompt_converters" / "variation_converter.yaml"
            )
        )

        self.number_variations = 1

        self.system_prompt = str(
            prompt_template.apply_custom_metaprompt_parameters(number_iterations=str(self.number_variations))
        )

        self._conversation_id = str(uuid.uuid4())
        self._normalizer_id = None  # Normalizer not used

        self.converter_target.set_system_prompt(
            prompt=self.system_prompt,
            conversation_id=self._conversation_id,
            normalizer_id=self._normalizer_id,
        )

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def convert(self, prompts: list[str]) -> list[str]:
        """
        Generates variations of the input prompts using the converter target.
        Parameters:
            prompts: list of prompts to convert
        Return:
            target_responses: list of prompt variations generated by the converter target
        """
        all_prompts = []
        for prompt in prompts:
            response_msg = self.converter_target.send_prompt(
                normalized_prompt=prompt,
                conversation_id=self._conversation_id,
                normalizer_id=self._normalizer_id,
            )

            try:
                prompt_variations = json.loads(response_msg)
                for variation in prompt_variations:
                    all_prompts.append(variation)
            except json.JSONDecodeError:
                logger.warning(logging.WARNING, f"could not parse response as JSON {response_msg}")
                raise RuntimeError(f"Error in LLM response {response_msg}")
        return all_prompts

