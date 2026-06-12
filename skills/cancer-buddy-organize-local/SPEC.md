# cancer-buddy-organize-local · SPEC

> Status: **APPROVED — implementing** · Author: Claude (with 鲍志炜) · Date: 2026-05-04 · Locked: 2026-05-04
> Variant of: `cancer-buddy-organize` — same output contract, swaps cloud OCR for local PaddleOCR + NER PII redaction
> Related: `cancerdao-vmtb`, `vmtb-skill`, `cancer-buddy-mtb-lite`

## 1. Goal

Turn raw patient files (folder / archive / single doc) into a canonical patient directory that:
- 字符级 OCR 经过审计（修正可追溯）
- PII 双层脱敏（图层遮挡 + 二次复查）
- profile.json / timeline.md / readiness.json **临床事件级**而非文件清单级
- 输出 schema 与 vmtb-skill / cancer-buddy-mtb-lite / cancer-buddy-trial-match 完全互通
- 支持患者补充材料（手写日记 / 微信 / 医生口述）作为 patient_curated 第二轮 merge

**不做**：临床判断、治疗建议、MTB 报告 — 这些由下游 skill 处理。

## 2. 为什么不沿用 v1 / mtb-core

| | v1 (Claude vision) | mtb-core (PaddleOCR + Gemini) | **v2 目标** |
|---|---|---|---|
| OCR 字符精度 | 黑盒 | ✅ 显式校正记录 | 沿用 mtb-core |
| PII 脱敏 | ⚠️ 仅 regex 提示 | ✅ NER 图层遮挡 | 沿用 mtb-core |
| profile.json 厚度 | ✅ 48 字段 + irAE 时序 | ⚠️ 11 字段 mostly null | 沿用 v1 |
| timeline.md | ✅ 临床事件流 | ⚠️ 文件清单 | 沿用 v1 |
| review_flags 五类审计 | ✅ | ❌ | 沿用 v1 |
| 子桶分类 | 平铺 11 桶（旧） | ✅ 子桶细分 | 沿用 mtb-core |
| 文档去重 | ⚠️ 部分 | ⚠️ 同一份 MRI 进 2 次 | **v2 新增** |
| 患者补充材料 merge | ❌ | ❌ | **v2 新增** |
| readiness schema | 8 域 schema_v1 ✅ | 7 模块独立 | 沿用 v1 |

## 3. 架构（3 层 pipeline + 1 个补丁通道）

```
Input (folder / .zip|.rar|.7z|.tar.gz / .pdf|.docx|.jpg|.png)
    │
    ├─► [Layer 1] 本地原子取字 (PaddleOCR + PaddleNLP NER)
    │       · subprocess 调 scripts/redact_ocr.py (vendored)
    │       · 图片 → ocr/<basename>.md (含字符校正 + PII 遮挡 + bbox)
    │       · PDF/DOCX/XLSX → 纯文本提取 (extract_pdf/docx/excel.py)
    │       · 输出双副本: 90_原始文件镜像/<原始子目录>/ (字节级镜像) + <临床域桶>/<子桶>/ (脱敏分类副本)
    │
    ├─► [Layer 2] 临床分类与归档 (Claude vision + 子桶映射)
    │       · 读 ocr/<basename>.md 的 OCR 文本 + 必要时回看图片
    │       · 决策: target_directory (含子桶) + doc_type + date + hospital + summary
    │       · 去重: 哈希同源文件只保留 1 份, 其余进 _duplicates/
    │       · 写入分类后的 <bucket>/<YYYY-MM-DD>_<brief_desc>.<ext>
    │
    ├─► [Layer 3] 临床综合 + 五类审计 (Claude text)
    │       · 读所有 ocr/*.md 合成 case_text.md
    │       · 抽取 profile.json (schema_v1, 48 字段)
    │       · 生成 timeline.md (临床事件流 — 治疗/检查/趋势节点)
    │       · 评 readiness.json (8 域评分 + blocking_gaps)
    │       · 跑 review_flags 五类审计 (format/cross-doc/clinical-logic/unverified-critical/value-trend)
    │       · 输出 review_flags.md (人类可读)
    │
    └─► [Layer 3.5] 患者补充材料 merge (可选, 第二轮入口)
            · 输入: manual_timeline.txt / 微信导出 / 医生口述音频转录
            · 标记 SOURCE: patient_curated, CONFIDENCE: low
            · 进 14_患者自管补充/, 同时 update profile.json + timeline.md (patient_curated 字段)
            · review_flags 增补 cross_doc_contradiction 检查 (与正式文档冲突点)
```

## 4. 文件布局（patient_dir）

```
<patient_dir>/
├── INDEX.md                  # 头：MTB readiness 摘要 + 关键指标 + 治疗线
├── profile.json              # schema_v1 (与 vmtb-skill 共享)
├── timeline.md               # 临床事件流 (非文件清单)
├── readiness.json            # 8 域 + blocking_gaps + review_flags
├── review_flags.md           # 待人工确认清单 (review_flags 非空时生成)
├── case_text.md              # 整合叙事
│
│                              # scheme_version 3 — 14 临床域 (+2 infra)；权威定义见 references/bucket-taxonomy.md §1
├── 01_身份与基础信息/
│   └── 身份证件/  人口学/  参保信息/
├── 02_既往史与家族史/
│   └── 既往病史/  手术史/  过敏史/  用药史/  家族史/  胚系遗传/
├── 03_病程与叙事文书/
│   └── 入院记录/  出院小结/  病程记录/  门诊病历/  主诉首程/
├── 04_诊断与分期/
│   └── 病理报告/  诊断证明/  分期评估/  其他/
├── 05_影像/
│   └── CT/  MRI/  PET-CT/  超声/  X光DR/  核医学/  内镜影像/  其他/
├── 06_分子与组学/
│   └── NGS报告/  免疫组化/  胚系检测/  WES-WGS/  转录组/  甲基化/  蛋白-代谢/  微生物组/  其他/
├── 07_检验/
│   └── 血常规/  生化肝肾功/  肿瘤标志物/  凝血/  尿便/  其他/
├── 08_治疗/
│   └── 化疗/  放疗/  免疫治疗/  靶向/  内分泌/  中医中药/  处方医嘱/  支持治疗/
├── 09_手术与操作/
│   └── 手术记录/  麻醉记录/  介入/  内镜操作/  植入物-器械卡/
├── 10_随访与监测/
│   └── 随访复查/  可穿戴导出/  PRO自报/  居家监测/
├── 11_会诊与转诊/
│   └── MDT/  会诊/  转诊/  第二意见/
├── 12_心理社会与支持/
│   └── 心理评估/  营养/  康复/  缓和/  社工/
├── 13_行政与财务/
│   └── 知情同意/  费用发票/  医保报销/  证明材料/
├── 14_患者自管补充/             # ★ Layer 3.5 入口
│   └── 患者补充/  日记/  自测/  conversation_notes/
│
├── 90_原始文件镜像/             # ★ HIDDEN — 字节级镜像 (保留 <原始子目录>/) + 去重副本，永不患者可见 / 永不锚定
│   ├── <原始子目录>/           # PII 未脱敏的全镜像 (审计用, 本地)；脱敏 job 在此就地替换图片
│   └── _duplicates/            # 哈希同源被去重的副本
├── 99_无关文件/                # ★ HIDDEN (quarantine) — 相关性隔离区
│   ├── high_confidence/
│   └── uncertain/
│
├── longitudinal_observations.json  # ★ scheme_version 3 — 纵向流观测值 store (timeseries / 趋势 structured)
└── ocr/                        # 每个图片/PDF 对应一个 sidecar
    └── <basename>.md
```

## 5. OCR sidecar schema（Layer 1 输出）

```markdown
# <basename>

> 原文件: `<original_name>` ｜ PII 遮挡: <N> 处 ｜ OCR 字符: <M>
> SOURCE: <source_type> ｜ CONFIDENCE: <high|medium|low>
> MODALITY: <text|image|structured|omics_raw|timeseries|binary_other>
> ORIGINAL: 90_原始文件镜像/<原始子目录>/<basename>

## 字符校正 (Layer 2 audit)
- "1F-FDG" → "18F-FDG" (line 5)
- "肾孟" → "肾盂" (line 12)
- "5.7mmOl/L" → "5.7 mmol/L" (line 8)

## PII 二次脱敏追加 (Layer 2 audit)
- 检查号 PT26010800014 → [REDACTED]
- 床号 023 → [REDACTED]

## 文档元数据 (Layer 2 写入)
- type: <doc_type>
- target_directory: <临床域桶/子桶>
- modality: <text|image|structured|omics_raw|timeseries|binary_other>
- date: <YYYY-MM-DD>
- hospital: <name>
- summary: <≤80字>

## 关键指标 (Layer 2 抽取)
- SUVmax_cervix: 11.4
- SCC: 15.00 ng/mL

## 文档正文（润色版）
<polished text>

## OCR 原文（PaddleOCR 一次脱敏后）
<details><summary>点击展开</summary>

```
<raw OCR text with bbox-redacted PII>
```
</details>
```

**SOURCE 类型**: `pathology_report | discharge_summary | admission_note | imaging_report | lab_report | prescription | molecular_panel | colposcopy | patient_note | patient_curated | wechat_chat | voice_transcript`

**CONFIDENCE 规则**: 同 v1（formal report → high; OCR with uncertainty → medium; handwriting / 语音转录 / patient_curated → low）

## 6. profile.json schema_v1（沿用 v1 + 微调）

字段保持与 vmtb-skill 共享 schema_v1。**v2 增加 2 字段**：
```json
{
  "patient_curated_sources": [
    {"path": "14_患者自管补充/患者补充/manual_timeline.txt", "encoding": "utf-16-le", "confidence": "low"}
  ],
  "duplicate_count": 3
}
```

完整 schema 见 [`../../references/patient-profile-schema.md`](../../references/patient-profile-schema.md)（vendored，与 cancer-buddy-skill 主仓 schema 双向同步）。

## 7. review_flags 五类审计（沿用 v1）

格式 / 跨文档矛盾 / 临床逻辑 / 未验证关键字段 / 数值趋势异常 — 完全沿用 v1。**v2 在跨文档矛盾检查中新增 manual vs formal 比对**：

| 新增检查 | 触发示例 |
|---|---|
| `patient_curated_vs_formal` | manual 写"1/7 出院诊断含鳞癌"，但 1/7 出院记录 OCR 写"病检未归"→ flag yellow |

## 8. 复用清单

| 来源 | 复用方式 | 用途 |
|---|---|---|
| `mtb-core/src/organizer/scripts/redact_ocr.py` | **vendor 到 `scripts/`** | Layer 1 PII 双层脱敏 |
| `mtb-core/src/organizer/scripts/extract_pdf.py` | **vendor 到 `scripts/`** | Layer 1 PDF 文本 |
| `mtb-core/src/organizer/scripts/extract_docx.py` | **vendor 到 `scripts/`** | Layer 1 DOCX 文本 |
| `mtb-core/src/organizer/scripts/extract_excel.py` | **vendor 到 `scripts/`** | Layer 1 XLSX 文本 |
| `mtb-core/src/organizer/scripts/unpack_archive.py` | **vendor 到 `scripts/`** | Layer 1 解压 |
| `mtb-core/src/organizer/assets/document-taxonomy.md` | 复制到 references/ | Layer 2 子桶映射依据 |
| `cancer-buddy-organize/references/organizer-prompt.md` | 改造扩展 | Layer 2/3 subagent 主提示词 |
| `cancer-buddy-organize/references/profile-card.md` | 直接复用 | 输出渲染 |
| `references/patient-profile-schema.md` | 直接复用 | profile.json schema_v1 |

**Skill 自洽**：所有 Layer 1 脚本 vendor 到 `scripts/`，运行时不依赖 mtb-core 路径。Provenance + 同步流程见 `scripts/README.md`。

## 9. PaddleOCR 集成

**venv**: `~/.venvs/mtb-ocr`（已装 paddleocr 3.4 + paddlepaddle 3.3 + paddlex）。v2 不要求用户自己装 paddlenlp（NER 走 regex fallback）。

**调用方式**: subagent 走 Bash → `subprocess.run([PADDLE_PYTHON, redact_ocr_path, image, "--output", out, "--no-ner"])`，捕 stdout JSON。

**Fallback**: 如检测到 venv 不存在或 paddleocr import 失败 → 自动降级到 v1 行为（Claude vision 直接 OCR），并在 readiness.warnings 标记 `paddleocr_unavailable`。

**首次运行性能**: PaddleOCR 模型懒加载，首次 OCR 约 +30s 模型下载/加载，之后 ~3-5s/图。63 张图实测 27.9 min（含 LLM 分类）。

## 10. 已做决策（不再讨论）

| 决策点 | v2 选择 | 理由 |
|---|---|---|
| Layer 2 用 Claude 还是 Gemini Flash | **Claude** | 已在 harness 内，省一层 LLM provider；审计更连贯 |
| 子桶分类沿用谁 | **mtb-core** taxonomy | 已成熟，直接抄 document-taxonomy.md |
| readiness schema | **v1 的 8 域 schema_v1** | 与 vmtb-skill / trial-match 互通是硬约束 |
| profile.json schema | **schema_v1** | 同上 |
| 是否保留 mtb-core 的 7 模块 readiness | **不保留** | 与下游 skill 不互通 |
| 是否兼容 v1 输出 | **不兼容** | 鼓励用户重新整理；v1 标记 deprecated 但不删 |
| OPENROUTER_API_KEY 依赖 | **零依赖** | mtb-core 用 Gemini Flash 来分类，v2 改 Claude 就不需要这个 key |
| PII 原始未遮挡镜像 | **保留**，仅本地 | 审计需要；下游 skill 永远只读脱敏版 |
| 哈希去重 | **SHA256**，同 hash 仅留 1 份 | 病历照片常拍多张 |

## 11. 开放问题（已锁定）

1. **patient_code 命名**: ✅ `PT-<hex>` 默认 + `--alias` 可选覆盖
2. **Layer 3.5 触发方式**: ✅ 自动检测（input 中包含 `*timeline*.txt` / `14_患者自管补充/` / `*manual*` / `*wechat*` 文件名时自动走 patient_curated 路径）
3. **去重粒度**: ✅ byte-level SHA256 — v2.0 简单优先；后续考虑 perceptual hash
4. **v1 用户迁移**: ✅ v2 自动检测旧 patient_dir 自动升级（看到 v1 schema 标记自动 reorganize）
5. **失败时回退**: ✅ skip + warning（写入 `readiness.warnings[]`）
6. **多语言**: ✅ 中文优先；英文 OCR 走 Claude vision fallback（PaddleOCR 中文模型遇英文准确度差）

## 12. 不在范围内（明确 out-of-scope）

- 临床判断 / 治疗建议（→ vmtb-skill / mtb-lite / cancer-buddy-pro-skill）
- 临床试验匹配（→ trial-match）
- 跨境 second-opinion packet（→ cancer-buddy-second-opinion）
- 影像 PACS DICOM 处理（仅图片 / PDF / OCR 文本）
- HIPAA 合规级 PII（v2 是 best-effort 中文医疗文档脱敏，不是法律级保证）
- 音视频原文件解析（仅接受用户提供的文本转录）

## 13. 文件清单（实施时创建）

```
~/.claude/skills/cancer-buddy-organize-local/
├── SKILL.md                              # 本 SPEC 落地为 SKILL.md
├── SPEC.md                               # 本文件 (历史保留)
├── scripts/                              # ★ vendored Layer 1 工具集 (skill 自洽, 不依赖 mtb-core 运行时路径)
│   ├── README.md                         # provenance + 同步流程 + 当前 SHA256 快照
│   ├── redact_ocr.py                     # PaddleOCR + PaddleNLP NER PII 双层脱敏
│   ├── extract_pdf.py                    # PDF 文本 (PyMuPDF + 内置 OCR fallback)
│   ├── extract_docx.py                   # DOCX 文本
│   ├── extract_excel.py                  # XLSX 文本
│   └── unpack_archive.py                 # zip/rar/7z/tar.gz 解压
├── references/
│   ├── organizer-prompt.md               # subagent 主提示词 (3 层 workflow)
│   ├── document-taxonomy.md              # 复制自 mtb-core
│   ├── subbucket-mapping.md              # 子桶映射规则
│   ├── ocr-sidecar-template.md           # Layer 1+2 输出格式
│   ├── review-flags-categories.md        # 6 类审计规则 (含 v2 新增 patient_curated_vs_formal)
│   └── paddleocr-integration.md          # subprocess 调用规范
└── tests/                                # (Phase 4 创建)
    ├── test-bingli/                      # 现有测试集
    └── expected_outputs/
        ├── profile.expected.json
        └── readiness.expected.json
```

## 14. 实施估时（Claude Code 协作）

| 阶段 | 工时 |
|---|---|
| Phase 0: SPEC review + 决策确认 | **现在** |
| Phase 1: 写 references/* (5 个文档) | 1.5 h |
| Phase 2: 写 SKILL.md (主 workflow) | 1 h |
| Phase 3: 写 references/organizer-prompt.md (3 层 subagent prompt) | 2 h |
| Phase 4: 跑 test-bingli/ 验证 + 调试 | 2 h |
| Phase 5: 写 cancer-buddy 父 skill 的路由更新 + 标 v1 deprecated | 0.5 h |
| **合计** | **~7 h** |

## 15. 验收标准（dogfood test）

用 `/Users/baozhiwei/Library/CloudStorage/坚果云-452858265@qq.com/我的坚果云/工作/cancerdao/患者/测试/test病历/` 跑 v2，期望输出：

- ✅ 63 文件全部分类，0 个"未知日期"（v1 已达成 / mtb-core 7 个失败）
- ✅ 同一份 MRI 报告只出现 1 次（mtb-core 出现 2 次）
- ✅ profile.json 字段数 ≥ 40（mtb-core 11 / v1 48）
- ✅ timeline.md 行数 ≤ 30 但每行是临床事件不是文件名（v1 28 行 ✓ / mtb-core 60+ 行文件清单 ✗）
- ✅ review_flags ≥ 8 项（v1 10 项 ✓ / mtb-core 0 项 ✗）
- ✅ PII 在 OCR sidecar 全部 [REDACTED]，90_原始文件镜像/ 保留明文（mtb-core ✓ / v1 ✗）
- ✅ 字符校正记录 ≥ 5 项（mtb-core ✓ / v1 ✗）
- ✅ 5 项 ground-truth 治疗事件依然漏（确认材料缺失而非 pipeline 缺陷）
- ✅ 处理时长 ≤ 35 min（mtb-core 27.9 min / v1 ~25 min）

## 16. Review 请求

@用户 请确认 / 推翻：

1. 第 10 节"已做决策"全部接受 ?
2. 第 11 节 6 个开放问题怎么定 ?
3. 是否要把 v1 立即标 deprecated ? 还是 v2 稳定后再标 ?
4. 实施次序: SPEC → references → SKILL.md → 测试，逐步交付 ?
