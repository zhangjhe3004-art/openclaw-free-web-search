# OpenClaw Free Web Search v3.0

> **Zero-cost, zero-API-key, privacy-first web search for OpenClaw.**  
> Self-hosted SearXNG + **Scrapling anti-bot engine** + multi-engine parallel search + Browse/Viewing.

[中文文档](./README_zh.md)

---

## What's New in v3.0

| Feature | Description |
|---|---|
| **Scrapling integration** | `browse_page.py` now uses Scrapling's three-tier fetcher cascade |
| **TLS fingerprint spoofing** | Realistic Chrome TLS fingerprint — bypasses most anti-bot checks |
| **Cloudflare bypass** | `StealthyFetcher` handles Cloudflare Turnstile automatically |
| **Full JS rendering** | `DynamicFetcher` (Playwright) for heavy JS / SPA sites |
| **Adaptive CSS extraction** | Priority-based selector chain survives website redesigns |
| **Upgraded quality score** | Now includes snippet density + title quality |
| **`--browse` flag** | Auto-fetch top search result immediately after search |
| **`--max-age-days`** | Downrank results older than N days |
| **stdlib fallback** | All features degrade gracefully without Scrapling |

---

## v2.0 Features (still included)

| Feature | Description |
|---|---|
| **Agent Reach** | Intent-aware query expansion — one query becomes 2–3 sub-queries |
| **Multi-engine parallel** | Bing, DuckDuckGo, Google, Startpage, Qwant run simultaneously |
| **Anti-hallucination** | Cross-engine validation + domain authority scoring + confidence levels |
| **Invalid page filter** | Auto-removes paywalls, 404s, login walls, JS-only pages |
| **Deduplication** | URL-level dedup + cross-engine appearance counting |
| **Public fallback** | Auto-falls back to `searx.be` if local SearXNG is down |

---

## Requirements

- macOS (Apple Silicon or Intel)
- Docker Desktop (for SearXNG)
- Python 3.8+
- OpenClaw desktop app

**Optional but strongly recommended:**

```bash
pip install scrapling[all]   # enables anti-bot bypass + JS rendering
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/wd041216-bit/openclaw-free-web-search.git
cd openclaw-free-web-search

# 2. Install Scrapling (optional but recommended)
pip install scrapling[all]

# 3. Install SearXNG (one-time)
./install_local_search.sh

# 4. Start SearXNG
./start_local_search.sh

# 5. Sync skill into OpenClaw workspace
./sync_openclaw_workspace.sh

# 6. Restart OpenClaw — the skill is now active
```

---

## Usage

### Web Search

```bash
# Basic search
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/search_local_web.py \
  --query "OpenAI latest model" --intent factual --limit 5

# Search + auto-browse top result
python3 ... --query "UW iSchool dean" --browse

# News with freshness filter
python3 ... --query "AI news" --intent news --freshness day

# Downrank old results
python3 ... --query "Python best practices" --max-age-days 90
```

### Browse a Page

```bash
# Auto mode (tries fast → stealth → dynamic)
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/browse_page.py \
  --url "https://openai.com/blog/..." --max-words 600

# Force stealth mode (Cloudflare sites)
python3 ... --url "https://..." --mode stealth

# Full JS rendering
python3 ... --url "https://..." --mode dynamic
```

### Fetcher Modes

| Mode | Engine | Use case | Speed |
|---|---|---|---|
| `auto` | Tier 1 → 2 → 3 | Default | variable |
| `fast` | `Fetcher` | Normal sites | ~1-3s |
| `stealth` | `StealthyFetcher` | Cloudflare / anti-bot | ~5-15s |
| `dynamic` | `DynamicFetcher` | Heavy JS / SPA | ~10-30s |

### Intent Options

| Intent | Best for | Engines |
|---|---|---|
| `general` | Default | bing, ddg, google |
| `factual` | Facts, docs | bing, google, ddg |
| `news` | Breaking news | bing, ddg, google |
| `research` | Papers, GitHub | google, startpage, bing |
| `tutorial` | How-to, examples | google, bing, ddg |
| `comparison` | A vs B | google, bing, startpage |
| `privacy` | Sensitive queries | ddg, startpage, qwant |

---

## Recommended Workflow

```
1. search_local_web.py  →  review Score + [cross-validated] results
2. browse_page.py       →  read full content, check Confidence level
   - LOW + JS site      →  retry with --mode stealth or --mode dynamic
3. HIGH confidence      →  safe to answer
4. LOW confidence       →  try next URL, never fabricate
```

---

## Management

```bash
./start_local_search.sh    # Start SearXNG
./stop_local_search.sh     # Stop SearXNG
./doctor.sh                # Health check
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOCAL_SEARCH_URL` | `http://127.0.0.1:18080` | Local SearXNG base URL |
| `LOCAL_SEARCH_FALLBACK_URL` | `https://searx.be` | Public fallback |

---

## Architecture

```
OpenClaw Agent
    │
    ├── search_local_web.py (v3.0)
    │       ├── Scrapling Fetcher (TLS fingerprint + Google referer)
    │       ├── ThreadPoolExecutor (parallel multi-engine)
    │       ├── Agent Reach query expansion
    │       ├── Quality scoring (authority + freshness + cross-validation + density)
    │       └── SearXNG (local) → searx.be (fallback)
    │
    └── browse_page.py (v3.0)
            ├── Tier 1: Scrapling Fetcher (fast, TLS spoof)
            ├── Tier 2: StealthyFetcher (Cloudflare bypass)
            ├── Tier 3: DynamicFetcher (full Playwright JS)
            ├── Tier 4: stdlib urllib (no-Scrapling fallback)
            ├── Adaptive CSS content extraction
            ├── Paywall / login-wall detection
            ├── Publication date extraction (meta + JSON-LD + text)
            └── Confidence scoring + hallucination guard
```

---

## License

MIT © 2025
