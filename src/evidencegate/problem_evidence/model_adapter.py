from __future__ import annotations

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
    def __init__(self, api_key_env: str = "OPENAI_API_KEY"):
        self.api_key_env = api_key_env

    def generate_audit_json(
        self,
        *,
        prompt: str,
        transport_schema: dict[str, Any],
        model: str,
    ) -> ModelSuccess | ModelFailure:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ModelConfigurationError(f"{self.api_key_env} is required for live model calls")

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
            raise ModelApiError(str(exc)) from exc

        response_id = getattr(response, "id", None)
        returned_model = getattr(response, "model", None) or model
        status = getattr(response, "status", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        if incomplete_details is not None:
            reason = getattr(incomplete_details, "reason", "incomplete")
            failure_reason: CompletionStatus = (
                "truncated" if reason == "max_output_tokens" else "incomplete"
            )
            return ModelFailure(
                reason=failure_reason,
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=f"response incomplete: {reason}",
            )
        if status not in (None, "completed"):
            return ModelFailure(
                reason="incomplete",
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                message=f"response status was {status}",
            )

        output = getattr(response, "output", None) or []
        for item in output:
            for content in getattr(item, "content", []) or []:
                content_type = getattr(content, "type", None)
                if content_type == "refusal":
                    return ModelFailure(
                        reason="refusal",
                        requested_model=model,
                        returned_model=returned_model,
                        response_id=response_id,
                        message=getattr(content, "refusal", "model refusal"),
                    )
                if content_type == "output_text":
                    parsed = getattr(content, "parsed", None)
                    if parsed is not None:
                        return ModelSuccess(
                            transport_content=parsed,
                            requested_model=model,
                            returned_model=returned_model,
                            response_id=response_id,
                            completion_status="completed",
                        )

        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            return ModelSuccess(
                transport_content=parsed,
                requested_model=model,
                returned_model=returned_model,
                response_id=response_id,
                completion_status="completed",
            )

        return ModelFailure(
            reason="incomplete",
            requested_model=model,
            returned_model=returned_model,
            response_id=response_id,
            message="response did not contain parsed structured output",
        )
