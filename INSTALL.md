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

> ⚠️ **issue #1 的 x86 崩溃,真因经真机验证是两点,跟版本无关**:
> 1. **缺系统库 `libGL.so.1`**(cv2/paddlex 依赖,裸服务器常缺)→ `ImportError: libGL.so.1`。
> 2. **oneDNN 崩溃** `ConvertPirAttribute2RuntimeAttribute ... onednn_instruction.cc` —— 已在真 x86(paddle 3.3.1 + paddleocr 3.6.0,无 avx512)复现,且**任何 env flag 都挡不住**(`FLAGS_use_mkldnn=0` / `FLAGS_enable_pir_in_executor=0` / `FLAGS_enable_pir_api=0` 实测均无效)。**唯一有效的是在 PaddleOCR 构造器传 `enable_mkldnn=False`** —— `redact_ocr.py` 已内置,无需你做任何事。
>
> 所以 reporter 自己那套版本(paddle 3.3.1 + paddleocr 3.6.0)装上系统库后就能跑,**不用降级**。

**Mac (Apple Silicon / Intel)**：开箱即用，CPU 推理一张报告约 2-4 秒。

```bash
pip install paddlepaddle paddleocr        # paddlenlp 可选，见 §2.5
```

**Linux (x86_64, CPU)**（issue #1）：

```bash
# 1) 先装系统库（cv2/paddlex 需要 libGL.so.1，裸服务器必缺）
#    Debian/Ubuntu:
sudo apt-get install -y libgl1 libglib2.0-0 libgomp1
#    RHEL/OpenCloudOS/CentOS:
sudo dnf install -y mesa-libGL glib2 libgomp

# 2) 装锁定版本（reporter 同款版本，已在真 x86 验证；不装 paddlenlp，避免 numpy 冲突）
pip install -r deploy/requirements.x86_64-linux.txt

# 3) 自检——ocr_predict.ok 必须为 true（已在腾讯云 OpenCloudOS9 x86 实测通过）
python skills/cancer-buddy-organize-local/scripts/smoke_test.py
```

oneDNN 关闭由 `redact_ocr.py` 在构造 PaddleOCR 时传 `enable_mkldnn=False` 完成,**你不用手动 export 任何 flag**。

**Linux (x86_64) — 推荐用 Docker 复现部署**（服务器场景，系统库已在镜像里）：

```bash
docker build -f deploy/Dockerfile -t cbol-ocr .
docker run --rm cbol-ocr        # 跑 smoke_test，ocr_predict.ok == true 才算通
```

- **Linux (x86, NVIDIA GPU)**：`pip install paddlepaddle-gpu`（详见 PaddlePaddle 官网选型）。
- **Windows / WSL**：建议 WSL2 + Ubuntu，按 x86_64 Linux 流程。

### 2.5 PaddleNLP name-NER（可选，默认不需要）

**默认 pipeline 不依赖 paddlenlp**。Layer 1 的本地脱敏底线是 **regex**（身份证 / 手机 / 带标签字段），由 `redact_ocr.py` 的 `--no-ner` 路径提供，零额外依赖；自由游走人名由 Layer 2 LLM 二次脱敏复查兜底。

PaddleNLP UIE NER 只是「在 regex 之上额外抓无标签人名」的增强。它与 paddleocr 3.x 在 numpy 上冲突（NER 要 numpy<2，OCR 要 numpy≥2），所以**不要装进同一个 OCR venv**。要用就单开 venv：

```bash
python3 -m venv ~/.venvs/mtb-ner && source ~/.venvs/mtb-ner/bin/activate
pip install "paddlenlp==2.8.1" "aistudio-sdk==0.2.6"   # 0.2.6 仍含 aistudio_sdk.hub.download
```

`redact_ocr.py` 在 NER 不可用时**不再静默降级**：输出 JSON 带 `ner_available: false` + `ner_error`，organizer 据此加一条 `ner_unavailable_name_redaction_degraded` review_flag。

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
# 必须通过：
~/.venvs/mtb-ocr/bin/python -c "import paddleocr; print('paddleocr', paddleocr.__version__)"
# 完整自检（推荐，等价于 Docker 的 CMD）：
~/.venvs/mtb-ocr/bin/python skills/cancer-buddy-organize-local/scripts/smoke_test.py
```

`smoke_test.py` 输出 JSON：`ocr_predict.ok == true` 是硬门（Layer 1 能跑）；`ner_load` 失败**不影响**默认 pipeline（见 §2.5）。

首次运行会自动下载模型（约 300MB，缓存到 `~/.paddleocr/`），后续不再下载。

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

## 4. Fallback 行为（隐私 fail-safe 默认）

PaddleOCR 读不了某文件时，**默认（`cloud_vision_fallback: deny`）绝不把原图上云**——这是本 skill「本地脱敏」前提的硬约束。默认行为：

- 该文件标 `ocr_gap_local_only`，留在 `10_原始文件/未分类/`
- readiness.json 加 review_flag（category `unverified_critical_field`, severity yellow）
- pipeline 继续跑（基于已成功的文件）

触发 fallback 的条件：

- `~/.venvs/mtb-ocr/bin/python` 不存在 / `import paddleocr` 失败 → `paddleocr_unavailable`
- 单张图片 OCR `success:false` 或超时 → `paddle_ocr_failed: <name>`
- 批量失败率 > 30% → `paddleocr_bulk_failure_rate`
- 英文**图片**（中文模型准确度差）→ `english_doc_paddle_skip`（英文 PDF/docx 走文本提取，不受影响）

**仅当**单人本地审阅、且你明确接受「原始病历会发给当前 runtime 的模型 provider（Claude Code→Anthropic / Codex→OpenAI）」时，才用 `--allow-cloud-vision` 显式开启 vision fallback。**服务器 / 隐私优先部署永不开。**

> ⚠️ 注意：在 **Codex/GPT 等非 Claude runtime** 上，"vision fallback" = 原始未脱敏病历图片直接发到 OpenAI，直接违背本 skill 核心前提。这就是默认 `deny` 的原因（issue #2）。

历史 flag `--strict-paddle`（仅覆盖"venv 不可用就报错退出"）仍兼容；新的 `cloud_vision_fallback: deny` 是更全面的默认（覆盖单文件失败 / 英文跳过 / 批量失败所有会触发 vision 的分支）。

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

A: 印刷体 95%+，手写体 60-75%。手写件 OCR 失败时，默认（`deny`）记 gap 进未分类、不上云；仅 `--allow-cloud-vision` 时才走多模态 vision。详见 [paddleocr-integration.md](skills/cancer-buddy-organize-local/references/paddleocr-integration.md)。

**Q: PII 脱敏漏检了怎么办？**

A: Layer 1 regex 兜底（身份证/手机/带标签字段，零依赖始终生效）+ 可选 NER（无标签人名）+ Layer 2 LLM 二次脱敏复查。`10_原始文件/原始未遮挡/` 永远本地 only，不要 commit / 上传任何外部系统。注意：Layer 2 二次脱敏只在 `--allow-cloud-vision` 或本地有 sidecar 文本时进行；`deny` 模式下读不出的文件直接记 gap，不会有"半脱敏"产物外流。

**Q: 这个仓和主仓 schema 不同步了怎么办？**

A: 提 Issue 到任一仓，我们会同时改两个。两仓 schema 漂移会让下游 `cancerdao-vmtb` / `cancer-buddy-vault` 等子技能挂掉。
