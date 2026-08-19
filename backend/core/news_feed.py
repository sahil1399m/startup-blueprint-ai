import requests
import os
from datetime import datetime, timedelta

def get_startup_news(api_key, query="India startup funding", page_size=6):
    """Fetch live startup news using NewsAPI"""
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "language": "en",
            "apiKey": api_key
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("status") == "ok":
            return data.get("articles", [])
        return []
    except Exception:
        return []

def get_trending_sectors(api_key):
    """Get trending startup sectors"""
    queries = ["fintech India 2025", "edtech startup India", "agritech startup funding"]
    results = {}
    for q in queries:
        articles = get_startup_news(api_key, query=q, page_size=2)
        sector = q.split()[0].capitalize()
        results[sector] = len(articles)
    return results

def search_market_data(serper_key, query):
    """Search live market data using Serper"""
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        results = []
        for item in data.get("organic", [])[:5]:
            results.append({
                "title": item.get("title",""),
                "snippet": item.get("snippet",""),
                "link": item.get("link","")
            })
        return results
    except Exception:
        return []
