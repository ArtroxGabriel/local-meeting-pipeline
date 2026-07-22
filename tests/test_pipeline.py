from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from meeting_pipeline.pipeline import run_pipeline


def test_run_pipeline(tmp_path: Path) -> None:
    input_path = tmp_path / "input.mp3"
    input_path.write_text("audio contents")
    output_dir = tmp_path / "output"

    mock_metadata = {"language": "pt", "duration": 120.0}

    with patch("meeting_pipeline.pipeline.extract_audio", return_value=output_dir / "normalized.wav") as mock_extract, \
         patch("meeting_pipeline.pipeline.transcribe_file", return_value=("Mock transcription", mock_metadata)) as mock_transcribe, \
         patch("meeting_pipeline.pipeline.summarize_transcript", return_value="Mock summary") as mock_summarize:

        tx_path, sum_path = run_pipeline(
            input_path=input_path,
            output_dir=output_dir,
            whisper_model="tiny",
            whisper_device="cpu",
            whisper_compute_type="int8",
            llm_model="gemma:2b",
            language="pt",
        )

        assert tx_path == output_dir / "transcript.txt"
        assert sum_path == output_dir / "meeting_points.md"

        mock_extract.assert_called_once_with(input_path, output_dir / "normalized.wav")
        mock_transcribe.assert_called_once_with(
            output_dir / "normalized.wav",
            model_name="tiny",
            device="cpu",
            compute_type="int8",
            language="pt",
        )
        mock_summarize.assert_called_once_with(
            transcript="Mock transcription",
            model_name="gemma:2b",
        )

        assert (output_dir / "transcript.txt").read_text(encoding="utf-8") == "Mock transcription\n"
        assert (output_dir / "meeting_points.md").read_text(encoding="utf-8") == "Mock summary\n"
        
        metadata_content = json.loads((output_dir / "transcript_metadata.json").read_text(encoding="utf-8"))
        assert metadata_content == mock_metadata
