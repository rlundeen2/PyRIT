# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import base64

from pyrit.models import PromptDataType
from pyrit.prompt_converter import PromptConverter


class Base64Converter(PromptConverter):
    def convert(self, *, prompt: str, input_type: PromptDataType = "text") -> str:
        """
        Simple converter that just base64 encodes the prompt
        """
        if not self.is_supported(input_type):
            raise ValueError("Input type not supported")

        string_bytes = prompt.encode("utf-8")
        encoded_bytes = base64.b64encode(string_bytes)
        return encoded_bytes.decode("utf-8")

    def is_supported(self, input_type: PromptDataType) -> bool:
        return input_type == "text"
