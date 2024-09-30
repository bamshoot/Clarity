from fastapi import HTTPException


def response_handler(data, detail="Error getting data"):
    if data is None:
        raise HTTPException(status_code=404, detail=detail)
    else:
        return data
