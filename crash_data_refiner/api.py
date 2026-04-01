"""Compatibility FastAPI wrapper for CrashDataRefiner.

This surface is kept intentionally narrower than the Flask web app. Core
refinement behavior should stay aligned with the shared service contract so it
cannot silently drift from the main application.
"""

from __future__ import annotations

import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from crash_data_refiner.agent_hub import fetch_knowledge, publish_knowledge, register_agent
from crash_data_refiner.coordinate_recovery import (
    load_coordinate_review_decisions,
    recover_missing_coordinates,
)
from crash_data_refiner.geo import load_kmz_polygon
from crash_data_refiner.refiner import CrashDataRefiner
from crash_data_refiner.run_contract import build_refine_response_summary
from crash_data_refiner.services import resolve_label_order
from crash_data_refiner.spreadsheets import read_spreadsheet

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_agent()
    yield


app = FastAPI(title="CrashDataRefiner API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/agent/info")
def agent_info() -> dict[str, Any]:
    return {
        "name": "CrashDataRefiner",
        "capabilities": ["crash-data", "kmz", "reports"],
    }


@app.post("/agent/register")
def agent_register() -> dict[str, str]:
    register_agent()
    return {"status": "registered"}


@app.post("/agent/knowledge/publish")
def agent_publish(payload: dict[str, Any]) -> dict[str, str]:
    publish_knowledge(payload)
    return {"status": "queued"}


@app.get("/agent/knowledge/query")
def agent_query(
    source: str | None = None,
    topic: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    try:
        return fetch_knowledge(source=source, topic=topic, tag=tag, limit=limit)
    except Exception as exc:  # pragma: no cover - optional integration boundary
        raise HTTPException(status_code=503, detail=f"Orchestrator knowledge hub unavailable: {exc}") from exc


@app.post("/refine")
async def refine(
    data_file: UploadFile = File(...),
    boundary_file: UploadFile | None = File(None),
    coordinate_review_file: UploadFile | None = File(None),
    lat_column: str | None = Form(None),
    lon_column: str | None = Form(None),
    label_order: str = Form("auto"),
    sample_limit: int = Form(10),
) -> dict[str, Any]:
    if not data_file.filename:
        raise HTTPException(status_code=400, detail="Crash data file is required.")

    suffix = Path(data_file.filename).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(status_code=400, detail="Crash data must be CSV or Excel.")

    with tempfile.TemporaryDirectory(prefix="crash_refiner_") as temp_dir:
        data_path = Path(temp_dir) / data_file.filename
        data_path.write_bytes(await data_file.read())

        data = read_spreadsheet(str(data_path))
        refiner = CrashDataRefiner()
        review_decisions = None
        recovery_report = None
        review_rows = []

        if coordinate_review_file and coordinate_review_file.filename:
            review_suffix = Path(coordinate_review_file.filename).suffix.lower()
            if review_suffix not in {".csv", ".xlsx", ".xlsm"}:
                raise HTTPException(
                    status_code=400,
                    detail="Coordinate review file must be CSV or Excel.",
                )
            review_path = Path(temp_dir) / coordinate_review_file.filename
            review_path.write_bytes(await coordinate_review_file.read())
            review_data = read_spreadsheet(str(review_path))
            review_decisions = load_coordinate_review_decisions(review_data.rows)

        if boundary_file:
            if not boundary_file.filename:
                raise HTTPException(status_code=400, detail="Boundary file name missing.")
            if Path(boundary_file.filename).suffix.lower() != ".kmz":
                raise HTTPException(status_code=400, detail="Boundary file must be KMZ.")
            if not lat_column or not lon_column:
                raise HTTPException(
                    status_code=400, detail="lat_column and lon_column are required with boundary."
                )

            boundary_path = Path(temp_dir) / boundary_file.filename
            boundary_path.write_bytes(await boundary_file.read())
            boundary = load_kmz_polygon(str(boundary_path))
            prepared_rows, review_rows, recovery_report = recover_missing_coordinates(
                data.rows,
                latitude_column=lat_column,
                longitude_column=lon_column,
                boundary=boundary,
                review_decisions=review_decisions,
            )
            refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
                prepared_rows,
                boundary=boundary,
                latitude_column=lat_column,
                longitude_column=lon_column,
            )
            resolved_label_order = resolve_label_order(
                refined_rows,
                lat_column=lat_column,
                lon_column=lon_column,
                label_order=label_order,
            )
        else:
            if review_decisions is not None:
                if not lat_column or not lon_column:
                    raise HTTPException(
                        status_code=400,
                        detail="lat_column and lon_column are required with coordinate_review_file.",
                    )
                prepared_rows, review_rows, recovery_report = recover_missing_coordinates(
                    data.rows,
                    latitude_column=lat_column,
                    longitude_column=lon_column,
                    review_decisions=review_decisions,
                )
            else:
                prepared_rows = data.rows
            refined_rows, report = refiner.refine_rows(prepared_rows)
            boundary_report = None
            invalid_rows = []
            resolved_label_order = label_order if label_order in {"west_to_east", "south_to_north"} else "west_to_east"

        sample_rows = refined_rows[: max(0, sample_limit)]
        payload = {
            "status": "success",
            "summary": build_refine_response_summary(
                report=report,
                boundary_report=boundary_report,
                invalid_rows=len(invalid_rows),
                coordinate_review_rows=len(review_rows),
                rejected_review_rows=0,
                recovery_report=recovery_report,
                requested_label_order=label_order,
                resolved_label_order=resolved_label_order,
            ),
            "boundary": boundary_report.__dict__ if boundary_report else None,
            "invalid_rows": len(invalid_rows),
            "coordinate_review_rows": len(review_rows),
            "recovery": recovery_report.__dict__ if recovery_report else None,
            "sample_rows": sample_rows,
        }
        return payload


def start_server() -> None:
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9005"))
    uvicorn.run("crash_data_refiner.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
