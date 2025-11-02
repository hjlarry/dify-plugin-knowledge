from typing import Any

import httpx
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class KnowledgeProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_uri = credentials.get("api_uri", "")
        if not api_uri:
            raise ToolProviderCredentialValidationError("api_uri is required")

        url = f"{api_uri.rstrip('/')}/datasets"
        headers = {"Authorization": f'Bearer {credentials.get("api_secret")}'}
        res = httpx.get(url, headers=headers)
        if res.status_code != 200:
            raise ToolProviderCredentialValidationError("Invalid credentials, please check your api_uri and api_secret")
