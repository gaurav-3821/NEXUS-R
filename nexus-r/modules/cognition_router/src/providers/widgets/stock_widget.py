import re
import httpx
import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.stock_widget")

TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
STOCK_KEYWORDS = ["stock", "price", "share", "market", "ticker"]

class StockWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        has_ticker = bool(TICKER_PATTERN.search(query))
        has_keyword = any(kw in query.lower() for kw in STOCK_KEYWORDS)
        return has_ticker or has_keyword

    async def execute(self, context) -> WidgetResult | None:
        query = getattr(context, "raw_input", "") or ""

        tickers = TICKER_PATTERN.findall(query)
        if not tickers:
            word_ticker = self._extract_word_ticker(query)
            if word_ticker:
                tickers = [word_ticker]

        if not tickers:
            return None

        symbol = tickers[0]
        data = await self._fetch_quote(symbol)
        if not data:
            return WidgetResult(
                widget_type="stock",
                data={"error": f"Could not fetch data for {symbol}"},
                title=f"Stock: {symbol}",
                priority=4,
            )

        return WidgetResult(
            widget_type="stock",
            data={
                "symbol": symbol,
                "price": data.get("regularMarketPrice") or data.get("currentPrice"),
                "change": data.get("regularMarketChange"),
                "change_percent": data.get("regularMarketChangePercent"),
                "volume": data.get("regularMarketVolume"),
                "market_open": data.get("regularMarketTime") is not None,
            },
            title=f"Stock: {symbol}",
            priority=4,
        )

    def _extract_word_ticker(self, query: str) -> str | None:
        words = query.lower().split()
        for i, w in enumerate(words):
            if w in ("stock", "price", "ticker") and i + 1 < len(words):
                candidate = words[i + 1].upper().strip(",.!?")
                if re.match(r'^[A-Z]{1,5}$', candidate):
                    return candidate
        return None

    async def _fetch_quote(self, symbol: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                resp = await client.get(url, params={"range": "1d", "interval": "1d"})
                resp.raise_for_status()
                data = resp.json()
                result = data.get("chart", {}).get("result", [])
                if not result:
                    return None
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("chartPreviousClose")
                change = (price - prev_close) if (price is not None and prev_close is not None) else None
                change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
                return {
                    "regularMarketPrice": price,
                    "regularMarketChange": change,
                    "regularMarketChangePercent": change_pct,
                    "regularMarketVolume": meta.get("regularMarketVolume"),
                    "regularMarketTime": meta.get("regularMarketTime"),
                    "currentPrice": price,
                }
        except Exception as e:
            logger.warning(f"Stock fetch failed for {symbol}: {e}")
        return None
