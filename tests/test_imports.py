"""Test that all modules can be imported."""


def test_import_modules():
    """Verify all src modules can be imported."""
    from src import market_data
    from src import database
    from src import llm_interface
    from src import trading_engine
    from src import risk_manager
    from src import learning_system
    from src import dashboard
    assert True
