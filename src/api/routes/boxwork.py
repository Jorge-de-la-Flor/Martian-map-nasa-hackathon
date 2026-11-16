from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import get_settings

router = APIRouter(prefix="/mission/boxwork", tags=["boxwork"])
PREVIEW = Path(__file__).resolve().parents[1] / "boxwork-preview.html"


def boxwork_file(name: str, media_type: str) -> FileResponse:
    path = get_settings().data_dir / "boxwork" / name
    if not path.is_file():
        raise HTTPException(
            404, "Run scripts/build_boxwork_layers.py to generate the boxwork data."
        )
    return FileResponse(path, media_type=media_type)


@router.get("/analysis", response_class=FileResponse)
def boxwork_analysis() -> FileResponse:
    return boxwork_file("analysis.json", "application/json")


@router.get("/slope.png", response_class=FileResponse)
def boxwork_slope_image() -> FileResponse:
    return boxwork_file("slope.png", "image/png")


@router.get("/imagery", response_class=FileResponse)
def boxwork_imagery() -> FileResponse:
    return boxwork_file("imagery.json", "application/json")


@router.get("/{name}.png", response_class=FileResponse, include_in_schema=False)
def gale_imagery_image(name: Literal["gale-context", "gale", "mount-sharp"]) -> FileResponse:
    return boxwork_file(f"{name}.png", "image/png")


@router.get("/preview", response_class=FileResponse, include_in_schema=False)
def boxwork_preview() -> FileResponse:
    return FileResponse(PREVIEW, media_type="text/html")
