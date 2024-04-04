import json
import logging
import uuid
import pathlib

from pyrit.memory.memory_models import PromptDataType
from pyrit.prompt_converter import PromptConverter
from pyrit.models import PromptTemplate
from pyrit.common.path import DATASETS_PATH
from pyrit.prompt_target import PromptChatTarget
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class TranslationConverter(PromptConverter):
    def __init__(
        self, *, converter_target: PromptChatTarget, language: str, prompt_template: PromptTemplate = None
    ):
        """
        Initializes a TranslationConverter object.

        Args:
            converter_target (PromptChatTarget): The target chat support for the conversion which will translate
            language (str): The language for the conversion. E.g. Spanish, French, leetspeak, etc.
            prompt_template (PromptTemplate, optional): The prompt template for the conversion.

        Raises:
            ValueError: If the language is not provided.
        """
        self.converter_target = converter_target

        # set to default strategy if not provided
        prompt_template = (
            prompt_template
            if prompt_template
            else PromptTemplate.from_yaml_file(
                pathlib.Path(DATASETS_PATH) / "prompt_converters" / "translation_converter.yaml"
            )
        )

        if not language:
            raise ValueError("Language must be provided for translation conversion")

        self.language = language

        self.system_prompt = prompt_template.apply_custom_metaprompt_parameters(languages=language)

        self._conversation_id = str(uuid.uuid4())
        self._normalizer_id = None  # Normalizer not used

        self.converter_target.set_system_prompt(
            prompt=self.system_prompt,
            conversation_id=self._conversation_id,
            normalizer_id=self._normalizer_id,
        )

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def convert(self, prompt: str, input_type: PromptDataType) -> str:
        """
        Generates variations of the input prompts using the converter target.
        Parameters:
            prompts: list of prompts to convert
        Return:
            target_responses: list of prompt variations generated by the converter target
        """

        if not self.is_supported(input_type):
            raise ValueError("Input type not supported")

        response_msg = self.converter_target.send_prompt(
            normalized_prompt=prompt,
            conversation_id=self._conversation_id,
            normalizer_id=self._normalizer_id,
        )

        try:
            llm_response: dict[str, str] = json.loads(response_msg)["output"]
            return llm_response[self.language]

        except json.JSONDecodeError as e:
            logger.warn(f"Error in LLM response {response_msg}: {e}")
            raise RuntimeError(f"Error in LLM respons {response_msg}")

    def is_supported(self, input_type: PromptDataType) -> bool:
        return input_type == "text"
