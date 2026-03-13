#!/usr/bin/env python3
"""
search_local_web.py - OpenClaw Free Web Search v2.0
Multi-engine parallel search via local SearXNG.
Zero API keys required. 100% free and private.

Features:
- Agent Reach        : intent-aware query expansion
- Multi-engine       : parallel Bing/DuckDuckGo/Google/Startpage/Qwant
- Anti-hallucination : cross-engine validation + domain authority scoring
- Invalid page filter: removes paywalls, error pages, low-quality domains
- Deduplication      : URL-level dedup + cross-engine count
- Fallback chain     : local SearXNG -> public fallback -> graceful error

Usage:
  python3 search_local_web.py --query "OpenAI latest model" --limit 5
  python3 search_local_web.py --query "python async" --intent tutorial
  python3 search_local_web.py --query "vscode vs cursor" --intent comparison
  python3 search_local_web.py --query "AI news" --intent news --freshness day
"""

from __future__ import annotations
import argparse, json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

DEFAULT_LOCAL_URL   = os.environ.get("LOCAL_SEARCH_URL", "http://127.0.0.1:18080")
PUBLIC_FALLBACK_URL = os.environ.get("LOCAL_SEARCH_FALLBACK_URL", "https://searx.be")
ALL_ENGINES = ["bing", "duckduckgo", "google", "startpage", "qwant"]

INTENT_ENGINE_MAP = {
    "factual":    ["bing", "google", "duckduckgo"],
    "news":       ["bing", "duckduckgo", "google"],
    "research":   ["google", "startpage", "bing"],
    "tutorial":   ["google", "bing", "duckduckgo"],
    "comparison": ["google", "bing", "startpage"],
    "privacy":    ["duckduckgo", "startpage", "qwant"],
    "general":    ["bing", "duckduckgo", "google"],
}

AUTHORITY_TIER = {
    "github.com":90, "stackoverflow.com":88, "docs.python.org":92,
    "developer.mozilla.org":90, "arxiv.org":88, "wikipedia.org":82,
    "nature.com":90, "pubmed.ncbi.nlm.nih.gov":92,
    "openai.com":85, "anthropic.com":85, "huggingface.co":83,
    "techcrunch.com":72, "theverge.com":72, "arstechnica.com":75,
    "bbc.com":80, "reuters.com":82, "apnews.com":82,
    "medium.com":55, "dev.to":58, "reddit.com":50, "news.ycombinator.com":65,
}

INVALID_URL_PATTERNS = [
    "login","signin","signup","register","subscribe","paywall","premium",
    "checkout","cart","404","error","not-found","page-not-found",
    "captcha","verify","challenge",
]
INVALID_CONTENT_PATTERNS = [
    "access denied","403 forbidden","404 not found","page not found",
    "subscribe to read","sign in to continue","enable javascript",
    "please enable cookies","this content is for subscribers",
]


def _project_root():
    marker = Path.home()/".openclaw"/"workspace"/"skills"/"local-web-search"/".project_root"
    return marker.read_text().strip() if marker.exists() else "<your-project-directory>"

def _is_invalid_url(url):
    u = url.lower()
    return any(p in u for p in INVALID_URL_PATTERNS)

def _is_invalid_content(snippet):
    if not snippet: return False
    s = snippet.lower()
    return any(p in s for p in INVALID_CONTENT_PATTERNS)

def _domain_authority(url):
    try:
        host = urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
        if host in AUTHORITY_TIER: return AUTHORITY_TIER[host]
        for d,sc in AUTHORITY_TIER.items():
            if host.endswith("."+d): return sc
        return 40
    except: return 40

def _freshness_score(pub):
    if not pub: return 0.3
    try:
        import datetime
        for fmt in ("%Y-%m-%dT%H:%M:%SZ","%Y-%m-%d","%Y/%m/%d"):
            try:
                dt = datetime.datetime.strptime(pub[:len(fmt)],fmt)
                d = (datetime.datetime.utcnow()-dt).days
                if d<=1: return 1.0
                if d<=7: return 0.9
                if d<=30: return 0.75
                if d<=90: return 0.6
                if d<=365: return 0.45
                return 0.25
            except ValueError: continue
    except: pass
    return 0.3

def _score(item):
    return round(
        _domain_authority(item.get("url",""))*0.35
        +_freshness_score(item.get("publishedDate",""))*100*0.25
        +item.get("_engine_count",1)*8*0.25
        +(1 if item.get("content","").strip() else 0)*15*0.15, 2)

def _expand_query(query, intent):
    q = [query]
    if intent=="news":         q+=[f"{query} latest 2025 2026",f"{query} breaking news"]
    elif intent=="research":   q+=[f"{query} paper study",f"{query} github implementation"]
    elif intent=="comparison": q+=[f"{query} pros cons difference",f"{query} which is better"]
    elif intent=="tutorial":   q+=[f"{query} how to guide example"]
    elif intent=="factual":    q+=[f"{query} official documentation"]
    seen,r=[],[]
    for x in q:
        if x not in seen: seen.append(x); r.append(x)
    return r

def _fetch_single(base_url, query, engine, limit, freshness):
    params={"q":query,"format":"json","language":"en-US","pageno":"1","engines":engine}
    if freshness: params["time_range"]=freshness
    url=f"{base_url}/search?{urllib.parse.urlencode(params)}"
    req=urllib.request.Request(url,headers={"User-Agent":"OpenClawFreeSearch/2.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            data=json.loads(r.read().decode())
            results=data.get("results",[])
            for x in results: x["_engines_seen"]={engine}
            return results
    except: return []

def _parallel_search(base_url, queries, engines, limit, freshness):
    tasks=[(base_url,q,e,limit,freshness) for q in queries for e in engines]
    raw=[]
    with ThreadPoolExecutor(max_workers=min(len(tasks),8)) as pool:
        for f in as_completed({pool.submit(_fetch_single,*t):t for t in tasks}):
            try: raw.extend(f.result())
            except: pass
    url_map={}
    for item in raw:
        url=item.get("url","").strip()
        if not url: continue
        if url in url_map:
            url_map[url]["_engines_seen"].update(item.get("_engines_seen",set()))
            if len(item.get("content",""))>len(url_map[url].get("content","")): url_map[url]["content"]=item["content"]
            if item.get("publishedDate") and not url_map[url].get("publishedDate"): url_map[url]["publishedDate"]=item["publishedDate"]
        else:
            url_map[url]=dict(item); url_map[url].setdefault("_engines_seen",set())
    merged=[]
    for url,item in url_map.items():
        es=item.pop("_engines_seen",set())
        item["_engine_count"]=len(es); item["_seen_in_engines"]=sorted(es)
        merged.append(item)
    valid=[i for i in merged if not _is_invalid_url(i.get("url","")) and not _is_invalid_content(i.get("content",""))]
    for i in valid: i["_score"]=_score(i)
    valid.sort(key=lambda x:x["_score"],reverse=True)
    return valid[:limit]

def main():
    p=argparse.ArgumentParser(description="OpenClaw Free Web Search v2.0 - multi-engine, zero API key.")
    p.add_argument("--query",required=True)
    p.add_argument("--limit",type=int,default=5)
    p.add_argument("--intent",choices=["factual","news","research","tutorial","comparison","privacy","general"],default="general")
    p.add_argument("--engines",default=None,help="Comma-separated: bing,duckduckgo,google,startpage,qwant")
    p.add_argument("--freshness",choices=["hour","day","week","month","year"],default=None)
    p.add_argument("--no-expand",action="store_true")
    p.add_argument("--json",action="store_true")
    args=p.parse_args()

    if args.engines:
        engines=[e.strip() for e in args.engines.split(",") if e.strip() in ALL_ENGINES]
        if not engines:
            print(f"ERROR: No valid engines. Available: {', '.join(ALL_ENGINES)}",file=sys.stderr); return 1
    else:
        engines=INTENT_ENGINE_MAP.get(args.intent,INTENT_ENGINE_MAP["general"])

    queries=[args.query] if args.no_expand else _expand_query(args.query,args.intent)
    results=[]; used_url=DEFAULT_LOCAL_URL
    for base_url in [DEFAULT_LOCAL_URL,PUBLIC_FALLBACK_URL]:
        if not base_url: continue
        results=_parallel_search(base_url,queries,engines,args.limit,args.freshness)
        if results: used_url=base_url; break

    if not results:
        root=_project_root()
        print("ERROR: All search sources returned no results.",file=sys.stderr)
        print(f'Start local SearXNG: cd "{root}" && ./start_local_search.sh',file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results,indent=2,default=str)); return 0

    is_fallback=used_url!=DEFAULT_LOCAL_URL
    print(f"Query     : {args.query}")
    print(f"Intent    : {args.intent}")
    print(f"Engines   : {', '.join(engines)}")
    if len(queries)>1: print(f"Expanded  : {len(queries)} sub-queries (Agent Reach)")
    if args.freshness: print(f"Freshness : {args.freshness}")
    print(f"Source    : {'public fallback ('+used_url+')' if is_fallback else 'local SearXNG'}")
    print(f"Results   : {len(results)}")
    print()

    for idx,item in enumerate(results,1):
        title  =(item.get("title") or "").strip() or "(no title)"
        url    =(item.get("url") or "").strip() or "(no url)"
        snippet=" ".join((item.get("content") or "").split())
        pub    =(item.get("publishedDate") or "").strip()
        engs   =", ".join(item.get("_seen_in_engines",[]))
        score  =item.get("_score",0)
        cross  =item.get("_engine_count",1)>1
        print(f"{idx}. {title}")
        print(f"   URL      : {url}")
        if pub:  print(f"   Published: {pub}")
        if engs:
            print(f"   Engines  : {engs}",end="")
            if cross: print("  [cross-validated]",end="")
            print()
        print(f"   Score    : {score:.1f}/100")
        if snippet: print(f"   Snippet  : {snippet[:300]}{'...' if len(snippet)>300 else ''}")
        print()

    cross_count=sum(1 for r in results if r.get("_engine_count",1)>1)
    print("-"*60)
    print(f"AGENT NOTE: {cross_count}/{len(results)} results cross-validated across engines.")
    print("  -> Prefer higher Score + [cross-validated] results.")
    print("  -> Use web_fetch or browse_page.py to read full page before answering.")
    print("  -> Do NOT state facts from snippets alone - always verify via page content.")
    print("-"*60)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
