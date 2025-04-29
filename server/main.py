from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import main_router, eod_router
import uvicorn
from .config.config import Config
from .controllers.chrono import EODDataCollectionChrono
from contextlib import asynccontextmanager
from .services.eod_data import EODData
from .database.db import DB
from .services.manual_trading_identification import ManualTradingIdentification

config = Config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = DB(config.DB_PATH)

    db_connection = app.state.db.get_connection()
    if db_connection is None:
        raise RuntimeError("Failed to establish database connection")

    eod_data_service = EODData(
        config.EOD_URL,
        config.EOD_API_KEY,
        db_connection=db_connection
    )

    app.state.manual_trading = ManualTradingIdentification(
        config=config,
        eod_data_service=eod_data_service,
        db_connection=app.state.db
    )

    app.state.data_collection_chrono = EODDataCollectionChrono(
        eod_data_service,
        max_concurrent_requests=3,
        db=app.state.db,
        schedule_hour=0,
        schedule_minute=23,
        manual_trading=app.state.manual_trading
    )

    await app.state.data_collection_chrono.start()
    app.state.config = config

    try:
        yield
    finally:
        await app.state.data_collection_chrono.stop(timeout=10)
        app.state.db.close()

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
