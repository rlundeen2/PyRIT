# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.


import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from scipy.io import wavfile

from pyrit.prompt_converter.audio_frequency_converter import AudioFrequencyConverter
from pyrit.models.data_type_serializer import AudioPathDataTypeSerializer


@pytest.mark.asyncio
@patch("pyrit.models.data_type_serializer.data_serializer_factory")
@patch("pyrit.memory.MemoryInterface.storage_io")
async def test_convert_async_success(mock_storage_io, mock_serializer_factory):
    # Set up mock serializer
    mock_serializer = MagicMock(spec=AudioPathDataTypeSerializer)
    mock_serializer.value = "mock_audio_file.wav"  # This will be updated to the temporary file name
    mock_serializer.read_data = AsyncMock()
    mock_serializer.save_data = AsyncMock()
    mock_serializer_factory.return_value = mock_serializer

    # Simulate WAV data
    sample_rate = 44100
    mock_audio_data = np.random.randint(-32768, 32767, size=(100,), dtype=np.int16)

    # Create a temporary file for the WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
        original_wav_path = temp_wav_file.name
        wavfile.write(original_wav_path, sample_rate, mock_audio_data)

    # Read the data from the created WAV file into bytes
    with open(original_wav_path, "rb") as f:
        wav_data = f.read()

    # Set the read_data mock to return the byte data
    mock_serializer.read_data.return_value = wav_data
    mock_storage_io.path_exists = AsyncMock(return_value=True)
    converter = AudioFrequencyConverter(shift_value=20000)

    # Call the convert_async method with the temporary WAV file path
    prompt = original_wav_path
    result = await converter.convert_async(prompt=prompt)

    assert result.output_text != mock_serializer.value
    assert os.path.exists(result.output_text)
    assert isinstance(result.output_text, str)

    # Clean up the original WAV file after the test
    os.remove(original_wav_path)

    # Optionally, clean up any created files in result (if applicable)
    if os.path.exists(result.output_text):
        os.remove(result.output_text)


@pytest.mark.asyncio
@patch("pyrit.models.data_type_serializer.data_serializer_factory")
@patch("pyrit.memory.MemoryInterface.storage_io")
async def test_convert_async_file_not_found(mock_storage_io, mock_serializer_factory):
    # Create a mock serializer
    mock_serializer = MagicMock(spec=AudioPathDataTypeSerializer)
    mock_serializer_factory.return_value = mock_serializer

    # Create an instance of the converter
    converter = AudioFrequencyConverter(shift_value=20000)

    prompt = "non_existent_file.wav"

    # Ensure that an exception is raised when trying to convert a non-existent file
    with pytest.raises(FileNotFoundError):
        await converter.convert_async(prompt=prompt)