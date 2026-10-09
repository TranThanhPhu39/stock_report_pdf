"""Create a transparent headline digest from sourced company news."""

from datetime import date


def build_news_digest(items: list[dict], limit: int = 4) -> dict:
	headlines = []
	seen = set()
	for item in items or []:
		title = str(item.get("title") or "").strip()
		published_at = str(item.get("published_at") or "")[:10]
		try:
			date.fromisoformat(published_at)
		except ValueError:
			continue
		if not title:
			continue
		url = str(item.get("url") or "").strip()
		identity = url or (published_at, title.casefold())
		if identity in seen:
			continue
		seen.add(identity)
		headlines.append({
			"title": title,
			"published_at": published_at,
			"url": url,
			"summary": str(item.get("summary") or "").strip(),
			"summary_source": item.get("summary_source"),
			"source_id": item.get("source_id"),
			"ticker": str(item.get("ticker") or "").strip().upper(),
			"news_scope": item.get("news_scope") or "company",
		})

	headlines.sort(key=lambda item: (item["published_at"], item["ticker"], item["title"].casefold()), reverse=True)
	if not headlines:
		return {
			"count": 0,
			"first_date": None,
			"latest_date": None,
			"headlines": [],
			"groups": [],
			"scope_counts": {"company": 0, "industry_peer": 0},
			"summary": "Nguồn hiện chưa trả về tin tài chính phù hợp.",
		}

	grouped = {}
	for headline in headlines:
		grouped.setdefault(headline["published_at"], []).append(headline)
	groups = [{"date": day, "articles": articles} for day, articles in sorted(grouped.items(), reverse=True)]
	excerpt_count = sum(bool(headline["summary"]) for headline in headlines)
	return {
		"count": len(headlines),
		"first_date": headlines[-1]["published_at"],
		"latest_date": headlines[0]["published_at"],
		"headlines": headlines[:max(1, limit)],
		"groups": groups,
		"scope_counts": {
			"company": sum(item["news_scope"] == "company" for item in headlines),
			"industry_peer": sum(item["news_scope"] == "industry_peer" for item in headlines),
		},
		"summary": (
			f"Nguồn trả về {len(headlines)} tin từ {headlines[-1]['published_at']} "
			f"đến {headlines[0]['published_at']}; {excerpt_count} tin có trích yếu từ feed KBS."
		),
	}
