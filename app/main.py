from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
import httpx
import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base service URLs (env-configurable)

def _normalize_service_base(val: str | None, name: str) -> str:
    # name: one of 'login','offers','transactions','monero'
    defaults = {
        "login": "http://login:8001",
        "offers": "http://offers:8002",
        "transactions": "http://transactions:8003",
        "monero": "http://monero:8004",
    }
    default = defaults.get(name, "")
    if not val:
        return default.rstrip("/")
    v = val.strip().rstrip("/")
    if "://" in v:
        return v
    host = v
    port = {
        "login": 8001,
        "offers": 8002,
        "transactions": 8003,
        "monero": 8004,
    }.get(name, None)
    if port:
        return f"http://{host}:{port}"
    return v

LOGIN_BASE = _normalize_service_base(os.getenv("LOGIN_SERVICE_URL"), "login")
OFFERS_BASE = _normalize_service_base(os.getenv("OFFERS_SERVICE_URL"), "offers")
TRANSACTIONS_BASE = _normalize_service_base(os.getenv("TRANSACTIONS_SERVICE_URL"), "transactions")
# Optional services; provide safe defaults to avoid NameError at import time
MONERO_BASE = _normalize_service_base(os.getenv("MONERO_SERVICE_URL"), "monero")
BALANCE_BASE = os.getenv("BALANCE_SERVICE_URL", TRANSACTIONS_BASE).rstrip("/")

HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"
}

app = FastAPI(title="Pupero API Manager")


@app.get("/")
def root():
    return {
        "service": "api-manager",
        "routes": [
            "/auth/* -> Login service",
            "/offers and /offers/* -> Offers service",
            "/transactions/* -> Transactions service",
            "/monero/* -> Monero Wallet Manager",
            "/healthz"
        ]
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


def _filter_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


async def _forward(request: Request, url: str) -> Response:
    # Copy incoming headers and body
    in_headers = _filter_headers(dict(request.headers))
    # Forward cookies via headers if present (FastAPI already includes Cookie header)
    content = await request.body()
    method = request.method
    params = request.query_params

    timeout = httpx.Timeout(30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.request(method, url, content=content, headers=in_headers, params=params)
    except httpx.RequestError as e:
        # Upstream unavailable; return a 502 with context (avoid leaking internal details beyond basics)
        return JSONResponse(status_code=502, content={
            "detail": "Upstream service unavailable",
            "upstream_url": url,
            "error": str(e.__class__.__name__),
            "message": str(e)
        })

    # Build response
    out_headers = _filter_headers(dict(upstream.headers))
    # Ensure content-type preserved if present
    return Response(content=upstream.content, status_code=upstream.status_code, headers=out_headers)


# -----------------
# Auth -> Login service (strip /auth prefix)
# -----------------
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Auth"])  # type: ignore
async def proxy_auth(request: Request, path: str):
    target = f"{LOGIN_BASE}/{path}" if path else LOGIN_BASE + "/"
    return await _forward(request, target)

@app.api_route("/auth", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Auth"])  # type: ignore
async def proxy_auth_root(request: Request):
    target = LOGIN_BASE + "/"
    return await _forward(request, target)


# -----------------
# Offers -> Offers service (preserve /offers path)
# -----------------
@app.api_route("/offers", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Offers"])  # type: ignore
async def proxy_offers_root(request: Request):
    target = f"{OFFERS_BASE}/offers"
    return await _forward(request, target)

@app.api_route("/offers/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Offers"])  # type: ignore
async def proxy_offers(request: Request, path: str):
    target = f"{OFFERS_BASE}/offers/{path}" if path else f"{OFFERS_BASE}/offers"
    return await _forward(request, target)


# -----------------
# Transactions -> Transactions service (strip /transactions prefix)
# -----------------
@app.api_route("/transactions/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Transactions"])  # type: ignore
async def proxy_transactions(request: Request, path: str):
    target = f"{TRANSACTIONS_BASE}/{path}" if path else TRANSACTIONS_BASE + "/"
    return await _forward(request, target)

@app.api_route("/transactions", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Transactions"])  # type: ignore
async def proxy_transactions_root(request: Request):
    target = TRANSACTIONS_BASE + "/"
    return await _forward(request, target)

# -----------------
# Monero Wallet Manager -> /monero/*
# -----------------
@app.api_route("/monero", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Monero"])  # type: ignore
async def proxy_monero_root(request: Request):
    target = MONERO_BASE + "/"
    return await _forward(request, target)


@app.api_route("/monero/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], tags=["Monero"])  # type: ignore
async def proxy_monero(request: Request, path: str):
    target = f"{MONERO_BASE}/{path}" if path else MONERO_BASE + "/"
    return await _forward(request, target)


# -------------
# OpenAPI proxy endpoints for each service
# -------------
@app.get("/auth/openapi.json", tags=["Docs"])
async def login_openapi_proxy():
    url = f"{LOGIN_BASE}/openapi.json"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/offers/openapi.json", tags=["Docs"])
async def offers_openapi_proxy():
    url = f"{OFFERS_BASE}/openapi.json"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/transactions/openapi.json", tags=["Docs"])
async def transactions_openapi_proxy():
    url = f"{TRANSACTIONS_BASE}/openapi.json"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/monero/openapi.json", tags=["Docs"])
async def monero_openapi_proxy():
    url = f"{MONERO_BASE}/openapi.json"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/balance/openapi.json", tags=["Docs"])
async def balance_openapi_proxy():
    url = f"{BALANCE_BASE}/openapi.json"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        return JSONResponse(status_code=r.status_code, content=r.json())


# -------------
# Combined OpenAPI aggregation and docs
# -------------
@app.get("/combined-openapi.json", tags=["Docs"])
async def combined_openapi():
    timeout = httpx.Timeout(20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        specs = {}
        for key, base in {
            "auth": LOGIN_BASE,
            "offers": OFFERS_BASE,
            "transactions": TRANSACTIONS_BASE,
            "monero": MONERO_BASE,
            "balance": BALANCE_BASE,
        }.items():
            try:
                resp = await client.get(f"{base}/openapi.json")
                resp.raise_for_status()
                specs[key] = resp.json()
            except Exception:
                specs[key] = None

    combined = {
        "openapi": "3.0.2",
        "info": {"title": "Pupero API Manager (Combined)", "version": "1.0.0"},
        "paths": {},
        "tags": [],
        "components": {}
    }

    def merge_tags(src_tags):
        if not isinstance(src_tags, list):
            return
        existing = {t.get("name") for t in combined.get("tags", []) if isinstance(t, dict)}
        for t in src_tags:
            name = (t or {}).get("name")
            if name and name not in existing:
                combined["tags"].append(t)
                existing.add(name)

    def merge_components(src_comp):
        if not isinstance(src_comp, dict):
            return
        comp = combined.setdefault("components", {})
        for section, items in src_comp.items():
            if not isinstance(items, dict):
                continue
            dest = comp.setdefault(section, {})
            for k, v in items.items():
                if k not in dest:
                    dest[k] = v

    # Helper to prefix paths
    def add_paths(spec, prefix_mode):
        if not spec or not isinstance(spec, dict):
            return
        paths = spec.get("paths", {})
        for p, item in paths.items():
            new_p = p
            if prefix_mode == "auth":
                if not p.startswith("/auth"):
                    new_p = "/auth" + p
            elif prefix_mode == "offers":
                # Ensure paths are under /offers
                if not p.startswith("/offers"):
                    new_p = "/offers" + (p if p.startswith("/") else f"/{p}")
            elif prefix_mode == "transactions":
                if not p.startswith("/transactions"):
                    new_p = "/transactions" + p
            combined["paths"][new_p] = item
        merge_tags(spec.get("tags"))
        merge_components(spec.get("components"))

    add_paths(specs.get("auth"), "auth")
    add_paths(specs.get("offers"), "offers")
    add_paths(specs.get("transactions"), "transactions")

    return JSONResponse(content=combined)


@app.get("/combined-docs", response_class=HTMLResponse, tags=["Docs"])
async def combined_docs_page():
    # Self-contained docs page without any external assets. It simply fetches and displays
    # the combined OpenAPI JSON in a <pre> block. You can copy the JSON into a local Swagger UI if desired.
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset=\"utf-8\"/>
      <title>Pupero API - Combined Docs (JSON)</title>
      <style>
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif; margin: 16px; }
        .controls { margin-bottom: 12px; }
        pre { white-space: pre-wrap; word-wrap: break-word; background: #f6f8fa; padding: 12px; border: 1px solid #e1e4e8; border-radius: 6px; max-height: 70vh; overflow: auto; }
        .hint { color: #555; font-size: 0.95em; }
      </style>
    </head>
    <body>
      <h1>Pupero API - Combined OpenAPI</h1>
      <div class=\"controls\">
        <button id=\"reload\">Reload</button>
        <span class=\"hint\">This page shows the raw OpenAPI JSON from <code>/combined-openapi.json</code>.</span>
      </div>
      <pre id=\"spec\">Loading...</pre>
      <script>
        async function loadSpec() {
          const el = document.getElementById('spec');
          try {
            const res = await fetch('/combined-openapi.json');
            const json = await res.json();
            el.textContent = JSON.stringify(json, null, 2);
          } catch (e) {
            el.textContent = 'Failed to load combined OpenAPI: ' + e;
          }
        }
        document.getElementById('reload').addEventListener('click', loadSpec);
        loadSpec();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
