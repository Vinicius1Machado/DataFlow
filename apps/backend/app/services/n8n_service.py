from typing import Any

import httpx

from app.core.config import settings


class N8NServiceError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class N8NService:
    def __init__(self) -> None:
        self.webhook_url = settings.n8n_webhook_url
        self.webhook_secret = settings.n8n_webhook_secret

    async def send_job_to_n8n(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"x-webhook-secret": self.webhook_secret}
        timeout = httpx.Timeout(30.0, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.webhook_url, json=payload, headers=headers)
        except httpx.ConnectError as exc:
            raise N8NServiceError("Could not connect to n8n webhook.") from exc
        except httpx.TimeoutException as exc:
            raise N8NServiceError("n8n webhook request timed out.") from exc
        except httpx.RequestError as exc:
            raise N8NServiceError("Failed to send request to n8n webhook.") from exc

        if response.status_code >= 400:
            raise N8NServiceError(
                f"n8n webhook returned HTTP {response.status_code}.",
                status_code=response.status_code,
            )

        try:
            response_data = response.json()
        except ValueError as exc:
            raise N8NServiceError("n8n webhook returned a non-JSON response.") from exc

        if not isinstance(response_data, dict):
            raise N8NServiceError("n8n webhook returned JSON, but not an object.")

        return response_data


def get_n8n_service() -> N8NService:
    return N8NService()
