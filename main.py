from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dbo.whisper_manager import (
    store_whisper,
    retrieve_whisper,
    destroy_whisper,
    generate_whisper,
)
from functions import date_functions
import re


app = FastAPI(redoc_url=None, docs_url=None, openapi_url=None)

templates = Jinja2Templates(directory="/app/templates")
app.mount("/app/static", StaticFiles(directory="/app/static"), name="static")
sha256_pattern = re.compile(r"^[a-f0-9]{64}$")


@app.middleware("http")
async def custom_http_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers[
        "Strict-Transport-Security"
    ] = "max-age=31536000; includeSubDomains"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    csp_header = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.counter.dev;"
        "connect-src 'self' https://cdn.jsdelivr.net https://cdn.counter.dev https://t.counter.dev/; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' https://whisper.page data:; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "frame-src 'none'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "block-all-mixed-content; "
        "upgrade-insecure-requests;"
    )
    response.headers["Content-Security-Policy"] = csp_header
    response.headers["X-Content-Type-Options"] = "nosniff"
    if response.status_code in (404, 405):
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )
    elif response.status_code == 500:
        return templates.TemplateResponse(
            "500.html", {"request": request}, status_code=500
        )

    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def page_index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)


@app.get("/security", response_class=HTMLResponse, include_in_schema=False)
async def page_security(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("security.html", context)


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def page_privacy(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("privacy.html", context)


@app.get("/contact", response_class=HTMLResponse, include_in_schema=False)
async def page_contact(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("contact.html", context)


@app.post("/generate_link")
async def page_generate_link(
    request: Request,
    whisper_content: str = Form(""),
    ttl: str = Form(...),
    destruct_upon_viewing: bool = Form(False),
):
    (
        link,
        hash1,
        hash2,
        encrypted_whisper_content,
        ttl_epoch,
        nonce,
    ) = await generate_whisper(whisper_content, ttl)

    await store_whisper(
        hash1,
        hash2,
        encrypted_whisper_content,
        ttl_epoch,
        destruct_upon_viewing,
        nonce,
    )

    ttl_date = await date_functions.ttl_date_parser(ttl_epoch)
    ttl_minutes = date_functions.minutes_until_expiry(ttl_date)

    context = {
        "request": request,
        "link": link,
        "ttl_date": ttl_date,
        "ttl_minutes": ttl_minutes,
    }

    return templates.TemplateResponse("link.html", context)


@app.get("/{hash1}/{hash2}")
async def page_retrieve_whisper(request: Request, hash1: str, hash2: str):
    if not (re.match(sha256_pattern, hash1) and re.match(sha256_pattern, hash2)):
        raise HTTPException(
            status_code=404,
            detail="This whisper has already been destroyed or does not exist",
        )

    try:
        (
            encrypted_whisper_content,
            ttl,
            destruct_upon_viewing,
            nonce,
        ) = await retrieve_whisper(hash1, hash2)

    except:
        raise HTTPException(
            status_code=404,
            detail="This whisper has already been destroyed or does not exist",
        )

    ttl_date = await date_functions.ttl_date_parser(ttl)
    ttl_minutes = date_functions.minutes_until_expiry(ttl_date)

    incoming_link = "/" + hash1 + "/" + hash2 + "/"

    context = {
        "request": request,
        "whisper_content": encrypted_whisper_content,
        "nonce": nonce,
        "destruct_upon_viewing": destruct_upon_viewing,
        "ttl_date": ttl_date,
        "ttl_minutes": ttl_minutes,
        "incoming_link": incoming_link,
    }

    if destruct_upon_viewing == "1":
        await destroy_whisper(hash1, hash2)

    return templates.TemplateResponse("whisper.html", context)


@app.post("/{hash1}/{hash2}/destroy_whisper")
async def page_destroy_whisper(request: Request, hash1: str, hash2: str):
    context = {
        "request": request,
    }
    await destroy_whisper(hash1, hash2)
    return templates.TemplateResponse("destroyed.html", context)
