FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
COPY vite.config.ts tsconfig.json tailwind.config.js postcss.config.js ./
RUN npm run build

FROM python:3.12-slim AS application
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOLAR_DATA_DIR=/app/data \
    SOLAR_DISABLE_API_DOCS=true
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir pip==26.2.2 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --system solar \
    && useradd --system --gid solar --home-dir /app solar
COPY app ./app
COPY --from=frontend-build /build/static ./static
RUN mkdir -p /app/data /app/backups && chown -R solar:solar /app
USER solar
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
