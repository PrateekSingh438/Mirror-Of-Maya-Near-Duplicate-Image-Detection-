# Optional self-host image (CPU). For GPU, use an nvidia/cuda base and the
# CUDA torch wheels, then bake or fetch the artifact bundle.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.hf_cache \
    ARTIFACT_SOURCE=local \
    ARTIFACT_DIR=/app/artifacts

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# To ship a prebuilt corpus, COPY ./artifacts in (or set ARTIFACT_SOURCE=hf/url).

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
