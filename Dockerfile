# AresPath · Martian Map — un solo servicio: API (FastAPI) + frontend (Vite/Cesium)

# ---------- 1) Compilar el frontend ----------
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# El token de Cesium Ion se pasa como variable de entorno del servicio (no está en Git)
ARG VITE_CESIUM_ION_TOKEN
ENV VITE_CESIUM_ION_TOKEN=$VITE_CESIUM_ION_TOKEN
RUN npm run build

# ---------- 2) Backend + datos del terreno ----------
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Librerías del sistema que necesita rasterio/GDAL (la imagen "slim" no las trae)
RUN apt-get update \
 && apt-get install -y --no-install-recommends libexpat1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY scripts ./scripts
COPY data ./data
# Descarga la ventana del DEM USGS de 1 m y genera el mapa de pendientes (scripts de Steven)
RUN .venv/bin/python scripts/prepare_boxwork_dem.py \
 && .venv/bin/python scripts/build_boxwork_layers.py
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV MARTIAN_MAP_FRONTEND_DIST=/app/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", ".venv/bin/uvicorn main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
