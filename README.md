# OpenClaw Free Web Search v4.0

> **Zero-cost, zero-API-key, privacy-first web search for OpenClaw.**  
> Self-hosted SearXNG + **Scrapling anti-bot engine** + multi-source **cross-validation** to eliminate AI hallucinations.

[中文文档](./README_zh.md)

---

## What's New in v4.0 — Cross-Validation Engine

The only free OpenClaw web search skill that tells you **how much to trust the answer**.

| Feature | Description |
|---|---|
| **`verify_claim.py`** | New third tool: multi-source factual cross-validation |
| **Multi-source consensus** | Fetches 3–10 independent sources, checks agreement/contradiction |
| **Authority-weighted scoring** | Wikipedia/Reuters/official sites count 3×; Medium/Reddit count 1× |
| **Verdict system** | ✅ VERIFIED / 🟢 LIKELY_TRUE / 🟡 UNCERTAIN / 🔴 LIKELY_FALSE / ⬜ UNVERIFIABLE |
| **`--urls` direct mode** | Verify against known URLs without SearXNG (works offline) |
| **Recency scoring** | Sources older than 2 years are down-weighted automatically |
| **Scrapling-powered** | All source fetching uses TLS fingerprint spoofing + Cloudflare bypass |

---

## Three-Tool Architecture

```
OpenClaw Agent
    │
    ├── 1. search_local_web.py   ← "Find relevant URLs"
    │       ├── Intent-aware query expansion (Agent Reach)
    │       ├── Parallel multi-engine: Bing + DDG + Google + Startpage + Qwant
    │       ├── Quality scoring (authority + freshness + cross-engine count)
    │       ├── Paywall / 404 / login-wall filter
    │       └── SearXNG (local Docker) → public fallback
    │
    ├── 2. browse_page.py        ← "Read a page deeply"
    │       ├── Tier 1: Scrapling Fetcher (TLS fingerprint, ~1-3s)
    │       ├── Tier 2: StealthyFetcher (Cloudflare bypass, ~5-15s)
    │       ├── Tier 3: DynamicFetcher (full Playwright JS, ~10-30s)
    │       ├── Tier 4: stdlib urllib (no-Scrapling fallback)
    │       ├── Adaptive CSS content extraction
    │       ├── Paywall detection + publication date extraction
    │       └── Confidence: HIGH / MEDIUM / LOW
    │
    └── 3. verify_claim.py       ← "How much should I trust this?"
            ├── Expands claim into 3 search queries
            ├── Fetches 3–10 independent sources in parallel
            ├── Classifies each source: AGREE / CONTRADICT / NEUTRAL
            ├── Authority-weighted confidence score (0–100%)
            ├── Cross-agreement bonus (sources that agree boost each other)
            └── Verdict: VERIFIED / LIKELY_TRUE / UNCERTAIN / LIKELY_FALSE / UNVERIFIABLE
```

---

## Recommended Workflow

```
User question
    │
    ▼
search_local_web.py  →  get top 5 URLs + quality scores
    │
    ▼
browse_page.py       →  read full content of top 1–2 URLs
    │                   check Confidence (HIGH / MEDIUM / LOW)
    ▼
verify_claim.py      →  cross-validate key facts before answering
    │                   VERIFIED / LIKELY_TRUE → answer confidently
    │                   UNCERTAIN / LIKELY_FALSE → say so explicitly
    ▼
Answer with citations + confidence level
```

---

## Requirements

- macOS (Apple Silicon or Intel)
- Docker Desktop (for SearXNG)
- Python 3.8+
- OpenClaw desktop app

**Optional but strongly recommended (enables anti-bot bypass):**

```bash
pip install scrapling[all]
python -m playwright install chromium
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/wd041216-bit/openclaw-free-web-search.git
cd openclaw-free-web-search

# 2. Install everything (SearXNG + Scrapling + Playwright)
./install_local_search.sh

# 3. Start SearXNG
./start_local_search.sh

# 4. Sync skill into OpenClaw workspace
./sync_openclaw_workspace.sh

# 5. Restart OpenClaw — all three tools are now active
```

---

## Usage

### 1. Web Search

```bash
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/search_local_web.py \
  --query "Claude 4 release date" --intent news --limit 5

# Search + auto-browse top result
python3 ... --query "UW iSchool dean" --intent factual --browse

# Downrank old results
python3 ... --query "Python best practices" --max-age-days 90
```

### 2. Browse a Page

```bash
# Auto mode (Scrapling cascade: fast → stealth → dynamic)
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/browse_page.py \
  --url "https://anthropic.com/news/..." --max-words 600

# Force stealth (Cloudflare-protected sites)
python3 ... --url "https://..." --mode stealth

# Full JS rendering (SPAs, React apps)
python3 ... --url "https://..." --mode dynamic
```

### 3. Verify a Claim

```bash
# Auto mode: SearXNG finds sources automatically
python3 ~/.openclaw/workspace/skills/local-web-search/scripts/verify_claim.py \
  --claim "Claude 3.7 Sonnet was released by Anthropic in February 2025" \
  --sources 5

# Direct URL mode: no SearXNG needed
python3 ... \
  --claim "Claude 3.7 Sonnet was released by Anthropic in February 2025" \
  --urls https://anthropic.com/news/claude-3-7-sonnet \
         https://en.wikipedia.org/wiki/Claude_(language_model)

# Machine-readable JSON output
python3 ... --claim "..." --json
```

**Example output:**

```
VERDICT    : 🟢 LIKELY_TRUE
CONFIDENCE : 67%
SOURCES    : 3 checked  (2 agree / 0 contradict / 1 neutral)
MODE       : FULL (Scrapling + StealthyFetcher)

[1] ✅ anthropic.com  [HIGH]  score=0.83
    Excerpt: "Claude 3.7 Sonnet and Claude Code Feb 24, 2025 Today, we're announcing..."

[2] ✅ en.wikipedia.org  [HIGH]  score=0.83

[3] ➖ techcrunch.com  [HIGH]  score=0.46
```

---

## Verdict Reference

| Verdict | Confidence | Meaning |
|---|---|---|
| ✅ VERIFIED | ≥ 75% | Multiple high-authority sources agree |
| 🟢 LIKELY_TRUE | 55–74% | Majority of sources support the claim |
| 🟡 UNCERTAIN | 35–54% | Mixed or insufficient evidence |
| 🔴 LIKELY_FALSE | 15–34% | Multiple sources contradict the claim |
| ⬜ UNVERIFIABLE | < 15% | Cannot find relevant sources |

---

## Intent Options (search_local_web.py)

| Intent | Best for | Engines used |
|---|---|---|
| `general` | Default | bing, ddg, google |
| `factual` | Facts, docs, definitions | bing, google, ddg |
| `news` | Breaking news, recent events | bing, ddg, google |
| `research` | Papers, GitHub, technical | google, startpage, bing |
| `tutorial` | How-to, code examples | google, bing, ddg |
| `comparison` | A vs B, reviews | google, bing, startpage |
| `privacy` | Sensitive queries | ddg, startpage, qwant |

---

## Fetcher Modes (browse_page.py)

| Mode | Engine | Use case | Speed |
|---|---|---|---|
| `auto` | Tier 1 → 2 → 3 | Default, tries fastest first | variable |
| `fast` | Scrapling `Fetcher` | Normal sites, TLS spoof | ~1–3s |
| `stealth` | `StealthyFetcher` | Cloudflare, anti-bot | ~5–15s |
| `dynamic` | `DynamicFetcher` | Heavy JS / SPA | ~10–30s |

---

## Management

```bash
./start_local_search.sh    # Start SearXNG
./stop_local_search.sh     # Stop SearXNG
./doctor.sh                # Health check (SearXNG + Scrapling + Playwright)
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOCAL_SEARCH_URL` | `http://127.0.0.1:18080` | Local SearXNG base URL |
| `LOCAL_SEARCH_FALLBACK_URL` | `https://searx.be` | Public fallback when local is down |

---

## Comparison with Other Free Skills

| Skill | Search | Browse | Anti-bot | Cross-Validation | Install |
|---|---|---|---|---|---|
| **This skill (v4.0)** | ✅ Multi-engine | ✅ 3-tier Scrapling | ✅ Cloudflare bypass | ✅ Multi-source verdict | One-click |
| `hugoreno/scrapling-browse` | ❌ None | ✅ Scrapling | ✅ | ❌ None | Manual |
| `keef-agent/openclaw-scrapling` | ❌ None | ✅ Scrapling | ✅ | ❌ None | Manual |
| Generic SearXNG skills | ✅ Single-engine | ❌ `web_fetch` only | ❌ | ❌ None | Manual |

---

## License

MIT © 2025
