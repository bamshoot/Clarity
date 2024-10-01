from fastapi import APIRouter, Request
from services.eod_data import EODData
from utils.handlers import response_handler

router = APIRouter(tags=["EOD API"])


@router.get("/candles/{ticker}/{exchange}/{interval}/{fmt}")
async def get_candles(
    request: Request, ticker: str, exchange: str, interval: str, fmt: str
):
    config = request.app.state.config
    async with EODData(
        base_url=config.EOD_URL,
        api_key=config.EOD_API_KEY,
    ) as eod_api:
        candles = await eod_api.get_candles(ticker, exchange, interval, fmt)
        return response_handler(candles, "Error getting candles")
