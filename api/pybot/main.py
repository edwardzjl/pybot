"""Main entrypoint for the app."""
from contextlib import asynccontextmanager
from typing import Annotated

from aredis_om import Migrator, NotFoundError
from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from pybot.dependencies import EmailHeader, UserIdHeader, UsernameHeader
from pybot.routers.chat import router as chat_router
from pybot.routers.conversations import router as conversation_router
from pybot.routers.files import router as files_router
from pybot.routers.messages import router as message_router
from pybot.schemas import UserProfile


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Migrator().run()
    yield


app = FastAPI(lifespan=lifespan, openapi_url="/api/openapi.json", docs_url="/api/docs")

app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(files_router)
app.include_router(message_router)


@app.get("/api/healthz")
def healthz():
    return "OK"


@app.get("/api/userinfo")
def userinfo(
    userid: Annotated[str | None, UserIdHeader()] = None,
    username: Annotated[str | None, UsernameHeader()] = None,
    email: Annotated[str | None, EmailHeader()] = None,
) -> UserProfile:
    return UserProfile(
        userid=userid,
        username=username,
        email=email,
    )


@app.exception_handler(NotFoundError)
async def notfound_exception_handler(request: Request, exc: NotFoundError):
    logger.error(f"NotFoundError: {exc}")
    # TODO: add some details here
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"detail": str(exc)}),
    )


app.mount(
    "/", StaticFiles(directory="static", html=True, check_dir=False), name="static"
)
