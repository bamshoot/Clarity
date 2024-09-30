from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class EODCandle(BaseModel):
    timestamp: Optional[int] = None
    gmtoffset: Optional[int] = None
    dt: Optional[datetime] = Field(None, alias="datetime")
    d: Optional[date] = Field(None, alias="date")
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    adjusted_close: Optional[float] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
            date: lambda v: v.strftime("%Y-%m-%d"),
        }

    def __init__(self, **data):
        super().__init__(**data)
        if self.dt is None and self.d is not None:
            self.dt = datetime.combine(self.d, datetime.min.time())
