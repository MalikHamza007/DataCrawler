from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from app.core.request_context import get_request_id


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class InvalidOwnerError(DomainError):
    status_code = 422


class InvalidStatusTransitionError(DomainError):
    status_code = 409


class PermissionDeniedError(DomainError):
    status_code = 403


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "error_code": exc.__class__.__name__.upper(), "request_id": get_request_id()})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())
        return JSONResponse(status_code=422, content={"detail": errors, "error_code": "VALIDATION_ERROR", "request_id": get_request_id(), "errors": errors})
