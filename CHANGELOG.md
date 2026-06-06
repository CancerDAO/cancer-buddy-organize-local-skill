# Changelog — cancer-buddy-organize-local

## Unreleased — fix/x86-install-and-runtime-agnostic

Fixes [#1](https://github.com/CancerDAO/cancer-buddy-organize-local-skill/issues/1)
(x86_64 Linux install) and [#2](https://github.com/CancerDAO/cancer-buddy-organize-local-skill/issues/2)
(runtime-agnostic worker + privacy-safe fallback).

Root cause was diagnosed on a real x86_64 server (Tencent Cloud OpenCloudOS 9,
Xeon without avx512 — matches the reporter's environment). It was NOT a version
problem: the crash reproduces on the reporter's own versions and is two issues.

- **oneDNN crash FIX** (`ConvertPirAttribute2RuntimeAttribute ... onednn_instruction.cc`):
  the real fix is `PaddleOCR(enable_mkldnn=False)` in `redact_ocr.py`
  (`_build_ocr_instance`, both v3 and v2 paths). Verified on real x86 with the
  reporter's exact combo (paddlepaddle 3.3.1 + paddleocr 3.6.0): the crash
  reproduces with the default constructor and disappears with `enable_mkldnn=False`.
  **No env flag fixes it** — `FLAGS_use_mkldnn=0` / `FLAGS_enable_pir_in_executor=0`
  / `FLAGS_enable_pir_api=0` were all verified ineffective. No version downgrade
  needed. (`FLAGS_use_mkldnn=0` kept only as a harmless default.)
- **Missing system lib**: bare servers lack `libGL.so.1` (cv2/paddlex) → `ImportError`.
  Documented `apt-get install libgl1 libglib2.0-0 libgomp1` (Debian) /
  `dnf install mesa-libGL glib2 libgomp` (RHEL/OpenCloudOS); `deploy/Dockerfile`
  installs them.
- **Pinned, verified OCR stack**: `deploy/requirements.x86_64-linux.txt` pins
  the reporter's working versions (paddlepaddle 3.3.1 + paddleocr 3.6.0 + numpy<2)
  for reproducibility; `deploy/Dockerfile` for reproducible server deploy.
- **PaddleNLP made truly optional**: it conflicts with paddleocr on numpy and the
  default pipeline does not need it. Removed from the required install; documented
  a separate venv (`paddlenlp==2.8.1` + `aistudio-sdk==0.2.6`, the version that
  still exposes `aistudio_sdk.hub.download`) for free-floating-name NER.
- **`smoke_test.py`** added (ships in `scripts/`, is the Docker `CMD`): hard-gates
  on `ocr_predict.ok`. Verified `ocr_predict.ok == true` on real x86 with the fix.

### Issue #2 — runtime-agnostic + privacy fallback

- **Runtime-agnostic worker prompt**: `organizer-prompt.md` now opens with a
  Runtime-adaptation table mapping Read/Write/Bash/subagent/Monitor to neutral
  verbs. Verified on Claude Code and Codex/GPT-5.5. SKILL.md documents supported
  runtimes and how non-CC runtimes run the prompt directly.
- **Privacy fail-safe by default**: new `cloud_vision_fallback` parameter
  (default `deny`). On local OCR failure the default is now **record a gap,
  leave the file in `未分类/`, never upload** — instead of silently sending the
  raw record to the runtime's cloud vision (OpenAI on Codex, Anthropic on CC).
  Cloud vision is opt-in via `--allow-cloud-vision` with an explicit warning.
  Covers every vision-triggering branch (venv missing, single-file fail, bulk
  failure, English-image skip), superseding the narrower `--strict-paddle`.

### Redaction floor (found while fixing #1/#2)

- **`--no-ner` now applies the regex PII floor** (ID / phone / labeled fields)
  instead of keeping every line. Previously `--no-ner` — the parameter the
  default pipeline passes — skipped *all* Layer-1 classification, so local
  redaction was effectively off and rested entirely on the Layer-2 LLM. This
  matched neither the docs nor the skill's "local redaction" premise.
- **NER status surfaced**: `redact_ocr.py` output now includes
  `ner_requested` / `ner_available` / `ner_error`. The organizer raises a
  `ner_unavailable_name_redaction_degraded` review_flag instead of a silent
  privacy downgrade.

### Docs

- INSTALL.md: per-platform install, Docker path, NER §2.5, fail-safe fallback §4.
- README.md / paddleocr-integration.md: runtime note, accurate OCR-engine /
  fallback descriptions.
