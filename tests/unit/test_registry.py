"""Testy rejestru silników i dostawców LLM."""

from __future__ import annotations

from pdf2md.core.registry import EngineRegistry, LLMRegistry
from pdf2md.engines.base import ConversionEngine, ConversionResult
from pdf2md.llm.base import LLMProvider, LLMResult


class _AvailableEngine(ConversionEngine):
    """Mock silnika — dostępny."""

    name = "mock_available"
    description = "Testowy silnik dostępny"
    supports_ocr = False
    supports_llm = False

    def is_available(self) -> bool:
        return True

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        return ConversionResult(markdown="# test", engine_used=self.name, pages=1)


class _UnavailableEngine(ConversionEngine):
    """Mock silnika — niedostępny."""

    name = "mock_unavailable"
    description = "Testowy silnik niedostępny"
    supports_ocr = True
    supports_llm = False

    def is_available(self) -> bool:
        return False

    def convert(self, pdf_path: str, **kwargs: object) -> ConversionResult:
        raise RuntimeError("niedostępny")


class _MockLLM(LLMProvider):
    """Mock dostawcy LLM."""

    name = "mock_llm"
    description = "Testowy LLM"
    requires_api_key = False
    default_model = "mock-model"

    def is_available(self) -> bool:
        return True

    def postprocess(
        self, markdown: str, mode: str = "whole_document", instructions: str = ""
    ) -> LLMResult:
        return LLMResult(text=markdown + " [LLM]", provider_used=self.name)

    def correct(self, text: str, *, system_prompt: str, temperature: float = 0.0) -> str:
        return text + " [CORRECTED]"


class TestEngineRegistry:
    def test_register_and_get_all(self) -> None:
        """Zarejestrowany silnik pojawia się w get_all()."""
        registry = EngineRegistry()
        engine = _AvailableEngine()
        registry.register(engine)
        assert engine in registry.get_all()

    def test_get_available_returns_only_available(self) -> None:
        """get_available() pomija silniki z is_available() == False."""
        registry = EngineRegistry()
        registry.register(_AvailableEngine())
        registry.register(_UnavailableEngine())
        available = registry.get_available()
        names = [e.name for e in available]
        assert "mock_available" in names
        assert "mock_unavailable" not in names

    def test_get_by_name_found(self) -> None:
        """get_by_name() zwraca właściwy silnik."""
        registry = EngineRegistry()
        engine = _AvailableEngine()
        registry.register(engine)
        found = registry.get_by_name("mock_available")
        assert found is engine

    def test_get_by_name_not_found(self) -> None:
        """get_by_name() zwraca None dla nieznanej nazwy."""
        registry = EngineRegistry()
        assert registry.get_by_name("nieistniejacy") is None

    def test_describe_empty(self) -> None:
        """describe() nie rzuca wyjątku gdy brak silników."""
        registry = EngineRegistry()
        text = registry.describe()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_describe_with_engines(self) -> None:
        """describe() zawiera nazwy zarejestrowanych silników."""
        registry = EngineRegistry()
        registry.register(_AvailableEngine())
        text = registry.describe()
        assert "mock_available" in text

    def test_is_installed_alias(self) -> None:
        """is_installed() jest aliasem dla is_available()."""
        engine = _AvailableEngine()
        assert engine.is_installed() == engine.is_available()


class TestLLMRegistry:
    def test_register_and_get_all(self) -> None:
        """Zarejestrowany dostawca pojawia się w get_all()."""
        registry = LLMRegistry()
        llm = _MockLLM()
        registry.register(llm)
        assert llm in registry.get_all()

    def test_get_available(self) -> None:
        """get_available() zwraca tylko dostępnych dostawców."""
        registry = LLMRegistry()
        registry.register(_MockLLM())
        assert len(registry.get_available()) == 1

    def test_get_by_name(self) -> None:
        """get_by_name() zwraca właściwego dostawcę."""
        registry = LLMRegistry()
        llm = _MockLLM()
        registry.register(llm)
        assert registry.get_by_name("mock_llm") is llm
