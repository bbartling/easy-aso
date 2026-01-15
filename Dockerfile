FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for bacpypes3/uvicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /app/
COPY easy_aso /app/easy_aso

RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir ".[platform]"

# Default command is a no-op; each compose service overrides it
CMD ["python", "-c", "print('easy-aso container built')"]
