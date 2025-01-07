from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, timezone


class EODCandle(BaseModel):
    timestamp: Optional[int] = None
    gmtoffset: Optional[int] = None
    datetime_: Optional[datetime] = Field(None, alias="datetime")
    date_: Optional[date] = Field(None, alias="date")
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
        if self.datetime_ is None and self.date_ is not None:
            self.datetime_ = datetime.combine(self.date_, datetime.min.time(),
                                              tzinfo=timezone.utc)
        elif self.datetime_ is None and self.timestamp is not None:
            self.datetime_ = datetime.fromtimestamp(self.timestamp,
                                                    tz=timezone.utc)

        if self.date_ is None and self.datetime_ is not None:
            self.date_ = self.datetime_.date()

        # Calculate timestamp from datetime_ if it's not provided
        if self.timestamp is None and self.datetime_ is not None:
            self.timestamp = int(self.datetime_.timestamp())
