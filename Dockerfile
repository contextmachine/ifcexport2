FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . .
# Install msi collision python module with app extras

RUN pip install --user --no-cache-dir --no-warn-script-location .


FROM python:3.12-slim


# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH


COPY --from=builder /root/.local /root/.local

WORKDIR /app
COPY --from=builder /build/ifcexport2 ifcexport2/

EXPOSE 8022

