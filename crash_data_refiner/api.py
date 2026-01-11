"""FastAPI wrapper for CrashDataRefiner."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from crash_data_refiner.agent_hub import fetch_knowledge, publish_knowledge, register_agent
from crash_data_refiner.geo import load_kmz_polygon
from crash_data_refiner.refiner import CrashDataRefiner
from crash_data_refiner.spreadsheets import read_spreadsheet

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="CrashDataRefiner API", version="0.1.0")
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


@app.on_event("startup")
def on_startup() -> None:
    register_agent()


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
    return fetch_knowledge(source=source, topic=topic, tag=tag, limit=limit)


@app.post("/refine")
async def refine(
    data_file: UploadFile = File(...),
    boundary_file: UploadFile | None = File(None),
    lat_column: str | None = Form(None),
    lon_column: str | None = Form(None),
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
            refined_rows, report, boundary_report, invalid_rows = refiner.refine_rows_with_boundary(
                data.rows,
                boundary=boundary,
                latitude_column=lat_column,
                longitude_column=lon_column,
            )
        else:
            refined_rows, report = refiner.refine_rows(data.rows)
            boundary_report = None
            invalid_rows = []

        sample_rows = refined_rows[: max(0, sample_limit)]
        payload = {
            "status": "success",
            "summary": {
                "total_rows": report.total_rows,
                "kept_rows": report.kept_rows,
                "dropped_missing_required": report.dropped_missing_required,
                "dropped_duplicates": report.dropped_duplicates,
                "coerced_dates": report.coerced_dates,
                "coerced_numbers": report.coerced_numbers,
                "coerced_booleans": report.coerced_booleans,
            },
            "boundary": boundary_report.__dict__ if boundary_report else None,
            "invalid_rows": len(invalid_rows),
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
