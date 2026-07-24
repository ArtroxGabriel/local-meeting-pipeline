from __future__ import annotations

from clerk.prompts import (
    CpuPromptStrategy,
    GpuPromptStrategy,
    PromptManager,
    clean_srt_for_prompt,
    get_language_name,
)


def test_get_language_name() -> None:
    assert get_language_name("pt") == "Portuguese"
    assert get_language_name("en") == "English"
    assert get_language_name(None) == "Portuguese"
    assert get_language_name("custom") == "custom"


def test_clean_srt_for_prompt() -> None:
    raw_srt = """1
00:00:00,000 --> 00:00:02,500
Hello world, welcome to the test.

2
00:00:03,000 --> 00:00:05,000
This is a secondary line.
"""
    cleaned = clean_srt_for_prompt(raw_srt)
    assert "00:00:00" not in cleaned
    assert "1" not in cleaned.splitlines()
    assert "Hello world, welcome to the test." in cleaned
    assert "This is a secondary line." in cleaned


def test_prompt_manager_and_strategies() -> None:
    cpu_strat = PromptManager.get_strategy(is_gpu_model=False)
    gpu_strat = PromptManager.get_strategy(is_gpu_model=True)

    assert isinstance(cpu_strat, CpuPromptStrategy)
    assert isinstance(gpu_strat, GpuPromptStrategy)

    meeting_prompt_cpu = cpu_strat.build_summary_prompt("test transcript", "Portuguese", is_video=False)
    assert "## Pontos principais" in meeting_prompt_cpu

    video_prompt_gpu = gpu_strat.build_summary_prompt("test transcript", "English", is_video=True)
    assert "## Resumo geral" in video_prompt_gpu
    assert "content strategist" in video_prompt_gpu
