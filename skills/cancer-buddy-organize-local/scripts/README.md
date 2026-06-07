# scripts/ — Layer 1 工具集 (vendored from mtb-core)

> 本目录下的 5 个脚本是 **vendored 副本**, 上游来自 `cancerdao/code/mtb/mtb-core/src/organizer/scripts/`. 让 v2 skill 自洽: 不依赖外部仓库路径.

## 文件

| 文件 | 用途 | Layer 1 调用阶段 |
|---|---|---|
| `redact_ocr.py` | 图片 OCR + PaddleNLP NER PII 双层脱敏 + bbox redact | Step 3.1 (jpg/png/tiff/webp) |
| `extract_pdf.py` | PDF 文本提取 (PyMuPDF, 内置 OCR fallback) | Step 3.2 (pdf) |
| `extract_docx.py` | DOCX 文本提取 (python-docx) | Step 3.3 (docx) |
| `extract_excel.py` | XLSX 文本 + 表格提取 (openpyxl) | Step 3.3 (xlsx) |
| `unpack_archive.py` | zip/rar/7z/tar.gz 解压 + 非 ASCII 文件名 flatten | Step 2.1 (archives) |

## 调用契约

每个脚本以 stdout JSON 返回, 见 `../references/paddleocr-integration.md` §调用 contract.

## 依赖

需要 venv (默认 `~/.venvs/mtb-ocr`) 已装:
- `paddleocr>=3.4`
- `paddlepaddle>=3.3`
- `paddlenlp` (可选, 不装时 redact_ocr.py 走 regex-only)
- `Pillow>=10`
- `PyMuPDF>=1.23`
- `python-docx>=1.0`
- `openpyxl>=3.1`
- `rarfile` (可选, 解 .rar)
- `py7zr` (可选, 解 .7z)

详见 `../references/paddleocr-integration.md` §依赖检查.

## 与上游同步

```bash
# 同步上游变更 (谨慎评估 breaking change)
SRC="$HOME/.../cancerdao/code/mtb/mtb-core/src/organizer/scripts"
DST="$HOME/.claude/skills/cancer-buddy-organize-local/scripts"
diff "$SRC/redact_ocr.py" "$DST/redact_ocr.py"
# 看变更后再决定是否 cp
```

## 当前 vendored 版本快照 (2026-06-07)

```
a979282c31d37ed20cdeb7a724cf63075a255135a2e657b4d65f28ab94ed1401  extract_docx.py
7e31a2a1d5f469c8f614809ddf2b5ae1c14b3cad273ff51fa7ce8fd64f6ec3ac  extract_excel.py
badf97cc42ff431c319405d96a7aa0b9bc8ee12780f4f670df21134545fab94e  extract_pdf.py
13c733908a61ec923f1027e414b3ab13e6e1cde1f7fb1bf903929fa7a558b268  redact_ocr.py
4197d19f070d8126b890d2c875455f4af998f0a8f4331b031fc008e44a2cb363  unpack_archive.py
```

> `redact_ocr.py` 含 skill-local 改动（`--batch` 批处理 + 逐张超时 + text_preview token 化脱敏），不在上游 mtb-core，按"修改原则"第 1 条不回推。

## 修改原则

- v2 skill 内部修改这些脚本 → **不**回推上游 mtb-core (mtb-core 是私有项目)
- 上游 mtb-core 修了 bug → 评估后用 cp 同步, 更新本文件 SHA256 + 时间戳
- 长期目标 (项目转向开源后): mtb-core 不再是 skill 的隐性依赖, 这些脚本就只属于 cancer-buddy-organize-local
