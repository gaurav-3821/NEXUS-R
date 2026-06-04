import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch

from modules.state_core.src.memory_engine import SemanticMemoryEngine

@pytest.fixture
async def memory_engine(tmp_path):
    db_path = tmp_path / "test_events.db"
    engine = SemanticMemoryEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()

@pytest.mark.asyncio
async def test_fallback_embedding(memory_engine):
    # Test fallback deterministic hashing
    vec1 = memory_engine._fallback_embed("I prefer dark mode in UI")
    vec2 = memory_engine._fallback_embed("dark mode is my favorite")
    vec3 = memory_engine._fallback_embed("i want to build a backend system")
    
    assert len(vec1) == 384
    sim1_2 = memory_engine._cosine_similarity(vec1, vec2)
    sim1_3 = memory_engine._cosine_similarity(vec1, vec3)
    
    # vec1 and vec2 should be more similar than vec1 and vec3
    assert sim1_2 > sim1_3

@pytest.mark.asyncio
async def test_importance_scoring(memory_engine):
    # Short chat with no real info
    score1 = memory_engine._score_importance("hello", "hi there")
    assert score1 < 0.35
    
    # Chat revealing project and preference
    user_msg = "I'm building a machine learning pipeline and I prefer using PyTorch"
    asst_msg = "That sounds great. I can help with PyTorch and ML pipelines..." * 10
    score2 = memory_engine._score_importance(user_msg, asst_msg)
    assert score2 > 0.5

@pytest.mark.asyncio
async def test_extract_and_recall_memory(memory_engine):
    with patch.object(memory_engine, '_embed', new_callable=AsyncMock) as mock_embed:
        # Mock embedding return
        mock_embed.return_value = [0.1] * 768
        
        # This should trigger memory extraction due to "i prefer"
        # Make assistant message long enough and include tech terms to pass importance threshold
        ids = await memory_engine.extract_memories(
            "i prefer to use functional programming when possible because I like to compose functions and api calls without side effects",
            "Functional programming has many benefits. It allows you to build reliable software pipelines and clear api structures. " * 10,
            conversation_id="conv_1"
        )
        
        assert len(ids) == 1
        
        # Test recall
        mock_embed.return_value = [0.1] * 768  # Same embedding for high similarity
        results = await memory_engine.recall("Do I like functional programming?")
        
        assert len(results) == 1
        assert "functional programming" in results[0]["content"]
        assert results[0]["category"] == "preference"

@pytest.mark.asyncio
async def test_memory_deduplication(memory_engine):
    with patch.object(memory_engine, '_embed', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 768
        
        await memory_engine.extract_memories(
            "my project is an api in rust using database connections",
            "That sounds like a great project. Writing an API in rust with database is fast and safe. " * 10,
            "conv_1"
        )
        
        # Same conceptual memory, mock gives same embedding -> should dedup
        ids = await memory_engine.extract_memories(
            "my project is an api built using rust and database",
            "Awesome, rust is great for an API and database backend. " * 10,
            "conv_2"
        )
        assert len(ids) == 0
        
        # Check reinforcement count
        stats = await memory_engine.get_stats()
        assert stats["total_memories"] == 1
