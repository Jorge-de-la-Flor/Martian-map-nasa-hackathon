from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from geospatial.raster import resolve_data_path
from models.mission import DataCatalogResponse, LayerInfo


def load_data_catalog(data_dir: Path) -> DataCatalogResponse:
    catalog_path = data_dir / "catalog.json"

    if not catalog_path.is_file():
        return DataCatalogResponse(
            region_name=None,
            region_status="not_selected",
            layers=[],
            available_categories=[],
        )

    try:
        raw: dict[str, Any] = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read data catalog: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("The data catalog root must be a JSON object.")

    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported data catalog schema version.")

    region = raw.get("region")

    if region is not None and not isinstance(region, dict):
        raise ValueError("The region field must be an object or null.")

    region_name = region.get("name") if region else None

    if region_name is not None and (not isinstance(region_name, str) or not region_name.strip()):
        raise ValueError("Region name must be a non-empty string.")

    raw_layers = raw.get("layers", [])

    if not isinstance(raw_layers, list):
        raise ValueError("The catalog layers field must be a list.")

    layers: list[LayerInfo] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw_layers):
        if not isinstance(item, dict):
            raise ValueError(f"Layer at position {index} must be an object.")

        local_path = item.get("local_path")
        available = False

        if local_path is not None:
            if not isinstance(local_path, str) or not local_path.strip():
                raise ValueError(f"Layer at position {index} has an invalid local_path.")

            try:
                resolve_data_path(data_dir, local_path)
                available = True
            except FileNotFoundError:
                # The product is registered but has not been downloaded.
                available = False

        layer_data = {
            **item,
            "available": available,
            "asset_url": (f"/api/mission/layers/{item.get('id')}/file" if available else None),
        }

        try:
            layer = LayerInfo.model_validate(layer_data)
        except ValidationError as exc:
            raise ValueError(f"Invalid layer definition at position {index}: {exc}") from exc

        if layer.id in seen_ids:
            raise ValueError(f"Duplicate layer identifier: {layer.id}")

        seen_ids.add(layer.id)
        layers.append(layer)

    available_categories = sorted({layer.category for layer in layers if layer.available})

    return DataCatalogResponse(
        region_name=region_name,
        region_status="selected" if region_name else "not_selected",
        layers=layers,
        available_categories=available_categories,
    )
