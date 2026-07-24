from __future__ import annotations

import re
from typing import Protocol

LANGUAGE_NAMES: dict[str, str] = {
    "pt": "Portuguese",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
}


def get_language_name(lang_code: str | None) -> str:
    if not lang_code:
        return "Portuguese"
    return LANGUAGE_NAMES.get(lang_code.lower(), lang_code)


def clean_srt_for_prompt(transcript: str) -> str:
    """Removes SRT sequence numbers and timestamp headers for clean LLM prompt input."""
    if not transcript or not transcript.strip():
        return ""

    lines: list[str] = []
    timestamp_pattern = re.compile(
        r"^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}"
    )
    number_pattern = re.compile(r"^\d+$")

    for line in transcript.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        if number_pattern.match(line_str):
            continue
        if timestamp_pattern.match(line_str):
            continue
        lines.append(line_str)

    return "\n".join(lines).strip()


class PromptStrategy(Protocol):
    def build_summary_prompt(self, transcript: str, language: str, is_video: bool) -> str:
        ...

    def build_consolidation_prompt(self, category: str, items: str, language: str) -> str:
        ...


class CpuPromptStrategy:
    """Compact, direct prompt strategy optimized for CPU/small models (e.g. LiquidAI/lfm2.5)."""

    MEETING_PROMPT = """You are extracting a factual summary from a meeting transcript. Follow every rule below exactly.

RULES:
- Use only explicit statements from the transcript. Never infer, guess, or add information not stated.
- Ignore ASR formatting artifacts; focus only on spoken content.
- Write all bullet content in {language}. Keep the four section headers exactly as shown below, unchanged.
- If a section has no explicit content, write: Nenhuma registrada.
- Output ONLY the formatted result below. No preamble, explanation, or closing remarks.

OUTPUT FORMAT:
## Pontos principais
- [point]
## Decisões
- [decision]
## Ações
- [action]
## Pendências
- [pending issue]

Transcript:
{transcript}""".strip()

    VIDEO_PROMPT = """You are extracting a factual summary from the transcript of a video. Follow every rule below exactly.

RULES:
- Use only explicit statements from the transcript. Never infer, guess, or add information not stated.
- Ignore ASR formatting artifacts; focus only on spoken content.
- Write all bullet content in {language}. Keep the four section headers exactly as shown below, unchanged.
- If a section has no explicit content, write: Nenhuma registrada.
- Output ONLY the formatted result below. No preamble, explanation, or closing remarks.

OUTPUT FORMAT:
## Resumo geral
- [concise overview]
## Principais tópicos
- [key topic]
## Momentos importantes
- [important moment]
## Conclusões ou mensagens finais
- [final takeaway]

Transcript:
{transcript}""".strip()

    CONSOLIDATE_PROMPT = """You are merging a list of extracted items for the category '{category}'. Follow every rule below exactly.

RULES:
- Keep only explicit facts. Do not add or infer new claims.
- Merge items only if they clearly refer to the same fact.
- Write the consolidated list in {language}.
- Output ONLY the list below. No preamble or explanation.

OUTPUT FORMAT:
- [consolidated item]

Items to consolidate:
{items}""".strip()

    def build_summary_prompt(self, transcript: str, language: str, is_video: bool) -> str:
        template = self.VIDEO_PROMPT if is_video else self.MEETING_PROMPT
        return template.format(transcript=transcript, language=language)

    def build_consolidation_prompt(self, category: str, items: str, language: str) -> str:
        return self.CONSOLIDATE_PROMPT.format(category=category, items=items, language=language)


class GpuPromptStrategy:
    """Detailed, rich prompt strategy optimized for GPU/larger models (e.g. llama3.1:8b)."""

    MEETING_PROMPT = """You are an expert executive assistant summarizing a meeting transcript accurately and concisely.

GUIDELINES:
- Extract key points, decisions, actions, and pending items strictly based on spoken statements.
- Never add assumptions, external facts, or speculative interpretations.
- Write all bullet points in {language}, using clear and professional phrasing.
- Retain the exact section headers below regardless of language.
- If a section contains no relevant information in the transcript, state: Nenhuma registrada.
- Provide ONLY the requested Markdown output structure.

OUTPUT FORMAT:
## Pontos principais
- [point]
## Decisões
- [decision]
## Ações
- [action]
## Pendências
- [pending issue]

Transcript:
{transcript}""".strip()

    VIDEO_PROMPT = """You are an expert content strategist summarizing a video transcript.

GUIDELINES:
- Extract a high-level overview, key topics, crucial moments, and final takeaways.
- Base every item strictly on explicit statements in the transcript.
- Write all bullet points in {language}, using clear and engaging language.
- Retain the exact section headers below regardless of language.
- If a section contains no relevant information, state: Nenhuma registrada.
- Provide ONLY the requested Markdown output structure.

OUTPUT FORMAT:
## Resumo geral
- [overview]
## Principais tópicos
- [key topic]
## Momentos importantes
- [important moment]
## Conclusões ou mensagens finais
- [takeaway]

Transcript:
{transcript}""".strip()

    CONSOLIDATE_PROMPT = """You are an editor consolidating items for category '{category}' extracted from multiple parts of a transcript.

GUIDELINES:
- Combine duplicate or closely synonymous points while preserving unique details.
- Do not introduce new information not present in the input items.
- Write all points in {language}.
- Provide ONLY bullet points as output.

OUTPUT FORMAT:
- [consolidated item]

Items to consolidate:
{items}""".strip()

    def build_summary_prompt(self, transcript: str, language: str, is_video: bool) -> str:
        template = self.VIDEO_PROMPT if is_video else self.MEETING_PROMPT
        return template.format(transcript=transcript, language=language)

    def build_consolidation_prompt(self, category: str, items: str, language: str) -> str:
        return self.CONSOLIDATE_PROMPT.format(category=category, items=items, language=language)


class PromptManager:
    """Factory for obtaining prompt strategies tailored to CPU vs GPU models."""

    @staticmethod
    def get_strategy(is_gpu_model: bool = False) -> PromptStrategy:
        if is_gpu_model:
            return GpuPromptStrategy()
        return CpuPromptStrategy()
