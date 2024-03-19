import json
import logging
import pathlib

from pyrit.interfaces import ChatSupport
from pyrit.prompt_converter import PromptConverter
from pyrit.models import PromptTemplate, ChatMessage
from pyrit.common.path import DATASETS_PATH
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class TranslationConverter(PromptConverter):
    def __init__(self, *, converter_target: ChatSupport, languages: list[str], prompt_template: PromptTemplate = None):
        """
        Initializes a TranslationConverter object.

        Args:
            converter_target (ChatSupport): The target chat support for the conversion which will translate
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

        self._validate_languages(languages)

        self.languages = languages
        language_str = ", ".join(languages)

        self.system_prompt = str(prompt_template.apply_custom_metaprompt_parameters(languages=language_str))

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def convert(self, prompts: list[str]) -> list[str]:
        """
        Generates variations of the input prompts using the converter target.
        Parameters:
            prompts: list of prompts to convert
        Return:
            target_responses: list of prompt variations generated by the converter target
        """
        converted_prompts = []

        for prompt in prompts:
            chat_entries = [
                ChatMessage(role="system", content=self.system_prompt),
                ChatMessage(role="user", content=prompt),
            ]

            response_msg = self.converter_target.complete_chat(messages=chat_entries)

            try:
                llm_response: dict[str, str] = json.loads(response_msg)["output"]

                for variation in llm_response.values():
                    converted_prompts.append(variation)

            except json.JSONDecodeError:
                logger.log(level=logging.WARNING, msg=f"Error in LLM response {response_msg}")
                raise RuntimeError(f"Error in LLM respons {response_msg}")

        return converted_prompts

    def is_one_to_one_converter(self) -> bool:
        return len(self.languages) == 1

    def _validate_languages(self, languages):
        if not languages:
            raise ValueError("Languages must be provided")

        for language in languages:
            if not language or "," in language:
                raise ValueError("Language must be provided and not have a comma")
