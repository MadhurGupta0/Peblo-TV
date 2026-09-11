from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppValidationError(Exception):
    """Business-rule or resource-lookup failure (as opposed to a schema/type error,
    which Pydantic already catches). Carries the same {field, code, message} shape
    as artwork validation so the API has exactly one error envelope everywhere,
    regardless of which layer raised it or what HTTP status it maps to."""

    def __init__(self, errors: list[dict], status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY) -> None:
        self.errors = errors
        self.status_code = status_code
        super().__init__(str(errors))

    @classmethod
    def single(cls, field: str, code: str, message: str, status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY) -> "AppValidationError":
        return cls([{"field": field, "code": code, "message": message}], status_code=status_code)


def _envelope(errors: list[dict]) -> dict:
    return {"errors": errors}


async def app_validation_error_handler(request: Request, exc: AppValidationError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_envelope(exc.errors))


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(p) for p in e["loc"] if p != "body"),
            "code": e["type"],
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(_envelope(errors)))


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    # Never leak the raw DB error string (constraint names, table internals) to a client.
    message = "This change conflicts with existing data (e.g. a duplicate language/episode combination)."
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=_envelope([{"field": "_", "code": "conflict", "message": message}]))
