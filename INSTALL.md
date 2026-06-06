# INSTALL — cancer-buddy-organize-local

完整安装路径、PaddleOCR venv 调试、fallback 行为。

---

## 1. 装 skill

```bash
# 全局安装（推荐）
npx skills add CancerDAO/cancer-buddy-organize-local-skill -g

# 或仅当前项目
npx skills add CancerDAO/cancer-buddy-organize-local-skill
```

装完后 skill 落在 `~/.claude/skills/cancer-buddy-organize-local/`（全局）或 `<repo>/.claude/skills/cancer-buddy-organize-local/`（项目）。

如果你同时装了 [`cancer-buddy-skill`](https://github.com/CancerDAO/cancer-buddy-skill)，两个 organize 子技能会并存，Claude Code 按 SKILL.md description 中的"隐私优先 / 本地 PaddleOCR"关键词路由。明确指定也可以：

```
/cancer-buddy-organize-local <path>
/cancer-buddy-organize       <path>   # 默认云端 OCR 版本
```

---

## 2. 装 PaddleOCR Python venv

Layer 1（本地原子取字 + PII 脱敏）通过 subprocess 调用本地 Python 脚本。需要一个独立 venv，避免污染系统 Python。

### 2.1 创建 venv

```bash
python3 -m venv ~/.venvs/mtb-ocr
source ~/.venvs/mtb-ocr/bin/activate
pip install --upgrade pip
```

> **Python 版本要求**：≥ 3.10。Apple Silicon 用 `python3` 系统自带或 brew 装的都行。

### 2.2 装 PaddleOCR

```bash
pip install paddlepaddle paddleocr paddlenlp
```

各平台备注：

- **Mac (Apple Silicon)**：默认 `paddlepaddle` 是 CPU 版，开箱可用。Metal GPU 加速目前 PaddlePaddle 不支持，CPU 推理一张报告约 2-4 秒。
- **Mac (Intel)**：同上。
- **Linux (x86, CPU)**：同上。
- **Linux (x86, NVIDIA GPU)**：`pip install paddlepaddle-gpu`（详见 PaddlePaddle 官网选型）。
- **Windows / WSL**：建议 WSL2 + Ubuntu，按 Linux 流程。

### 2.3 装运行时依赖

Layer 1 + Layer 2 协同还需要：

```bash
pip install \
  "openai>=1.55.0" \
  "python-dotenv==1.0.1" \
  "loguru==0.7.2" \
  "PyMuPDF>=1.23.0" \
  "Jinja2==3.1.4" \
  "pydantic==2.9.2" \
  "requests==2.32.3" \
  "PyYAML>=6.0" \
  "lxml>=4.9.0" \
  "typing-extensions==4.12.2"
```

#### 2.3.1 文档提取依赖 (PDF / DOCX / XLSX)

Layer 1 从 PDF / DOCX / XLSX 直接抽取文本时需要 `pdfplumber` / `python-docx` / `openpyxl`。这些固定在仓库根的 `requirements-extract.txt`：

```bash
# 装入同一个 PaddleOCR venv
~/.venvs/mtb-ocr/bin/pip install -r requirements-extract.txt
```

缺这几个包时 `extract_pdf.py` / `extract_docx.py` / `extract_excel.py` 会返回 `{"success": false, "error": "... Run: pip install -r requirements-extract.txt (see INSTALL.md)"}`，按提示装上即可。

#### 2.3.2 压缩包解压的系统工具

`unpack_archive.py` 支持 `.zip` / `.tar` / `.tar.gz` / `.tgz` / `.tar.bz2` / `.tbz2` / `.tar.xz` / `.txz` / `.rar` / `.7z`：

- **`.zip` 和所有 `.tar*` 变体**：用 Python 标准库（`zipfile` / `tarfile`），无需额外安装。
- **`.7z`**：需要系统 `7z`（p7zip）。macOS：`brew install p7zip`；Debian/Ubuntu：`apt install p7zip-full`。
- **`.rar`**：需要系统 `unrar` 或 `unar`（脚本通过 subprocess 调用）。macOS：`brew install unar`；Debian/Ubuntu：`apt install unar`（或 `unrar`）。

### 2.4 自检

```bash
~/.venvs/mtb-ocr/bin/python -c "import paddleocr; print('paddleocr', paddleocr.__version__)"
~/.venvs/mtb-ocr/bin/python -c "import paddlenlp; print('paddlenlp', paddlenlp.__version__)"
```

期望输出类似：

```
paddleocr 3.x.y
paddlenlp 2.x.y
```

首次运行会自动下载 PP-OCRv4 模型（约 300MB，缓存到 `~/.paddleocr/`），后续不再下载。

---

## 3. 跑一遍试试

```bash
# 准备一个测试文件夹
mkdir -p /tmp/test-organize
cp <a few sample medical PDFs/images> /tmp/test-organize/

# 在 Claude Code 里说：
帮我用本地 OCR 整理这个文件夹: /tmp/test-organize
```

期望输出：

```
$HOME/CancerDAO/patients/PT-<10-hex>/
├── INDEX.md
├── profile.json
├── timeline.md
├── readiness.json
├── case_text.md
├── 01_当前状态/ ~ 11_诊断证明/
├── 09_患者补充/   # 仅当输入含手写 timeline / 微信导出
├── 10_原始文件/原始未遮挡/
└── ocr/<basename>.md  # 每个图片一份 sidecar
```

第一次跑会用 5-10 分钟（首次模型下载 + OCR）。后续跑同样规模约 3-5 分钟。

---

## 4. Fallback 行为

PaddleOCR 不可用时，skill **不会**直接报错——它会自动降级到 Claude vision（即默认 `cancer-buddy-organize` 的行为），但会在 readiness.json 里加一个 review_flag：

```json
{
  "category": "ocr_fallback",
  "severity": "yellow",
  "message": "PaddleOCR venv 不可用，Layer 1 降级到 Claude vision；PII 仅做 regex 提示，未做 NER 图层遮挡"
}
```

触发降级的条件：

- `~/.venvs/mtb-ocr/bin/python` 不存在
- `import paddleocr` 失败（版本不兼容 / 依赖缺失）
- 单张图片 OCR 超时 > 60 秒（罕见，通常是图片损坏）

如果你不想要 fallback、宁可让 skill 报错退出，在调用时加 `--strict-paddle`（详见 [paddleocr-integration.md](skills/cancer-buddy-organize-local/references/paddleocr-integration.md)）。

---

## 5. 卸载

```bash
npx skills remove cancer-buddy-organize-local -g
rm -rf ~/.venvs/mtb-ocr
rm -rf ~/.paddleocr
```

---

## 6. 常见问题

**Q: 我装了 `cancer-buddy-skill` 主仓，还需要装这个吗？**

A: 不强制。两个 organize 子技能输出契约一致，主仓默认版本对患者侧场景够用。本仓适合**隐私优先 / 合规审计 / 批量队列**场景。

**Q: 没有 GPU 也能跑吗？**

A: 能。PaddleOCR CPU 推理一张报告 2-4 秒，63 文件批次约 10-15 分钟。

**Q: PaddleOCR 对手写文档识别效果如何？**

A: 印刷体 95%+，手写体 60-75%。本 skill 对手写自动 fallback Claude vision，详见 [paddleocr-integration.md](skills/cancer-buddy-organize-local/references/paddleocr-integration.md)。

**Q: PII 脱敏漏检了怎么办？**

A: Layer 1 NER + regex 双层后还有 Layer 2 vision 复查，三层 miss 是小概率。`10_原始文件/原始未遮挡/` 永远本地 only，不要 commit / 上传任何外部系统。

**Q: 这个仓和主仓 schema 不同步了怎么办？**

A: 提 Issue 到任一仓，我们会同时改两个。两仓 schema 漂移会让下游 `cancerdao-vmtb` / `cancer-buddy-vault` 等子技能挂掉。
