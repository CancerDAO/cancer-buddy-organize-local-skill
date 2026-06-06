# PaddleOCR Integration — cancer-buddy-organize-local

> Layer 1 (本地原子取字 + PII 脱敏) 调用 mtb-core 现成脚本。本文档规范 subprocess 调用 + venv 选择 + 失败回退。

## 依赖检查

### venv

期望 `~/.venvs/mtb-ocr/`（已装 paddleocr 3.4 + paddlepaddle 3.3 + paddlex 3.4）。

补装 workflow deps（已在 SPEC 锁定，组件复用 mtb-core）：
```bash
~/.venvs/mtb-ocr/bin/pip install -q "openai>=1.55.0" "python-dotenv==1.0.1" \
    "loguru==0.7.2" "PyMuPDF>=1.23.0" "Jinja2==3.1.4" "pydantic==2.9.2" \
    "requests==2.32.3" "PyYAML>=6.0" "lxml>=4.9.0" "typing-extensions==4.12.2"
```

### 自检命令

Layer 1 启动前 subagent 必跑：

```bash
PADDLE_PYTHON="$HOME/.venvs/mtb-ocr/bin/python"
"$PADDLE_PYTHON" -c "import paddleocr; print('paddleocr', paddleocr.__version__)" 2>/dev/null
```

返回 `paddleocr 3.x.y` 视为可用。任何错误（venv 不存在 / paddleocr import 失败）→ **降级**，见末尾 "Fallback" 节。

### Layer 1 脚本路径（vendored 在 skill 内）

Layer 1 调的脚本就在 skill 自己的 `scripts/` 目录下（来源记录见 `scripts/README.md`）：

```
$SKILL_DIR/scripts/redact_ocr.py        # 图片 OCR + PII 双层脱敏
$SKILL_DIR/scripts/extract_pdf.py        # PDF 文本
$SKILL_DIR/scripts/extract_docx.py       # DOCX 文本
$SKILL_DIR/scripts/extract_excel.py      # XLSX 文本
$SKILL_DIR/scripts/unpack_archive.py     # 解压 .zip/.rar/.7z/.tar.gz
```

`$SKILL_DIR` = `~/.claude/skills/cancer-buddy-organize-local`（subagent 通过 `dirname $0` 风格自定位）。

Skill 自洽，**不**依赖 mtb-core 仓库路径。脚本是从 mtb-core vendored 来的，跟踪同步流程见 `scripts/README.md`。

## 调用 contract

### 图片 → OCR sidecar (redact_ocr.py)

**输入**：单张图片绝对路径
**输出**：JSON 到 stdout

```bash
"$PADDLE_PYTHON" \
    "$SKILL_DIR/scripts/redact_ocr.py" \
    "$INPUT_IMAGE" \
    --output "$REDACTED_IMAGE" \
    --confidence 0.5 \
    --no-ner   # 默认 --no-ner; 跳过 PaddleNLP NER，但 regex PII 检测（身份证/手机号/带标签姓名）仍然运行 (paddlenlp 可选)
```

**stdout JSON**:
```json
{
  "success": true,
  "output": "/tmp/cb-v2/0001_redacted.jpg",
  "ocr_text_safe": "...",          // PII 已遮挡的文本 (Layer 2 拿这个)
  "pii_detected": 5,
  "regions": [                       // 每个 PII 区域的 bbox (审计)
    {"type": "patient_name", "bbox": [x, y, w, h], "value_hash": "..."}
  ]
}
```

错误时:
```json
{"success": false, "error": "...", "regions": []}
```

**重要**：`ocr_text_safe` 已是字符串，可直接喂 Layer 2。**禁止**让 Layer 2 重新 OCR 同一张图（除非 `--no-ner` 时漏检率 > 30%，详见 fallback 章节）。

### PDF → 文本 (extract_pdf.py)

```bash
"$PADDLE_PYTHON" \
    "$SKILL_DIR/scripts/extract_pdf.py" \
    "$INPUT_PDF"
```

stdout JSON:
```json
{"success": true, "text": "...", "page_count": N, "pages": [{"page": 1, "text": "..."}]}
```

PDF 是图片型扫描件 → extract_pdf 内部走 PyMuPDF 渲染每页 → 调 redact_ocr.py 处理。Layer 1 透明，无需关心。

### DOCX / XLSX

```bash
"$PADDLE_PYTHON" "$SKILL_DIR/scripts/extract_docx.py" "$F"
"$PADDLE_PYTHON" "$SKILL_DIR/scripts/extract_excel.py" "$F"
```

stdout JSON: `{"success": true, "text": "...", "tables": [...]}`

### 解压

```bash
"$PADDLE_PYTHON" "$SKILL_DIR/scripts/unpack_archive.py" "$INPUT_ARCHIVE"
```

stdout JSON: `{"success": true, "tmp_dir": "...", "files": [{"path": "...", "name": "..."}]}`

**注意**：unpack_archive.py 检测到非 ASCII 文件名时**会自动 flatten** 为 `0001.jpg / 0002.jpg / ...`，并写 `_mapping.json`。Layer 1 必须保留 mapping，Layer 2 分类时把目标文件名映射回原中文 + 日期。

## 性能 + 进度

- **首次启动**：PaddleOCR 模型懒加载 ~30s（首张图）
- **稳态**：3-8s/张（CPU），16GB RAM 占用约 20GB（含模型）
- **并发**：`ThreadPoolExecutor(max_workers=5)`（mtb-core 默认）。subagent 不要自己再开并发，在 SKILL.md workflow 里串行触发即可。
- **进度日志**：mtb-core 把 progress 写到 `tasks[task_id]["progress"]["label"]`。subagent 可以 tail mtb-core 自己的 logs 文件来 surface 进度。

## 环境变量

调 redact_ocr.py 前 export：

```bash
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True   # 跳过模型源连通性自检, 加速
export FLAGS_use_mkldnn=0                            # macOS Apple Silicon 关掉 MKL-DNN
```

Layer 1 应在每次 subprocess 调用前都 prepend 这两个 env，**不要**依赖 shell rc。

## Fallback — PaddleOCR 不可用时

按下列顺序判断：

1. **venv 不存在** (`$HOME/.venvs/mtb-ocr/bin/python` 不存在)
   → 提示用户先 `python -m venv ~/.venvs/mtb-ocr && ~/.venvs/mtb-ocr/bin/pip install paddleocr paddlepaddle`，或：
   → 直接走 v1 兼容路径（Claude vision 自己 OCR），写 `readiness.warnings += ["paddleocr_unavailable: venv 缺失"]`

2. **paddleocr import 失败** (`paddleocr 3.x` 检查失败)
   → 同上 fallback

3. **Layer 1 单文件 OCR 失败**（subprocess 返回 success: false 或超时）
   → 该文件**跳过 Layer 1，进 Layer 2 直接 vision**
   → 写 `readiness.warnings += ["paddle_ocr_failed: <basename>"]`
   → sidecar 头标记 `OCR_ENGINE: claude_vision_fallback`

4. **批量失败率 > 30%**（>30% 的图片 Layer 1 失败）
   → 整批 abort Layer 1，全部走 Claude vision
   → readiness.warnings 加 `paddleocr_bulk_failure_rate: 0.<X>, switched to vision-only`

## 英文文档处理

PaddleOCR 默认中文模型对纯英文报告（如 NCCN 英文版 / 美国医院出院 summary）准确度 < 中文。处理规则：

1. 文件名匹配 `[A-Za-z]{30,}` 或 OCR 头部 50 字非中文比例 > 70% → 标 `language: en`
2. `language=en` 文件直接走 Claude vision（v1 兼容路径），不调 PaddleOCR
3. 写 `readiness.warnings += ["english_doc_paddle_skip: <basename>"]`

## 调用示例（subagent 实际执行）

Layer 1 处理 1 张图的完整伪代码：

```python
import subprocess, json, os
PADDLE_PYTHON = os.environ.get("HOME") + "/.venvs/mtb-ocr/bin/python"
SKILL_DIR = os.environ.get("HOME") + "/.claude/skills/cancer-buddy-organize-local"

env = os.environ.copy()
env["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
env["FLAGS_use_mkldnn"] = "0"

result = subprocess.run(
    [PADDLE_PYTHON, f"{SKILL_DIR}/scripts/redact_ocr.py",
     input_image, "--output", redacted_path, "--no-ner"],
    capture_output=True, text=True, timeout=120, env=env
)

if result.returncode != 0:
    # fallback to vision
    pass
else:
    data = json.loads(result.stdout)
    if not data["success"]:
        # fallback
        pass
    else:
        ocr_text = data["ocr_text_safe"]
        pii_count = data["pii_detected"]
        # → 喂给 Layer 2 + 写 sidecar
```

subagent 通过 Bash 工具直接运行这种 Python，**不要**让 Claude 自己解析 OCR 输出 — 用 mtb-core 现成的 JSON 协议。

## 已知限制

- PaddleOCR 对**手写**字识别极差（< 60% 准确率）— 强制走 Claude vision
- PaddleOCR 对**化验单中复杂表格**（多列对齐，含↑↓箭头）有 5-10% 错位率 — Layer 2 必须做字符校正补救
- PaddleNLP NER 对**罕见姓名**漏检率较高 — Layer 2 必须做二次脱敏复查（OCR sidecar 模板里的 `## PII 二次脱敏追加` 区块就是这个用途）
