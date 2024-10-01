from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import main_router, eod_router
import uvicorn
from config.config import Config
from contollers.chrono import Chrono
from contextlib import asynccontextmanager

config = Config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chrono = Chrono(interval=10)
    app.state.chrono.start()
    yield
    app.state.chrono.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router.router)
app.include_router(eod_router.router, prefix="/api/eod", tags=["EOD API"])

app.state.config = config


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
