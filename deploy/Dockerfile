# Reproducible x86_64 Linux server image for cancer-buddy-organize-local Layer-1 OCR.
# Addresses issue #1: unpinned `pip install paddlepaddle paddleocr paddlenlp`
# pulled paddle 3.3.1 (oneDNN/PIR crash on x86 CPU) + an incompatible aistudio-sdk.
#
# Build (on the x86_64 server, NOT emulated):
#   docker build -f deploy/Dockerfile -t cbol-ocr .
# Smoke test (must print ocr_predict.ok == true):
#   docker run --rm cbol-ocr
# Verified: ocr_predict.ok == true on Tencent Cloud OpenCloudOS 9 / Xeon (no avx512).
# The oneDNN crash is prevented by PaddleOCR(enable_mkldnn=False) in redact_ocr.py;
# libgl1 below fixes the libGL.so.1 ImportError on bare servers.
#
# The image installs ONLY the OCR stack. PaddleNLP name-NER is optional and
# kept OUT by default — it conflicts with paddleocr 3.x on numpy and the default
# pipeline runs with the regex floor (no paddlenlp needed). See INSTALL.md §NER.

FROM python:3.11-slim

# NOTE: the oneDNN crash is fixed in code via PaddleOCR(enable_mkldnn=False),
# NOT by env flags. FLAGS_use_mkldnn=0 kept as a harmless default.
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    FLAGS_use_mkldnn=0 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/cbol
COPY deploy/requirements.x86_64-linux.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY skills/cancer-buddy-organize-local/scripts/ ./scripts/

# Default command runs the smoke test (Issue #1 gate).
CMD ["python", "scripts/smoke_test.py"]
