<div align="center">

# cancer-buddy-organize-local.skill

> *Local-OCR, NER-PII variant of [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill)'s病历整理 module.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![CancerDAO](https://img.shields.io/badge/CancerDAO-Open%20Source-orange)](https://github.com/CancerDAO)

</div>

---

## 这是什么

**`cancer-buddy-organize-local` 是 [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) 中 `cancer-buddy-organize` 子技能的隐私优先变体。** 同样的输出契约（`profile.json` schema_v1 / `timeline.md` / `readiness.json`），同样下游 cancer-buddy / vmtb 子技能开箱即用——区别在 OCR 层：

| | 默认 `cancer-buddy-organize` | **本仓 `cancer-buddy-organize-local`** |
|---|---|---|
| OCR 引擎 | Claude vision（云端 multimodal） | **本地 PaddleOCR + PaddleNLP NER** |
| 字符精度 | 黑盒，无校正记录 | **显式校正记录**，每个修改可追溯到 OCR 原始输出 |
| PII 脱敏 | regex 提示 + 模型自觉 | **双层**：NER 图层遮挡 + 二次复查 |
| 部署要求 | Claude Code 即可 | + Python ≥ 3.10 venv + PaddleOCR + PaddlePaddle |
| 安装复杂度 | 一行 `npx skills add` | 一行 npx + 一次性 5-10 分钟 PaddleOCR 安装 |
| 处理时长（63 文件） | ~25 min | ~35 min（多了本地 OCR 一遍） |
| 适合谁 | 患者直接用 / 入门 | **隐私优先 / 临床合规要求 / 硬件支持本地推理的用户** |

`profile.json` schema、`timeline.md` 临床事件格式、`readiness.json` 8 域评分、review_flags 审计规则——**与默认版本完全互通**。你可以把已有 `cancer-buddy-organize` 整理过的 patient_dir 原地升级到本地变体，下游 vMTB / find-care / trial-match 不需要任何改动。

---

## 谁应该用这个

- 把患者真实病历拿到 CancerDAO 体系内做精准医疗会诊，但**不想让影像/姓名/身份证号过 Claude API 云端**
- 给医院 / 药企 / 保险机构演示时，需要**字符级 OCR 审计追溯**（监管侧可能要看每个数字是怎么读出来的）
- 跑批量队列（>50 份病历），希望避开 Claude vision 的 per-image cost
- 有一台能跑 PaddleOCR 推理的 Mac/Linux 工作站（Apple Silicon / 任意 x86）

**不需要的人请继续用 [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) 自带的默认 `cancer-buddy-organize`**——它已经覆盖 95% 的患者侧场景，无 Python 依赖，零安装。

---

## 安装

```bash
# 1. 装本地 OCR 变体（替代默认 organize）
npx skills add CancerDAO/cancer-buddy-organize-local-skill -g

# 2. 装 PaddleOCR Python venv（一次性，约 5-10 分钟）
# 详见 INSTALL.md
python3 -m venv ~/.venvs/mtb-ocr

# Linux x86_64 CPU 用户请使用固定依赖：
~/.venvs/mtb-ocr/bin/pip install -r requirements-linux-x86-cpu.txt

# 其他平台见 INSTALL.md

# 3. 验证
~/.venvs/mtb-ocr/bin/python -c "import paddleocr; print('OK')"
```

主仓 `cancer-buddy-skill` 是建议但**非强制**前置依赖——本仓 vendor 了所需的 `references/patient-profile-schema.md` / `safety-guardrails.md` / `roles.md` / `terminology.md` / `profile-card.md`，单独安装也能跑。但若要用下游 `cancer-buddy-vault` / `cancer-buddy-find-care` 等子技能，仍需 [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) 主仓。

完整安装、PaddleOCR 调试、fallback 行为见 [INSTALL.md](INSTALL.md)。

---

## 用法

装完后直接用自然语言：

```
帮我整理病历（用本地 OCR）
我有一堆报告，要做完隐私脱敏再走下游
```

Claude Code 会优先路由到 `cancer-buddy-organize-local`（如果同时装了默认 organize，按 description 中的"隐私优先 / 本地 OCR"关键词区分）。强制指定也可以：

```
/cancer-buddy-organize-local <path/to/folder>
```

输出与默认 organize 完全一样的 `patients/<patient_code>/` 目录结构，再加：

- `ocr/<basename>.md` — 每个图片一份，含 SOURCE / CONFIDENCE / 字符校正 / 双层 PII 脱敏 / 正文润色版
- `09_患者补充/` — 手写 timeline / 微信 / 语音转录 的 patient_curated 合并通道
- `10_原始文件/原始未遮挡/` — 字节级镜像，PII 未脱敏，**仅本地审计**，下游 skill 永远只读脱敏版

---

## 与主仓的同步关系

本仓和 [CancerDAO/cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) 的 `cancer-buddy-organize` 子技能是**孪生关系**——同一个输出契约（schema_v1）的两个实现。任何对以下结构的改动**必须在两个仓库同步进行**：

- `references/patient-profile-schema.md`（48 字段 schema_v1）
- `references/safety-guardrails.md`
- `references/roles.md`
- `references/profile-card.md`
- review_flags 类别（默认 5 类 / local 6 类，扩展时需对齐）
- 11 桶 + 子桶分类法
- `readiness.json` 8 域评分定义

如果你发了一个 PR 只改了一边，另一边的 maintainer 会 ping 你同步。两仓 schema 漂移会让下游 `cancer-buddy-vault` / `cancerdao-vmtb` / `cancer-buddy-trial-match` 直接坏掉。

---

## 项目结构

```
cancer-buddy-organize-local-skill/
├── README.md                                # 这个文件
├── INSTALL.md                                # PaddleOCR venv 安装 + 自检
├── LICENSE                                   # MIT
├── references/                               # 与主仓双向同步的契约文档
│   ├── patient-profile-schema.md             # 48 字段 schema_v1
│   ├── safety-guardrails.md
│   ├── roles.md
│   ├── terminology.md
│   └── profile-card.md
└── skills/
    └── cancer-buddy-organize-local/
        ├── SKILL.md                          # skill 入口（Claude Code 会读这个）
        ├── SPEC.md                           # 完整设计 + 决策 + 验收
        ├── references/                       # 本 skill 私有引用
        │   ├── document-taxonomy.md          # 11 桶分类法
        │   ├── subbucket-mapping.md          # 子桶 + 09_患者补充 检测
        │   ├── ocr-sidecar-template.md       # Layer 1+2 sidecar schema
        │   ├── review-flags-categories.md    # 6 类审计规则
        │   ├── paddleocr-integration.md      # subprocess + venv + fallback
        │   └── organizer-prompt.md           # subagent 主提示词
        └── scripts/                          # 本地 Python 工具（subprocess 调用）
            ├── redact_ocr.py                 # PaddleOCR + NER PII 双层脱敏
            ├── extract_pdf.py
            ├── extract_docx.py
            ├── extract_excel.py
            └── unpack_archive.py
```

---

## 数据存储

与主仓默认相同：

```
$HOME/CancerDAO/patients/
```

可用环境变量覆盖：`$CANCER_BUDDY_PATIENTS_DIR` 优先于 `$VMTB_PATIENT_DATA_ROOT` 优先于默认路径。

---

## 注意事项

- 本工具不提供医疗诊断或治疗建议——所有医疗决策需与专业医生确认
- PaddleOCR 中文模型对手写 / 印章 / 严重模糊文档准确率有限，本 skill 在这些场景会自动 fallback 到 Claude vision（你可以通过 paddleocr-integration.md 调整阈值）
- 字符校正只能改 OCR 错字，**禁止**做语义改写
- 10_原始文件/原始未遮挡/ 是字节级镜像——永远本地 only，不要 commit 到任何 git 仓

---

## 贡献

欢迎贡献。特别欢迎：

- PaddleOCR 模型升级（PP-OCRv4 / v5 兼容测试）
- NER 模型微调（医疗实体类别扩展）
- 子桶分类规则补充（罕见癌种文档类型）
- 跨平台 install.sh（Linux / Windows WSL）

请提 [Issue](https://github.com/CancerDAO/cancer-buddy-organize-local-skill/issues) 或 PR。涉及上面"同步关系"清单中的契约文档，请**同时**给 [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) 开一个对应 PR。

---

## 关于我们

[CancerDAO](https://github.com/CancerDAO)：用 AI + 开源，构建面向患者与家属的支持系统。

---

## 致谢

- **PaddleOCR + PaddleNLP**：百度开源生态。
- **cancer-buddy-skill 主仓**：本仓 vendored 了主仓的 schema / safety / roles / terminology / profile-card 契约文档，license MIT。

---

<div align="center">

MIT License © [CancerDAO](https://github.com/CancerDAO)

</div>
