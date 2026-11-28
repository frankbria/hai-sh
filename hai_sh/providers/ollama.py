"""
Ollama provider implementation.

This module provides integration with Ollama for local LLM execution.
"""

from typing import Any, Optional
import json

from hai_sh.providers.base import BaseLLMProvider

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# Default local model. Chosen by the eval in eval/ (2026-11-27): the smallest
# model tested that clears every line of the bar in eval/README.md, with the
# constrained settings in hai_sh.config.DEFAULT_CONFIG. Apache-2.0 licensed.
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"


class OllamaModelNotFoundError(RuntimeError):
    """The configured model is not installed in the local Ollama."""

    def __init__(self, model: str):
        self.model = model
        super().__init__(f"Model '{model}' isn't installed in Ollama. Run: ollama pull {model}")


class OllamaProvider(BaseLLMProvider):
    """
    Ollama local model provider implementation.

    Supports local model execution via Ollama's REST API.
    Ollama must be running on the configured host.

    Example:
        >>> config = {
        ...     "base_url": "http://localhost:11434",
        ...     "model": "gemma4:e2b",
        ...     "timeout": 60
        ... }
        >>> provider = OllamaProvider(config)
        >>> response = provider.generate("List files")
        >>> print(response)
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Ollama provider.

        Args:
            config: Configuration dictionary with:
                - base_url: Ollama API URL (default: "http://localhost:11434")
                - model: Model name (default: "gemma4:e2b")
                - timeout: Request timeout in seconds (default: 60)
                - stream: Enable streaming (default: True)
                - temperature: Sampling temperature (default: 0.7)
                - format: Optional structured-output constraint passed to
                  Ollama: "json" (any JSON), "schema" (hai's response
                  JSON schema), or a JSON-schema dict. Default: None (off).
                - think: Optional bool sent as Ollama's ``think`` flag, for
                  models that reason before answering. Default: None (unset).
                - system_field: If True, send the system prompt in Ollama's
                  ``system`` field instead of prepending it to the prompt.
                  Default: False.
                - options: Optional dict of extra Ollama options (e.g.
                  seed, num_ctx, num_predict). Merged after temperature.
                - keep_alive: Optional keep_alive value (e.g. "10m").

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If requests package is not installed
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError(
                "Ollama provider requires the 'requests' package. "
                "Install it with: pip install requests"
            )

        super().__init__(config)

        # Store configuration
        self.base_url = self.config.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = self.config.get("model", DEFAULT_OLLAMA_MODEL)
        self.timeout = self.config.get("timeout", 60)
        self.stream = self.config.get("stream", True)
        self.temperature = self.config.get("temperature", 0.7)
        self.format = self.config.get("format")
        self.think = self.config.get("think")
        self.system_field = self.config.get("system_field", False)
        self.extra_options = self.config.get("options") or {}
        self.keep_alive = self.config.get("keep_alive")
        # Timing/token counts from the last completed request (Ollama's
        # eval_count, eval_duration, prompt_eval_count, ...). Empty until a
        # request finishes.
        self.last_metrics: dict[str, Any] = {}

    def _resolve_format(self) -> Optional[Any]:
        """Return the value for Ollama's ``format`` field, or None."""
        if self.format is None or self.format is False:
            return None
        if self.format == "schema":
            from hai_sh.prompt import RESPONSE_JSON_SCHEMA

            return RESPONSE_JSON_SCHEMA
        return self.format

    def build_payload(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Build the JSON body for Ollama's /api/generate.

        With the default configuration this is identical to the historical
        behaviour: system prompt, context and user prompt are concatenated
        into ``prompt``. The optional settings (format, think, system_field,
        options, keep_alive) are only added when configured.
        """
        if self.format == "schema" and system_prompt and system_prompt.strip():
            from hai_sh.prompt import RESPONSE_SCHEMA_HINT

            system_prompt = f"{system_prompt.rstrip()}\n\n{RESPONSE_SCHEMA_HINT}"

        if self.system_field and system_prompt and system_prompt.strip():
            payload_prompt = self._format_prompt(prompt, context, None)
        else:
            payload_prompt = self._format_prompt(prompt, context, system_prompt)

        options: dict[str, Any] = {"temperature": self.temperature}
        options.update(self.extra_options)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": payload_prompt,
            "stream": self.stream,
            "options": options,
        }
        if self.system_field and system_prompt and system_prompt.strip():
            payload["system"] = system_prompt

        fmt = self._resolve_format()
        if fmt is not None:
            payload["format"] = fmt
        if self.think is not None:
            payload["think"] = bool(self.think)
        if self.keep_alive is not None:
            payload["keep_alive"] = self.keep_alive
        return payload

    def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a response using Ollama's API.

        Args:
            prompt: The input prompt/query
            context: Optional context dictionary (e.g., cwd, git state)
            system_prompt: Optional system prompt with JSON format instructions

        Returns:
            str: Generated response from Ollama

        Raises:
            RuntimeError: If Ollama is not running or request fails
        """
        try:
            # Prepare API request
            url = f"{self.base_url}/api/generate"
            payload = self.build_payload(prompt, context, system_prompt)

            # Make API request
            response = requests.post(url, json=payload, timeout=self.timeout, stream=self.stream)

            # A model without the "thinking" capability may reject the think
            # flag. hai's defaults send think=false, so drop the flag for this
            # model and retry once instead of failing.
            if self._rejects_think(response, payload):
                self.think = None
                payload.pop("think", None)
                response = requests.post(
                    url, json=payload, timeout=self.timeout, stream=self.stream
                )

            # A model that was never pulled comes back as a 404. Say exactly
            # how to fix it rather than surfacing a bare HTTP error.
            if self._model_missing(response):
                raise OllamaModelNotFoundError(self.model)

            # Check for HTTP errors
            response.raise_for_status()

            # Handle streaming vs non-streaming responses
            if self.stream:
                return self._handle_streaming_response(response)
            else:
                return self._handle_non_streaming_response(response)

        except OllamaModelNotFoundError:
            raise
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. " f"Is Ollama running? Error: {e}"
            )
        except requests.exceptions.Timeout as e:
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s: {e}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Ollama: {e}")

    @staticmethod
    def _model_missing(response: Any) -> bool:
        """True if Ollama answered that the requested model is not installed."""
        if getattr(response, "status_code", None) != 404:
            return False
        try:
            body = response.text or ""
        except Exception:
            return False
        return "not found" in body.lower()

    @staticmethod
    def _rejects_think(response: Any, payload: dict[str, Any]) -> bool:
        """True if Ollama refused the request because of the think flag."""
        if "think" not in payload:
            return False
        if getattr(response, "status_code", None) != 400:
            return False
        try:
            body = response.text or ""
        except Exception:
            return False
        return "think" in body.lower()

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate Ollama provider configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid
        """
        # Model is not strictly required (has default), but if provided must be non-empty
        if "model" in config:
            model = config["model"]
            if not isinstance(model, str) or not model.strip():
                return False

        # Validate base_url if provided
        if "base_url" in config:
            base_url = config["base_url"]
            if not isinstance(base_url, str) or not base_url.strip():
                return False
            # Should start with http:// or https://
            if not base_url.startswith(("http://", "https://")):
                return False

        # Validate timeout if provided
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return False

        # Validate stream if provided
        if "stream" in config:
            stream = config["stream"]
            if not isinstance(stream, bool):
                return False

        # Validate format if provided
        if "format" in config and config["format"] is not None:
            fmt = config["format"]
            if not (fmt in ("json", "schema") or isinstance(fmt, dict)):
                return False

        # Validate think / system_field if provided
        for key in ("think", "system_field"):
            if key in config and config[key] is not None:
                if not isinstance(config[key], bool):
                    return False

        # Validate options if provided
        if "options" in config and config["options"] is not None:
            if not isinstance(config["options"], dict):
                return False

        # Validate temperature if provided
        if "temperature" in config:
            temperature = config["temperature"]
            if not isinstance(temperature, (int, float)):
                return False
            if temperature < 0 or temperature > 2:
                return False

        return True

    def is_available(self) -> bool:
        """
        Check if Ollama provider is available.

        Tests connection to Ollama API and checks if the model is available.

        Returns:
            bool: True if Ollama is running and accessible
        """
        if not REQUESTS_AVAILABLE:
            return False

        try:
            # Try to ping the Ollama API
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _format_prompt(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Format prompt with optional system prompt and context.

        Args:
            prompt: User prompt
            context: Optional context dictionary
            system_prompt: Optional system prompt with format instructions

        Returns:
            str: Formatted prompt with system prompt and context
        """
        parts = []

        # Add system prompt first if provided
        if system_prompt and system_prompt.strip():
            parts.append(system_prompt)

        # Build context info if provided
        if context:
            context_parts = []

            if "cwd" in context:
                context_parts.append(f"Current directory: {context['cwd']}")

            if "git" in context and context["git"].get("is_repo"):
                git_info = context["git"]
                context_parts.append(f"Git branch: {git_info.get('branch', 'unknown')}")
                if git_info.get("has_changes"):
                    context_parts.append("Git status: uncommitted changes")

            if "env" in context:
                env_info = context["env"]
                if "user" in env_info:
                    context_parts.append(f"User: {env_info['user']}")
                if "shell" in env_info:
                    context_parts.append(f"Shell: {env_info['shell']}")

            if context_parts:
                parts.extend(context_parts)

        # Add user prompt last
        parts.append(prompt)

        return "\n\n".join(parts)

    def _handle_streaming_response(self, response: requests.Response) -> str:
        """
        Handle streaming response from Ollama.

        Args:
            response: Streaming HTTP response

        Returns:
            str: Complete response text
        """
        full_response = []

        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        full_response.append(data["response"])

                    # Check if done
                    if data.get("done", False):
                        self._record_metrics(data)
                        break
                except json.JSONDecodeError:
                    continue

        return "".join(full_response).strip()

    def _handle_non_streaming_response(self, response: requests.Response) -> str:
        """
        Handle non-streaming response from Ollama.

        Args:
            response: HTTP response

        Returns:
            str: Response text
        """
        data = response.json()
        self._record_metrics(data)
        return data.get("response", "").strip()

    _METRIC_KEYS = (
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "prompt_eval_duration",
        "eval_count",
        "eval_duration",
    )

    def _record_metrics(self, data: Any) -> None:
        """Keep Ollama's timing and token counts from a final response."""
        if isinstance(data, dict):
            self.last_metrics = {k: data[k] for k in self._METRIC_KEYS if k in data}
