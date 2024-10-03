from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import main_router, eod_router
import uvicorn
from config.config import Config

# from contollers.chrono import DataCollectionChrono
from contextlib import asynccontextmanager
from services.eod_data import EODData
from database.db import DB
from resource import williams_fractal

config = Config()

eod_data_service = EODData(config.EOD_URL, config.EOD_API_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = DB()

    # app.state.data_collection_chrono = DataCollectionChrono(
    #     data_service=eod_data_service,
    #     interval=300,
    #     max_concurrent_requests=10,
    # )

    # await app.state.data_collection_chrono.start()
    app.state.config = config

    result = williams_fractal(
        db=app.state.db,
        table="USDJPY_d",
        period=3,
        data_point="close",
        column_name="date",
    )
    print(result)

    try:
        yield

    finally:
        app.state.db.close()
        # await app.state.data_collection_chrono.stop(timeout=10)


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
