"""Finance / Trading — Alpaca / CCXT / Backtrader integrations."""
from __future__ import annotations
import os


class FinanceTradingTopic:
    name = "finance_trading"
    tools = ["alpaca", "ccxt", "backtrader", "zipline", "quantlib", "pandas-ta", "vectorbt"]

    async def get_crypto_price(self, symbol: str = "BTC/USDT", exchange: str = "binance") -> dict:
        try:
            import ccxt.async_support as ccxt_a
            ex = getattr(ccxt_a, exchange)()
            ticker = await ex.fetch_ticker(symbol)
            await ex.close()
            return {"symbol": symbol, "price": ticker["last"]}
        except ImportError:
            return {"error": "ccxt not installed"}
