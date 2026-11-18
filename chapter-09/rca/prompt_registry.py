from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PromptTemplate:
    template_id: str
    version: str
    intent: str
    task_type: str
    safety_profile: str
    owner_team: str
    rollout_strategy: str
    previous_version: Optional[str] = None


class PromptRegistry:
    """Simple in-memory prompt registry for treatment variant.

    Provides metadata describing prompt templates and their evolution over
    time. This is a minimal stand-in for a more realistic registry with diffs
    and changelogs.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._by_version: Dict[str, PromptTemplate] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        # W1 prompts.
        self.register(
            PromptTemplate(
                template_id="answering-assistant",
                version="answering-assistant-v1",
                intent="qa_answering",
                task_type="qa",
                safety_profile="default",
                owner_team="qa-team",
                rollout_strategy="stable",
            )
        )
        self.register(
            PromptTemplate(
                template_id="answering-assistant",
                version="answering-assistant-v2-regressed",
                intent="creative_answering",
                task_type="qa",
                safety_profile="default",
                owner_team="qa-team",
                rollout_strategy="canary",
                previous_version="answering-assistant-v1",
            )
        )
               
        self.register(
            PromptTemplate(
                template_id="answering-assistant",
                version="answering-assistant-v3-fixed",
                intent="faithful_answering",
                task_type="qa",
                safety_profile="strict",
                owner_team="qa-team",
                rollout_strategy="stable",
                previous_version="answering-assistant-v2-regressed",
            )
        )

        # W2 RAG prompts.
        self.register(
            PromptTemplate(
                template_id="rag-assistant",
                version="rag-assistant-v1",
                intent="rag_factual_answering",
                task_type="rag_qa",
                safety_profile="default",
                owner_team="rag-team",
                rollout_strategy="stable",
            )
        )
        self.register(
            PromptTemplate(
                template_id="rag-assistant",
                version="rag-assistant-v2-heuristic-fix",
                intent="rag_answer_even_when_uncertain",
                task_type="rag_qa",
                safety_profile="lenient",
                owner_team="rag-team",
                rollout_strategy="canary",
                previous_version="rag-assistant-v1",
            )
        )

        # W3 policy-aware prompt.
        self.register(
            PromptTemplate(
                template_id="policy-aware-assistant",
                version="policy-aware-assistant-v1",
                intent="policy_sensitive_qa",
                task_type="qa",
                safety_profile="strict",
                owner_team="policy-team",
                rollout_strategy="stable",
            )
        )

    def register(self, tmpl: PromptTemplate) -> None:
        self._templates[tmpl.version] = tmpl
        self._by_version[tmpl.version] = tmpl

    def get_by_version(self, version: str) -> Optional[PromptTemplate]:
        return self._by_version.get(version)


__all__ = ["PromptRegistry", "PromptTemplate"]
