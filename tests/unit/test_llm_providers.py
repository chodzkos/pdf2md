"""Testy jednostkowe dostawców LLM — bez prawdziwych wywołań API."""

from __future__ import annotations

import importlib.metadata
import json
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pdf2md.llm.anthropic_provider import AnthropicProvider
from pdf2md.llm.base import LLMResult
from pdf2md.llm.gemini_provider import GeminiProvider
from pdf2md.llm.ollama_provider import OllamaProvider
from pdf2md.llm.openai_provider import OpenAIProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_settings(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "anthropic_api_key": "",
        "openai_api_key": "",
        "gemini_api_key": "",
        "anthropic_model": "",
        "openai_model": "",
        "gemini_model": "",
        "ollama_model": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    def test_is_available_true_when_server_responds(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", return_value=mock_resp):
            assert OllamaProvider().is_available() is True

    def test_is_available_false_when_server_down(self) -> None:
        with patch(
            "pdf2md.llm.ollama_provider.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert OllamaProvider().is_available() is False

    def test_is_available_false_on_oserror(self) -> None:
        with patch(
            "pdf2md.llm.ollama_provider.urllib.request.urlopen",
            side_effect=OSError("connection refused"),
        ):
            assert OllamaProvider().is_available() is False

    def test_postprocess_returns_llm_result(self) -> None:
        response_body = json.dumps({"response": "# Poprawiony"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        fake_settings = _fake_settings(ollama_model="qwen2.5:14b")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", return_value=mock_resp),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            result = OllamaProvider().postprocess("# Wejście", mode="whole_document")

        assert isinstance(result, LLMResult)
        assert result.text == "# Poprawiony"
        assert result.provider_used == "Ollama (lokalny)"

    def test_postprocess_uses_model_from_settings(self) -> None:
        captured: dict[str, object] = {}
        response_body = json.dumps({"response": "ok"}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req: object, **kwargs: object) -> object:
            captured["data"] = json.loads(req.data.decode())  # type: ignore[attr-defined]
            return mock_resp

        fake_settings = _fake_settings(ollama_model="llama3:8b")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", side_effect=fake_urlopen),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            OllamaProvider().postprocess("tekst", mode="whole_document")

        assert captured["data"]["model"] == "llama3:8b"  # type: ignore[index]

    def test_postprocess_uses_default_model_when_settings_empty(self) -> None:
        captured: dict[str, object] = {}
        response_body = json.dumps({"response": "ok"}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req: object, **kwargs: object) -> object:
            captured["data"] = json.loads(req.data.decode())  # type: ignore[attr-defined]
            return mock_resp

        fake_settings = _fake_settings(ollama_model="")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", side_effect=fake_urlopen),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            OllamaProvider().postprocess("tekst", mode="whole_document")

        assert captured["data"]["model"] == OllamaProvider.default_model  # type: ignore[index]

    def test_postprocess_by_chunk_calls_llm_multiple_times(self) -> None:
        call_count = 0
        response_body = json.dumps({"response": "chunk ok"}).encode()

        def fake_urlopen(req: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_body
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        long_text = "słowo " * 20000  # ~120 000 znaków / 4 = 30 000 tokenów
        fake_settings = _fake_settings(ollama_model="qwen2.5:14b")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", side_effect=fake_urlopen),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            result = OllamaProvider().postprocess(long_text, mode="by_chunk")

        assert call_count > 1
        assert isinstance(result, LLMResult)

    def test_correct_sends_system_user_think_false_and_temperature(self) -> None:
        """correct(): /api/chat z system+user, think=False na poziomie body, options.temperature."""
        captured: dict[str, object] = {}
        response_body = json.dumps({"message": {"content": "skorygowany"}}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        def fake_urlopen(req: object, **kwargs: object) -> object:
            captured["url"] = req.full_url  # type: ignore[attr-defined]
            captured["data"] = json.loads(req.data.decode())  # type: ignore[attr-defined]
            return mock_resp

        fake_settings = _fake_settings(ollama_model="qwen3:14b")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", side_effect=fake_urlopen),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            out = OllamaProvider().correct("0CR tekst", system_prompt="KOREKTA", temperature=0.0)

        assert out == "skorygowany"
        data = captured["data"]
        assert str(captured["url"]).endswith("/api/chat")
        assert data["think"] is False  # type: ignore[index]
        assert data["options"]["temperature"] == 0.0  # type: ignore[index]
        assert data["messages"] == [  # type: ignore[index]
            {"role": "system", "content": "KOREKTA"},
            {"role": "user", "content": "0CR tekst"},
        ]


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def test_is_available_false_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.get_settings",
            lambda: _fake_settings(anthropic_api_key=""),
        )
        assert AnthropicProvider().is_available() is False

    def test_is_available_false_when_package_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.get_settings",
            lambda: _fake_settings(anthropic_api_key="sk-test"),
        )

        def fake_version(pkg: str) -> str:
            raise importlib.metadata.PackageNotFoundError

        monkeypatch.setattr(importlib.metadata, "version", fake_version)
        assert AnthropicProvider().is_available() is False

    def test_is_available_true_when_key_and_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.get_settings",
            lambda: _fake_settings(anthropic_api_key="sk-test"),
        )
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "0.29.0")
        assert AnthropicProvider().is_available() is True

    def test_postprocess_uses_model_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_message = MagicMock()
        fake_message.content = [MagicMock(text="# Poprawiony")]

        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_message

        fake_anthropic_mod = MagicMock()
        fake_anthropic_mod.Anthropic.return_value = fake_client

        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.get_settings",
            lambda: _fake_settings(anthropic_api_key="sk-test", anthropic_model="claude-opus-4-8"),
        )
        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.importlib.import_module",
            lambda name: fake_anthropic_mod,
        )

        result = AnthropicProvider().postprocess("# tekst", mode="whole_document")

        assert result.text == "# Poprawiony"
        call_kwargs = fake_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-8"

    def test_postprocess_uses_default_model_when_settings_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_message = MagicMock()
        fake_message.content = [MagicMock(text="ok")]

        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_message

        fake_anthropic_mod = MagicMock()
        fake_anthropic_mod.Anthropic.return_value = fake_client

        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.get_settings",
            lambda: _fake_settings(anthropic_api_key="sk-test", anthropic_model=""),
        )
        monkeypatch.setattr(
            "pdf2md.llm.anthropic_provider.importlib.import_module",
            lambda name: fake_anthropic_mod,
        )

        AnthropicProvider().postprocess("tekst")

        call_kwargs = fake_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == AnthropicProvider.default_model


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def test_is_available_false_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.get_settings",
            lambda: _fake_settings(openai_api_key=""),
        )
        assert OpenAIProvider().is_available() is False

    def test_postprocess_returns_llm_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_choice = MagicMock()
        fake_choice.message.content = "# GPT wynik"

        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response

        fake_openai_mod = MagicMock()
        fake_openai_mod.OpenAI.return_value = fake_client

        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.get_settings",
            lambda: _fake_settings(openai_api_key="sk-test", openai_model="gpt-4o"),
        )
        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.importlib.import_module",
            lambda name: fake_openai_mod,
        )

        result = OpenAIProvider().postprocess("# tekst")

        assert isinstance(result, LLMResult)
        assert result.text == "# GPT wynik"
        assert result.provider_used == "OpenAI (GPT)"

    def test_postprocess_uses_model_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_choice = MagicMock()
        fake_choice.message.content = "ok"

        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response

        fake_openai_mod = MagicMock()
        fake_openai_mod.OpenAI.return_value = fake_client

        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.get_settings",
            lambda: _fake_settings(openai_api_key="sk-test", openai_model="gpt-4o-mini"),
        )
        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.importlib.import_module",
            lambda name: fake_openai_mod,
        )

        OpenAIProvider().postprocess("tekst")

        call_kwargs = fake_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"

    def test_postprocess_uses_default_model_when_settings_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_choice = MagicMock()
        fake_choice.message.content = "ok"

        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response

        fake_openai_mod = MagicMock()
        fake_openai_mod.OpenAI.return_value = fake_client

        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.get_settings",
            lambda: _fake_settings(openai_api_key="sk-test", openai_model=""),
        )
        monkeypatch.setattr(
            "pdf2md.llm.openai_provider.importlib.import_module",
            lambda name: fake_openai_mod,
        )

        OpenAIProvider().postprocess("tekst")

        call_kwargs = fake_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == OpenAIProvider.default_model


# ---------------------------------------------------------------------------
# GeminiProvider
# ---------------------------------------------------------------------------


class TestGeminiProvider:
    def test_is_available_false_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key=""),
        )
        assert GeminiProvider().is_available() is False

    def test_is_available_false_when_package_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test"),
        )

        def fake_version(pkg: str) -> str:
            raise importlib.metadata.PackageNotFoundError

        monkeypatch.setattr(importlib.metadata, "version", fake_version)
        assert GeminiProvider().is_available() is False

    def test_is_available_true_when_key_and_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test"),
        )
        monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "1.0.0")
        assert GeminiProvider().is_available() is True

    def test_call_llm_raises_runtime_error_when_package_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test"),
        )
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.importlib.import_module",
            lambda name: (_ for _ in ()).throw(ImportError("No module named 'google.genai'")),
        )
        with pytest.raises(RuntimeError, match="google-genai nie jest zainstalowany"):
            GeminiProvider().postprocess("# tekst")

    def test_postprocess_returns_llm_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_response = MagicMock()
        fake_response.text = "# Gemini wynik"

        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = fake_response

        fake_genai_mod = MagicMock()
        fake_genai_mod.Client.return_value = fake_client

        fake_types_mod = MagicMock()

        def fake_import(name: str) -> object:
            if name == "google.genai":
                return fake_genai_mod
            if name == "google.genai.types":
                return fake_types_mod
            raise ImportError(name)

        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test", gemini_model="gemini-2.5-flash"),
        )
        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.importlib.import_module",
            fake_import,
        )

        result = GeminiProvider().postprocess("# tekst")

        assert isinstance(result, LLMResult)
        assert result.text == "# Gemini wynik"
        assert result.provider_used == "Gemini (Google)"

    def test_postprocess_uses_model_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_response = MagicMock()
        fake_response.text = "ok"

        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = fake_response

        fake_genai_mod = MagicMock()
        fake_genai_mod.Client.return_value = fake_client
        fake_types_mod = MagicMock()

        def fake_import(name: str) -> object:
            return fake_genai_mod if name == "google.genai" else fake_types_mod

        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test", gemini_model="gemini-2.0-flash"),
        )
        monkeypatch.setattr("pdf2md.llm.gemini_provider.importlib.import_module", fake_import)

        GeminiProvider().postprocess("tekst")

        call_kwargs = fake_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"

    def test_postprocess_uses_default_model_when_settings_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_response = MagicMock()
        fake_response.text = "ok"

        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = fake_response

        fake_genai_mod = MagicMock()
        fake_genai_mod.Client.return_value = fake_client
        fake_types_mod = MagicMock()

        def fake_import(name: str) -> object:
            return fake_genai_mod if name == "google.genai" else fake_types_mod

        monkeypatch.setattr(
            "pdf2md.llm.gemini_provider.get_settings",
            lambda: _fake_settings(gemini_api_key="AIza-test", gemini_model=""),
        )
        monkeypatch.setattr("pdf2md.llm.gemini_provider.importlib.import_module", fake_import)

        GeminiProvider().postprocess("tekst")

        call_kwargs = fake_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == GeminiProvider.default_model


# ---------------------------------------------------------------------------
# Size guard (by_heading z brakującymi nagłówkami)
# ---------------------------------------------------------------------------


class TestSizeGuard:
    """Strażnik rozmiaru: chunki ponad limit są automatycznie dzielone."""

    def test_by_heading_giant_chunk_is_split_further(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = 0
        response_body = json.dumps({"response": "ok"}).encode()

        def fake_urlopen(req: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.read.return_value = response_body
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        # Dokument bez nagłówków (by_heading zwróci jeden gigantyczny chunk)
        giant_text = "słowo " * 15000  # ~90 000 znaków = ~22 500 tokenów > 8 000

        fake_settings = _fake_settings(ollama_model="qwen2.5:14b")
        with (
            patch("pdf2md.llm.ollama_provider.urllib.request.urlopen", side_effect=fake_urlopen),
            patch("pdf2md.llm.ollama_provider.get_settings", return_value=fake_settings),
        ):
            result = OllamaProvider().postprocess(giant_text, mode="by_heading")

        # Musi być więcej niż jeden call — strażnik rozmiaru zadziałał
        assert call_count > 1
        assert isinstance(result, LLMResult)
