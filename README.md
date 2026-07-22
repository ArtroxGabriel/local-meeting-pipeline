# Local Meeting Pipeline

A high-performance Python-based local pipeline to process meeting audio and video files, transcribe them, and extract meeting bullet points using local models.

---

## 🛠️ Architecture

The pipeline processes files end-to-end entirely on your local machine:

```mermaid
graph TD
    A[Audio/Video Input or YT URL] --> B[Audio Extraction & Normalization]
    B -->|Convert to WAV 16kHz Mono| C[Transcription with faster-whisper]
    C -->|Generate transcript.srt| D[LLM Meeting Points with local Ollama]
    D -->|Generate meeting_points.md| E[Outputs: Subtitles + Summary + Metadata]
```

1. **Audio/Video Extraction & Normalization**: The input file (e.g., `.mp3`, `.mp4`, `.wav`, `.mkv`) or YouTube URL is processed via `ffmpeg` or `yt-dlp` to extract the audio channel and normalize it into a standard format: PCM 16-bit, 16000Hz, mono WAV.
2. **Transcription**: The normalized audio is transcribed using the **`faster-whisper`** library, generating a `.srt` subtitle file.
3. **Summarization (Local LLM)**: The transcript is fed to a local instance of **Ollama** (defaulting to the `gemma:2b` model) to construct structural meeting bullet points (Key Points, Decisions, Actions, and Pendencies) in Portuguese. Transcripts exceeding context windows are automatically chunked and consolidated.

---

## 📋 Prerequisites

Before running the pipeline, ensure you have the following installed on your system:

1. **Python >= 3.14**
2. **[uv](https://docs.astral.sh/uv/)** — Fast Python package installer and resolver.
3. **FFmpeg** — Required for audio extraction and format normalization.
   * *Linux*: `sudo apt install ffmpeg` (or your distro's package manager)
   * *macOS*: `brew install ffmpeg`
4. **yt-dlp** — Required for downloading audio from YouTube URLs.
5. **[Ollama](https://ollama.com/)** — Running locally with your model of choice pulled:
   ```bash
   ollama pull gemma:2b
   ```

---

## 🚀 Installation

Clone the repository and synchronize the environment using `uv`:

```bash
uv sync
```

This will automatically create a virtual environment, install all dependencies (including dev tools like `pytest` and `pyrefly`), and expose the CLI scripts.

---

## 💻 CLI Usage

Run the pipeline using `uv run`:

```bash
uv run meeting-pipeline --target <path_to_audio_or_video_file_or_youtube_url> [OPTIONS]
```

### Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--target` | `str` | *Required* | Path to local media file or YouTube URL |
| `--output-dir` | `Path` | `output` | Directory where output files will be saved |
| `--whisper-model` | `str` | `small` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, etc.) |
| `--whisper-device` | `str` | `cpu` | Device to run Whisper inference on (`cpu` or `cuda`) |
| `--whisper-compute-type`| `str` | `int8` | Model quantization/compute type (`int8`, `float16`, etc.) |
| `--llm-model` | `str` | `gemma:2b` | Ollama model name to use for summarization |
| `--language` | `str` | `pt` | Language code for transcription (e.g., `pt`, `en`) |
| `--verbose` | `flag` | `False` | Enable debug logs |

### Examples

**Standard Audio Run:**
```bash
uv run meeting-pipeline --target sample.mp3 --whisper-model small --language pt
```

**YouTube URL Run:**
```bash
uv run meeting-pipeline --target "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --whisper-model small --language pt
```

**Fast / Low-Resource Run:**
```bash
uv run meeting-pipeline --target sample.mp3 --whisper-model tiny --language pt --verbose
```

---

## 🐳 Docker & Docker Compose

You can run the entire pipeline, including an isolated instance of Ollama, using Docker Compose. The Docker setup is optimized for ultra-lightweight CPU execution (**~400 MB** image size) with optional GPU acceleration (**~2.2 GB** image size with CUDA library pruning).

### 📦 Image Sizes & Strategy

* **CPU Image (Default)**: `~400 MB` — Builds lightweight standard dependencies.
* **GPU Image (CUDA Enabled)**: `~2.2 GB` — Built with `INSTALL_CUDA=true`. Static CUDA archives (`*.a` files) are stripped automatically during build to reduce image size by over 55%.

### ⚙️ Configuration & Build (CPU vs GPU)

1. **Copy configuration file**:
   ```bash
   cp .env.example .env
   ```

2. **Select Mode in `.env`**:
   * **CPU Mode (Default)**: Keep `.env` configured for CPU:
     ```env
     COMPOSE_FILE=docker-compose.yaml
     ```
   * **GPU Mode (CUDA Acceleration)**: Edit `.env` to load the GPU overlay:
     ```env
     COMPOSE_FILE=docker-compose.yaml:docker-compose.gpu.yaml
     ```

3. **Build the Container Image**:
   * **For CPU**: `docker compose build app`
   * **For GPU**: `docker compose build app` *(Builds with `INSTALL_CUDA=true` when `.env` has the GPU overlay)*

---

### 🚀 How to Run

#### Single-Job Execution (With Auto-Teardown)
To process a file and automatically stop all containers (releasing system resources) when finished:

```bash
docker compose up --exit-code-from app --abort-on-container-exit
```

#### Interactive / Custom Command Execution
Start background services first, then run custom parameters:

1. **Start background services (Ollama)**:
   ```bash
   docker compose up -d
   ```

2. **Run Pipeline Command**:
   * **CPU Example**:
     ```bash
     docker compose run --rm app --target sample.mp3 --whisper-model small --whisper-device cpu --language pt
     ```
   * **GPU Example (CUDA)**:
     ```bash
     docker compose run --rm app --target "https://youtu.be/aqmt_3UWItA" --whisper-model medium --whisper-device cuda --whisper-compute-type float16 --llm-model llama3.1:8b --verbose
     ```

3. **Stop background services**:
   ```bash
   docker compose down
   ```

> 💡 **Automatic Model Pulling & Memory Eviction**:
> * If a requested LLM model (e.g. `llama3.1:8b`) is not downloaded locally in Ollama, the pipeline will automatically pull it on demand.
> * Upon completing summarization, the pipeline automatically sends `keep_alive: 0` to Ollama, evicting the model from VRAM/RAM immediately.

---

## 📁 Outputs

All outputs are saved to the designated `--output-dir` (default: `output/`):
* **`normalized.wav`**: The 16kHz mono audio track extracted/normalized from the input.
* **`transcript.srt`**: The full transcription in SubRip (.srt) format with timestamps.
* **`transcript_metadata.json`**: Metadata containing runtime parameters, detected language, and duration.
* **`meeting_points.md`**: Markdown document summarizing main points, decisions, actions, and pendencies in Portuguese.


---

## 🧪 Development & Quality Assurance

### Run Tests
A comprehensive suite of unit tests covers the CLI, transcription, normalization, and summarization modules. Run the registered test script:

```bash
uv run meeting-pipeline-test
```

### Code Formatting & Quality
Check lint rules using Ruff:
```bash
uv run ruff check
```

### Static Type Checking
Perform static analysis and type checking using the **Pyrefly** LSP/type checker:
```bash
uv run pyrefly check
```
