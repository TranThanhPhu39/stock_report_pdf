import unittest
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from src.analysis.news import build_news_digest
from src.data.research import collect_peer_news, company_news_url, parse_company_news


class NewsDigestTests(unittest.TestCase):
    def test_kbs_news_url_requests_twelve_items(self):
        params = parse_qs(urlsplit(company_news_url("HPG")).query)
        self.assertEqual(params["p"], ["12"])
        self.assertEqual(params["s"], ["1"])

    def test_sorts_deduplicates_and_limits_headlines(self):
        digest = build_news_digest([
            {"title": "Tin cũ", "published_at": "2026-09-01", "url": "https://example.test/old"},
            {"title": "Tin mới", "published_at": "2026-10-01", "url": "https://example.test/new"},
            {"title": "Tin mới", "published_at": "2026-10-01", "url": "https://example.test/new"},
            {"title": "Thiếu ngày", "published_at": "không rõ", "url": "https://example.test/bad"},
        ], limit=1)
        self.assertEqual(digest["count"], 2)
        self.assertEqual(digest["first_date"], "2026-09-01")
        self.assertEqual(digest["latest_date"], "2026-10-01")
        self.assertEqual([item["title"] for item in digest["headlines"]], ["Tin mới"])
        self.assertEqual([group["date"] for group in digest["groups"]], ["2026-10-01", "2026-09-01"])
        self.assertIn("trích yếu từ feed KBS", digest["summary"])

    def test_company_feed_excerpt_is_kept_and_future_news_is_filtered(self):
        parsed = parse_company_news([
            {"Title": "Tin có nội dung", "Head": "<p>Tóm lược gốc từ nguồn.</p>",
             "PublishTime": "2026-10-08T12:00:00", "URL": "/tin-1.htm"},
            {"Title": "Tin tương lai", "Head": "Không dùng", "PublishTime": "2026-10-10T12:00:00",
             "URL": "/tin-2.htm"},
            {"Title": "Tin ngày lỗi", "PublishTime": "không rõ", "URL": "/tin-3.htm"},
        ], "HPG", "KBS_NEWS", date(2026, 10, 9))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["summary"], "Tóm lược gốc từ nguồn.")
        self.assertEqual(parsed[0]["summary_source"], "KBS news feed Head")
        self.assertEqual(parsed[0]["url"], "https://vietstock.vn/tin-1.htm")

    def test_empty_feed_returns_explicit_empty_summary(self):
        digest = build_news_digest([])
        self.assertEqual(digest["count"], 0)
        self.assertIsNone(digest["latest_date"])
        self.assertEqual(digest["headlines"], [])

    def test_peer_news_is_limited_tagged_and_sourced(self):
        payload = json.dumps([{
            "Title": "Bank peer report", "Head": "Peer KBS excerpt",
            "PublishTime": "2026-10-08T12:00:00", "URL": "/bank-news.htm",
        }]).encode()
        with TemporaryDirectory() as folder, patch("src.data.research.download", return_value=payload) as download:
            articles, sources, errors = collect_peer_news(
                ["AAA", "BBB", "CCC", "DDD"], date(2026, 10, 9), Path(folder), "fixture", limit=2,
            )
        self.assertEqual(download.call_count, 2)
        self.assertEqual(len(articles), 2)
        self.assertTrue(all(item["news_scope"] == "industry_peer" for item in articles))
        self.assertTrue(all(item["summary_source"] == "KBS news feed Head" for item in articles))
        self.assertEqual(len(sources), 2)
        self.assertFalse(errors)


if __name__ == "__main__":
    unittest.main()