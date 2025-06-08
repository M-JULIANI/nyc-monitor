"""Simple smoke test to verify test infrastructure is working."""


def test_basic_import():
    """Test that we can import the main modules."""
    from rag.config import get_config
    from rag.main import app

    # Should not raise any errors
    config = get_config()
    assert config is not None
    assert app is not None
