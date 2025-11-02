from collections.abc import Generator
from typing import Any
import json

import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


DEFAULT_INDEXING_TECHNIQUE = "high_quality"
DEFAULT_PROCESS_RULE = {"mode": "automatic"}

class KnowledgeTool(Tool):
    def _validate_pre_processing_rules(self, pre_processing_rules: list | None):
        if pre_processing_rules is None:
            raise ValueError("Process rule pre_processing_rules is required")
        for rule in pre_processing_rules:
            if not rule.get("id"):
                raise ValueError("Process rule pre_processing_rules id is required")
            if not isinstance(rule.get("enabled"), bool):
                raise ValueError("Process rule pre_processing_rules enabled is invalid, must be a boolean")

    def _validate_segmentation_rules(self, segmentation: dict | None, mode: str, parent_mode: str | None):
        if segmentation is None:
            raise ValueError("Process rule segmentation is required")

        separator = segmentation.get("separator")
        if separator is None:
            raise ValueError("Process rule segmentation separator is required")
        if not isinstance(separator, str):
            raise ValueError("Process rule segmentation separator is invalid, must be a string")

        # max_tokens is required unless mode is hierarchical and parent_mode is full-doc
        if not (mode == "hierarchical" and parent_mode == "full-doc"):
            max_tokens = segmentation.get("max_tokens")
            if max_tokens is None:
                raise ValueError("Process rule segmentation max_tokens is required")
            if not isinstance(max_tokens, int):
                raise ValueError("Process rule segmentation max_tokens is invalid, must be an integer")

    def _validate_process_rule_structure(self, process_rule: dict[str, Any]):
        mode = process_rule.get("mode")
        if mode not in ["automatic", "custom", "hierarchical"]:
            raise ValueError(f"Invalid process_rule mode: {mode}")

        if mode in ["custom", "hierarchical"]:
            rules = process_rule.get("rules")
            if not rules:
                raise ValueError("Process rule rules is required for custom or hierarchical mode")

            self._validate_pre_processing_rules(rules.get("pre_processing_rules"))
            self._validate_segmentation_rules(rules.get("segmentation"), mode, rules.get("parent_mode"))

    def _resolve_indexing_technique(self, indexing_technique: Any) -> str:
        if indexing_technique is None:
            return DEFAULT_INDEXING_TECHNIQUE

        if isinstance(indexing_technique, str):
            stripped = indexing_technique.strip()
            if not stripped:
                return DEFAULT_INDEXING_TECHNIQUE
            return stripped

        raise ValueError("indexing_technique must be a string")

    def _load_process_rule(self, process_rule_raw: Any) -> dict[str, Any]:
        if process_rule_raw is None:
            process_rule = DEFAULT_PROCESS_RULE.copy()
            self._validate_process_rule_structure(process_rule)
            return process_rule

        if not isinstance(process_rule_raw, str):
            raise ValueError("process_rule must be provided as a JSON string")

        process_rule_str = process_rule_raw.strip()
        if not process_rule_str:
            process_rule = DEFAULT_PROCESS_RULE.copy()
            self._validate_process_rule_structure(process_rule)
            return process_rule

        process_rule = json.loads(process_rule_str)
        self._validate_process_rule_structure(process_rule)
        return process_rule

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        api_uri = self.runtime.credentials.get("api_uri")
        api_secret = self.runtime.credentials.get("api_secret")
        dataset_id = tool_parameters.get("dataset_id")

        if not api_uri or not api_secret:
            raise ValueError("api_uri and api_secret are required credentials")
        if not dataset_id:
            raise ValueError("dataset_id is required")

        base_url = api_uri.rstrip("/")
        dataset_base_url = f"{base_url}/datasets/{dataset_id}"
        headers = {
            "Authorization": f'Bearer {api_secret}',
            "Content-Type": "application/json",
        }

        document_name = tool_parameters.get("name")
        data = {
            "text": tool_parameters.get("text"),
            "name": document_name,
            "indexing_technique": self._resolve_indexing_technique(tool_parameters.get("indexing_technique")),
        }

        doc_form = tool_parameters.get("doc_form")
        if doc_form not in (None, ""):
            data["doc_form"] = doc_form

        doc_language = tool_parameters.get("doc_language")
        if doc_language not in (None, ""):
            data["doc_language"] = doc_language

        try:
            process_rule = self._load_process_rule(tool_parameters.get("process_rule"))
            data["process_rule"] = process_rule
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for process_rule: {e}")
        except Exception as e:
            raise ValueError(f"Invalid process_rule: {e}")

        document_id = None
        if document_name:
            document_id = self._find_document_id_by_name(dataset_base_url, headers, document_name)

        if document_id:
            operation = "update"
            url = f"{dataset_base_url}/documents/{document_id}/update-by-text"
        else:
            operation = "create"
            url = f"{dataset_base_url}/document/create-by-text"

        response = httpx.post(url, headers=headers, json=data)
        self._raise_for_status(response, f"Failed to {operation} document")

        result = response.json()
        if isinstance(result, dict):
            result.setdefault("operation", operation)
            if document_id and "document" not in result:
                result.setdefault("document", {"id": document_id})

        yield self.create_json_message(result)

    def _find_document_id_by_name(self, dataset_base_url: str, headers: dict[str, str], document_name: str) -> str | None:
        params = {"keyword": document_name, "limit": 2, "page": 1}
        response = httpx.get(f"{dataset_base_url}/documents", headers=headers, params=params)
        self._raise_for_status(response, "Failed to query existing documents")

        try:
            payload = response.json()
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Unexpected response while searching documents: {error}") from error

        if not isinstance(payload, dict):
            return None

        documents = payload.get("data")
        if not isinstance(documents, list):
            return None

        for item in documents:
            if isinstance(item, dict) and item.get("name") == document_name:
                doc_id = item.get("id")
                if isinstance(doc_id, str) and doc_id:
                    return doc_id
        return None

    @staticmethod
    def _raise_for_status(response: httpx.Response, message: str) -> None:
        if 200 <= response.status_code < 300:
            return

        detail: str | None = None
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                detail = (
                    parsed.get("message")
                    or parsed.get("error")
                    or parsed.get("detail")
                )
        except json.JSONDecodeError:
            parsed = response.text
            if parsed:
                detail = parsed

        if detail:
            raise RuntimeError(f"{message}: {detail}")

        raise RuntimeError(f"{message}: HTTP {response.status_code}")
