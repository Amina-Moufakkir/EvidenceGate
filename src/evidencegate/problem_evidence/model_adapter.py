from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal


CompletionStatus = Literal["completed", "refusal", "incomplete", "truncated", "content_filtered"]


class ModelAdapterError(Exception):
    pass


class ModelConfigurationError(ModelAdapterError):
    pass


class ModelApiError(ModelAdapterError):
    pass


@dataclass(frozen=True)
class ModelSuccess:
    transport_content: dict[str, Any]
    requested_model: str
    returned_model: str
    response_id: str | None
    completion_status: CompletionStatus


@dataclass(frozen=True)
class ModelFailure:
    reason: CompletionStatus | Literal["api_error"]
    requested_model: str
    message: str
    returned_model: str | None = None
    response_id: str | None = None


class ModelAdapter:
    def generate_audit_json(
        self,
        *,
        prompt: str,
        transport_schema: dict[str, Any],
        model: str,
    ) -> ModelSuccess | ModelFailure:
        raise NotImplementedError


@dataclass
class FakeModelAdapter(ModelAdapter):
    transport_content: dict[str, Any] | None = None
    failure: ModelFailure | None = None

    def generate_audit_json(
        self,
        *,
        prompt: str,
        transport_schema: dict[str, Any],
        model: str,
    ) -> ModelSuccess | ModelFailure:
        if self.failure is not None:
            return self.failure
        if self.transport_content is None:
            raise ModelAdapterError("fake adapter requires transport_content or failure")
        return ModelSuccess(
            transport_content=self.transport_content,
            requested_model=model,
            returned_model=model,
            response_id="fake-response",
            completion_status="completed",
        )


class OpenAIResponsesAdapter(ModelAdapter):
    def __init__(self, api_key_env: str = "OPENAI_API_KEY", client: Any | None = None):
        self.api_key_env = api_key_env
        self.client = client

    def generate_audit_json(
        self,
        *,
        prompt: str,
        transport_schema: dict[str, Any],
        model: str,
    ) -> ModelSuccess | ModelFailure:
        api_key = os.environ.get(self.api_key_env)
        if not api_key and self.client is None:
            raise ModelConfigurationError(f"{self.api_key_env} is required for live model calls")

        client = self.client
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ModelConfigurationError("openai package is required for live model calls") from exc

            client = OpenAI(api_key=api_key)

        try:
            response = client.responses.create(
                model=model,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "problem_evidence_transport",
                        "strict": True,
                        "schema": transport_schema,
                    }
                },
            )
        except Exception as exc:
            return ModelFailure(
                reason="api_error",
                requested_model=model,
                message=f"OpenAI API error: {exc}",
            )

        response_id = getattr(response, "id", None)
        returned_model = getattr(response, "model", None) or model
        status = getattr(response, "status", None)

        refusal = _find_refusal(response)
        if refusal is not None:
            return ModelFailure(
                reason="refusal",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=refusal,
            )

        incomplete_details = getattr(response, "incomplete_details", None)
        if incomplete_details is not None:
            reason = getattr(incomplete_details, "reason", "incomplete")
            failure_reason: CompletionStatus
            if reason == "max_output_tokens":
                failure_reason = "truncated"
            elif reason == "content_filter":
                failure_reason = "content_filtered"
            else:
                failure_reason = "incomplete"
            return ModelFailure(
                reason=failure_reason,
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=f"response incomplete: {reason}",
            )
        if status not in (None, "completed"):
            return ModelFailure(
                reason="content_filtered" if status == "content_filtered" else "incomplete",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=f"response status was {status}",
            )

        text = _extract_output_text(response)
        if not text:
            return ModelFailure(
                reason="incomplete",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message="response did not contain output_text",
            )

        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            return ModelFailure(
                reason="incomplete",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=f"response output_text was not valid JSON: {exc.msg}",
            )

        if not isinstance(decoded, dict):
            return ModelFailure(
                reason="incomplete",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message="response output_text JSON must decode to an object",
            )

        return ModelSuccess(
            transport_content=decoded,
            requested_model=model,
            returned_model=returned_model,
            response_id=response_id,
            completion_status="completed",
        )


def _iter_response_content(response: Any):
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            yield content


def _find_refusal(response: Any) -> str | None:
    for content in _iter_response_content(response):
        if getattr(content, "type", None) == "refusal":
            return getattr(content, "refusal", None) or getattr(content, "text", None) or "model refusal"
    return None


def _extract_output_text(response: Any) -> str:
    texts = [
        getattr(content, "text", "")
        for content in _iter_response_content(response)
        if getattr(content, "type", None) == "output_text"
    ]
    if texts:
        return "".join(texts)
    return getattr(response, "output_text", "") or ""
