"""Protected bulk access for NSO/RBI analysts (doc 11 ``/api/v1/data/quotes``)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response, StreamingResponse

from apps.api.dependencies.db import ApiKey, AppSettings, DbSession
from apps.api.services.export_service import ExportService

router = APIRouter(prefix="/api/v1/data", tags=["data"], dependencies=[ApiKey])


@router.get("/quotes")
def quotes(
    session: DbSession,
    settings: AppSettings,
    date_: date = Query(..., alias="date"),
    format_: Literal["csv", "json"] = Query("csv", alias="format"),
    canonical_only: bool = True,
) -> StreamingResponse:
    """The canonical dataset underlying the index for one observation date, with lineage ids."""
    service = ExportService(session, settings)
    if format_ == "json":
        return StreamingResponse(
            service.quotes_json(date_, canonical_only), media_type="application/json"
        )
    return StreamingResponse(
        service.quotes_csv(date_, canonical_only),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="apix-quotes-{date_.isoformat()}.csv"'
        },
    )


@router.get("/evidence/{response_id}")
def evidence(response_id: uuid.UUID, session: DbSession, settings: AppSettings) -> Response:
    """The exact bytes a source returned (verified against its SHA-256)."""
    body, content_type = ExportService(session, settings).evidence(response_id)
    return Response(content=body, media_type=content_type or "application/octet-stream")
