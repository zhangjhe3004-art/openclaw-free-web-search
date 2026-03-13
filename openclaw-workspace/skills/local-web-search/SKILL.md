---
name: local-web-search
description: >
  Free, private, real-time web search using a self-hosted local SearXNG instance.
  Powered by Scrapling for anti-bot bypass (Cloudflare, JS-heavy sites).
  Supports multi-engine parallel search (Bing/DuckDuckGo/Google/Startpage/Qwant),
  intent-aware query expansion (Agent Reach), three-tier Browse/Viewing
  (Fetcher → StealthyFetcher → DynamicFetcher), cross-engine anti-hallucination
  validation, invalid page filtering, and automatic public fallback.
  Zero API keys required. Use for current events, latest releases, research,
  comparisons, tutorials, or any query requiring live internet search.
---

# Local Free Web Search v3.0

Use this skill when the user needs current or real-time web information.
Powered by **Scrapling** (anti-bot) + **SearXNG** (self-hosted search).
Zero API keys. Zero cost. Runs entirely locally.

---

## Tool 1 — Web Search

```bash
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/search_local_web.py \
  --query "YOUR QUERY" \
  --intent general \
  --limit 5
```

**Intent options** (controls engine selection + query expansion):

| Intent | Best for |
|---|---|
| `general` | Default, mixed queries |
| `factual` | Facts, definitions, official docs |
| `news` | Latest events, breaking news |
| `research` | Papers, GitHub, technical depth |
| `tutorial` | How-to guides, code examples |
| `comparison` | A vs B, pros/cons |
| `privacy` | Sensitive queries (ddg/startpage/qwant only) |

**Additional flags:**

| Flag | Description |
|---|---|
| `--engines bing,duckduckgo,...` | Override engine selection |
| `--freshness hour\|day\|week\|month\|year` | Filter by recency |
| `--max-age-days N` | Downrank results older than N days |
| `--browse` | Auto-fetch top result with browse_page.py |
| `--no-expand` | Disable Agent Reach query expansion |
| `--json` | Machine-readable JSON output |

---

## Tool 2 — Browse/Viewing (read full page)

```bash
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/browse_page.py \
  --url "https://example.com/article" \
  --max-words 600
```

**Fetcher modes** (use `--mode` flag):

| Mode | Fetcher | Use case |
|---|---|---|
| `auto` | Tier 1 → 2 → 3 | Default — tries fast first |
| `fast` | `Fetcher` | Normal sites |
| `stealth` | `StealthyFetcher` | Cloudflare / anti-bot sites |
| `dynamic` | `DynamicFetcher` | Heavy JS / SPA sites |

Returns: title, published date, word count, confidence (HIGH/MEDIUM/LOW),
full extracted text, and anti-hallucination advisory.

---

## Recommended Workflow

1. Run `search_local_web.py` — review results by Score and `[cross-validated]` tag
2. Run `browse_page.py` on the top URL — check Confidence level
3. If Confidence is LOW (paywall/blocked) — retry with `--mode stealth` or try next URL
4. Answer only after reading HIGH-confidence page content
5. **Never state facts from snippets alone**

---

## Rules

- Always use `--intent` to match the query type for best results.
- When local SearXNG is unavailable, both scripts automatically fall back to `searx.be`.
- If the fallback also fails, tell the user to start local SearXNG:

```bash
cd "$(cat ~/.openclaw/workspace/skills/local-web-search/.project_root)" && ./start_local_search.sh
```

- Do NOT invent search results if all sources fail.
- `search_local_web.py` and `browse_page.py` are complementary: **search first, browse second**.
- Prefer `[cross-validated]` results (appeared in multiple engines) for factual claims.
- For sites behind Cloudflare or requiring JS, use `browse_page.py --mode stealth`.
