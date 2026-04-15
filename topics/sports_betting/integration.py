"""Sports Betting — PrizePicks / Odds API / ML model integrations."""
from __future__ import annotations
import os


class SportsBettingTopic:
    name = "sports_betting"
    tools = ["prizepicks-api", "the-odds-api", "pandas", "scikit-learn", "xgboost", "lightgbm", "statsmodels"]

    async def fetch_odds(self, sport: str = "basketball_nba") -> dict:
        api_key = os.getenv("ODDS_API_KEY", "")
        if not api_key:
            return {"error": "ODDS_API_KEY not set"}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"https://api.the-odds-api.com/v4/sports/{sport}/odds",
                    params={"apiKey": api_key, "regions": "us", "markets": "h2h"}
                )
                return r.json()
        except Exception as e:
            return {"error": str(e)}
