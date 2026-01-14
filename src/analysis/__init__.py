"""Analysis Module - Technical indicators and stock analysis"""

# Import classes lazily to avoid circular imports
def __getattr__(name):
    if name == "Indicators":
        from .indicators import Indicators
        return Indicators
    elif name == "TechnicalIndicators":
        from .indicators import TechnicalIndicators
        return TechnicalIndicators
    elif name == "SignalGenerator":
        from .indicators import SignalGenerator
        return SignalGenerator
    elif name == "StockScorer":
        from .stock_scorer import StockScorer
        return StockScorer
    elif name == "PreMarketAnalyzer":
        from .pre_market import PreMarketAnalyzer
        return PreMarketAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['Indicators', 'TechnicalIndicators', 'SignalGenerator', 'StockScorer', 'PreMarketAnalyzer']
