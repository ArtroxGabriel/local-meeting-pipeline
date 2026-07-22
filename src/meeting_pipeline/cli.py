from __future__ import annotations

import logging
from pathlib import Path
import time

import typer

from .audio import download_youtube_audio
from .pipeline import run_pipeline

app = typer.Typer(add_completion=False)
logger = logging.getLogger(__name__)

PRESETS: dict[str, dict[str, str]] = {
    "cpu": {
        "whisper_model": "small",
        "whisper_device": "cpu",
        "whisper_compute_type": "int8",
        "llm_model": "LiquidAI/lfm2.5-1.2b-instruct",
    },
    "fast": {
        "whisper_model": "tiny",
        "whisper_device": "cpu",
        "whisper_compute_type": "int8",
        "llm_model": "LiquidAI/lfm2.5-1.2b-instruct",
    },
    "gpu": {
        "whisper_model": "medium",
        "whisper_device": "cuda",
        "whisper_compute_type": "float16",
        "llm_model": "llama3.1:8b",
    },
    "cuda": {
        "whisper_model": "medium",
        "whisper_device": "cuda",
        "whisper_compute_type": "float16",
        "llm_model": "llama3.1:8b",
    },
    "accurate": {
        "whisper_model": "large-v3",
        "whisper_device": "cuda",
        "whisper_compute_type": "float16",
        "llm_model": "llama3.1:8b",
    },
}


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@app.command()
def main(
    target: str = typer.Option(
        ...,
        "--target",
        help="Input file path or YouTube URL of the video/audio to process.",
    ),
    output_dir: Path = typer.Option(Path("output"), "--output-dir"),
    preset: str | None = typer.Option(
        None,
        "--preset",
        "-p",
        help="Configuration profile ('cpu', 'gpu'/'cuda', 'fast', 'accurate').",
    ),
    gpu: bool = typer.Option(False, "--gpu", help="Shortcut for GPU configuration (--preset gpu)."),
    fast: bool = typer.Option(False, "--fast", help="Shortcut for fast CPU configuration (--preset fast)."),
    whisper_model: str | None = typer.Option(None, "--whisper-model"),
    whisper_device: str | None = typer.Option(None, "--whisper-device"),
    whisper_compute_type: str | None = typer.Option(None, "--whisper-compute-type"),
    llm_model: str | None = typer.Option(None, "--llm-model"),
    language: str = typer.Option("pt", "--language"),
    video: bool = typer.Option(
        False,
        "--video",
        help="Use video summary prompt template instead of meeting template.",
    ),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    configure_logging(verbose)

    # Determine preset profile
    selected_preset = preset.lower() if preset else None
    if not selected_preset:
        if gpu:
            selected_preset = "gpu"
        elif fast:
            selected_preset = "fast"
        else:
            selected_preset = "cpu"

    if selected_preset not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        typer.echo(f"Error: Unknown preset '{selected_preset}'. Available presets: {available}", err=True)
        raise typer.Exit(code=1)

    defaults = PRESETS[selected_preset]

    # Explicit flags override preset defaults
    effective_whisper_model = whisper_model or defaults["whisper_model"]
    effective_whisper_device = whisper_device or defaults["whisper_device"]
    effective_whisper_compute_type = whisper_compute_type or defaults["whisper_compute_type"]
    effective_llm_model = llm_model or defaults["llm_model"]

    is_url = (
        target.startswith(("http://", "https://", "www."))
        or "youtube.com" in target
        or "youtu.be" in target
    )
    is_video = is_url or video

    temp_file: Path | None = None

    try:
        if is_url:
            t0 = time.perf_counter()
            temp_file = download_youtube_audio(target)
            t_dl = time.perf_counter() - t0
            logger.info("YouTube audio download completed in %.2fs", t_dl)
            input_path = temp_file

        else:
            input_path = Path(target)
            if not input_path.exists():
                logger.error("Input file does not exist: %s", input_path)
                typer.echo(f"Error: Input file does not exist: {input_path}", err=True)
                raise typer.Exit(code=1)

        transcript_path, summary_path = run_pipeline(
            input_path=input_path,
            output_dir=output_dir,
            whisper_model=effective_whisper_model,
            whisper_device=effective_whisper_device,
            whisper_compute_type=effective_whisper_compute_type,
            llm_model=effective_llm_model,
            language=language,
            is_video=is_video,
        )

        typer.echo(f"Transcript: {transcript_path}")
        typer.echo(f"Meeting points: {summary_path}")

    except KeyboardInterrupt:
        typer.echo("\nProcess interrupted by user. Exiting...", err=True)
        raise typer.Exit(code=130)
    except typer.Exit:
        raise
    except Exception:
        logger.exception("Pipeline execution failed")
        raise typer.Exit(code=1)
    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
                logger.info("Deleted temporary YouTube audio file: %s", temp_file)
            except Exception as e:
                logger.warning("Failed to delete temporary file %s: %s", temp_file, e)
