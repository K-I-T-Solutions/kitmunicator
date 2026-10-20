import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import engine, Base
from services.asterisk_ari import ari_consumer
from telephony.router import router as telephony_router
from presence.router import router as presence_router
from contacts.router import router as contacts_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    ari_task = asyncio.create_task(ari_consumer())

    yield

    ari_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await ari_task

    await engine.dispose()


app = FastAPI(
    title="KITmunicator API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telephony_router, prefix="/telephony", tags=["Telefonie"])
app.include_router(presence_router, prefix="/presence", tags=["Presence"])
app.include_router(contacts_router, prefix="/contacts", tags=["Kontakte"])


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
