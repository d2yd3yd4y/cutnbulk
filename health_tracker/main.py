from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.exceptions import AuthRedirect
from app.routers import auth, calendar, day, goal, meals, media, summary


settings = get_settings()

app = FastAPI(title="cutnbulk")

if settings.allowed_hosts and settings.allowed_hosts != ("*",):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(settings.allowed_hosts) + ["testserver"],
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(_request: Request, exc: AuthRedirect):
    return RedirectResponse(url=exc.url, status_code=303)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "cutnbulk"}


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    detail = getattr(exc, "detail", "禁止访问")
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/login", status_code=303)
    return JSONResponse({"detail": detail}, status_code=403)


app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(day.router)
app.include_router(goal.router)
app.include_router(summary.router)
app.include_router(meals.router)
app.include_router(media.router)
