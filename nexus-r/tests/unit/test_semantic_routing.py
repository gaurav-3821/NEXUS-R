from __future__ import annotations

import math
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import httpx

from nexus_r.config import NEXUSConfig
from foundation.nexus_r.model_registry import ModelRegistry


@pytest.fixture
def registry():
    tmp = Path(tempfile.mkdtemp(prefix="nexus_registry_test_"))
    config = NEXUSConfig.default(tmp)
    from modules.trust_layer.src.secret_registry import SecretRegistry
    secrets = SecretRegistry(config.app_name)
    r = ModelRegistry(config, secrets)
    yield r
    try:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass


class TestCosineSimilarity:
    def test_identical_vectors_return_one(self, registry):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        similarity = registry._compute_cosine_similarity(a, b)
        assert math.isclose(similarity, 1.0, rel_tol=1e-5)

    def test_orthogonal_vectors_return_zero(self, registry):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        similarity = registry._compute_cosine_similarity(a, b)
        assert math.isclose(similarity, 0.0, abs_tol=1e-5)

    def test_opposite_vectors_return_minus_one(self, registry):
        a = [1.0, 1.0]
        b = [-1.0, -1.0]
        similarity = registry._compute_cosine_similarity(a, b)
        assert math.isclose(similarity, -1.0, rel_tol=1e-5)

    def test_zero_vector_returns_zero(self, registry):
        a = [0.0, 0.0]
        b = [1.0, 2.0]
        assert registry._compute_cosine_similarity(a, b) == 0.0


class TestSemanticRoutingIntent:
    def test_coding_semantic_intent_matches_coder_model(self, registry):
        # We mock available local models to include qwen2.5-coder
        available_models = [{"name": "qwen2.5-coder:7b"}, {"name": "gemma2:9b"}]
        
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            # We mock the embedding fetcher: 
            # When prompt is "write python", return a specific embedding
            # When prompt is one of the coding anchors, return similar embedding
            # When prompt is a math/creative anchor, return orthogonal embedding
            def mock_get_embed(text, local_models=None):
                if "python" in text or "coder" in text or "sql" in text or "javascript" in text or "FastAPI" in text or "rust" in text or "conflicts" in text or "inheritance" in text:
                    return [1.0, 0.0, 0.0, 0.0]
                elif "solve" in text or "integral" in text or "statistics" in text or "derivative" in text or "regression" in text or "theorem" in text:
                    return [0.0, 1.0, 0.0, 0.0]
                elif "story" in text or "poem" in text or "essay" in text or "blog" in text or "detectives" in text or "recipe" in text:
                    return [0.0, 0.0, 1.0, 0.0]
                else:
                    return [0.0, 0.0, 0.0, 1.0]

            with patch.object(registry, "_get_embedding", side_effect=mock_get_embed):
                # Request a coding prompt
                selected = registry._get_dynamic_local_model("write a python algorithm")
                
                assert "qwen2.5-coder" in selected
                assert "Coding" in registry._last_model_reason

    def test_math_reasoning_semantic_intent_matches_reasoning_model(self, registry):
        available_models = [{"name": "deepseek-r1:8b"}, {"name": "gemma2:9b"}]
        
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            def mock_get_embed(text, local_models=None):
                if "solve" in text or "integral" in text or "statistics" in text or "derivative" in text or "regression" in text or "theorem" in text or "quadratic" in text:
                    return [1.0, 0.0, 0.0, 0.0]
                else:
                    return [0.0, 1.0, 0.0, 0.0]

            with patch.object(registry, "_get_embedding", side_effect=mock_get_embed):
                selected = registry._get_dynamic_local_model("solve this equation please")
                
                assert "deepseek-r1" in selected
                assert "Math & Reasoning" in registry._last_model_reason

    def test_fallback_when_semantic_similarity_is_low(self, registry):
        available_models = [{"name": "gemma2:9b"}]
        
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            # Low/orthogonal embedding vector for everything
            def mock_get_embed(text, local_models=None):
                return [0.05, 0.05, 0.05, 0.05]

            with patch.object(registry, "_get_embedding", side_effect=mock_get_embed):
                selected = registry._get_dynamic_local_model("completely unrelated random prompt text")
                
                assert "fallback" in registry._last_model_reason.lower()

    @pytest.mark.asyncio
    async def test_manual_model_lock_bypass(self, registry):
        # Configure the local model to be a specific locked model, not 'auto'
        registry.config.models.local_model = "ollama/gemma2:9b"
        registry.local.is_available = True
        
        # Mock _get_dynamic_local_model to ensure it is NOT called
        with patch.object(registry, "_get_dynamic_local_model") as mock_dynamic:
            with patch.object(registry, "_litellm_completion") as mock_litellm:
                mock_litellm.return_value = MagicMock()
                
                # Execute _invoke on the local provider
                await registry._invoke(registry.local, "some math code writing greeting prompt", False)
                
                # Assert that dynamic routing was bypassed
                mock_dynamic.assert_not_called()
                assert registry.local.name == "ollama/gemma2:9b"
                assert "Manual override active" in registry._last_model_reason


class TestEmbeddingFallbackEngine:
    def test_sentence_transformer_preferred_when_available(self, registry):
        # We mock imports so that SentenceTransformer loads successfully
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
            from sentence_transformers import SentenceTransformer
            with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
                # Trigger lazy-load check
                registry._sentence_transformer_loaded = False
                vector = registry._get_embedding("test query", [])
                
                assert vector == [0.1, 0.2, 0.3]
                assert registry._sentence_transformer_loaded is True

    def test_ollama_fallback_when_package_missing(self, registry):
        # Ensure sentence-transformers fails to import
        with patch("builtins.__import__", side_effect=ImportError):
            registry._sentence_transformer_loaded = False
            
            # Mock Ollama HTTP post response
            with patch.object(httpx, "post") as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=200, 
                    json=lambda: {"embeddings": [[0.5, 0.6, 0.7]]}
                )
                
                vector = registry._get_embedding("test query", ["gemma2:9b"])
                
                assert vector == [0.5, 0.6, 0.7]
                assert registry._sentence_transformer_loaded is False

    def test_graceful_dummy_fallback_when_offline(self, registry):
        # Ensure imports fail and Ollama connection fails (raises Exception)
        with patch("builtins.__import__", side_effect=ImportError):
            registry._sentence_transformer_loaded = False
            
            with patch.object(httpx, "post", side_effect=httpx.ConnectError("Connection refused")):
                vector = registry._get_embedding("test query", [])
                
                # Check that it returns a non-empty zero/dummy list of floats
                assert len(vector) == 384
                assert all(v == 0.0 for v in vector)


class TestHeuristicsBypass:
    def test_trivial_greeting_bypass(self, registry):
        available_models = [{"name": "gemma2:9b"}]
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            # This should immediately hit Heuristic 1 without calling _get_embedding!
            with patch.object(registry, "_get_embedding") as mock_embed:
                selected = registry._get_dynamic_local_model("hi")
                assert "gemma2" in selected
                assert "Heuristic match (Trivial Greeting)" in registry._last_model_reason
                mock_embed.assert_not_called()

    def test_explicit_code_block_bypass(self, registry):
        available_models = [{"name": "qwen2.5-coder:7b"}]
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            # This should hit Heuristic 2!
            with patch.object(registry, "_get_embedding") as mock_embed:
                selected = registry._get_dynamic_local_model("```python\nprint('hello')\n```")
                assert "qwen2.5-coder" in selected
                assert "Heuristic match (Code Syntax Block detected)" in registry._last_model_reason
                mock_embed.assert_not_called()

    def test_long_prompt_bypass(self, registry):
        available_models = [{"name": "gemma2:9b"}]
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": available_models})
            
            # Generate a prompt of 300 words
            long_prompt = "hello " * 300
            with patch.object(registry, "_get_embedding") as mock_embed:
                selected = registry._get_dynamic_local_model(long_prompt)
                assert "gemma2" in selected
                assert "Heuristic match (Long Prompt" in registry._last_model_reason
                mock_embed.assert_not_called()

