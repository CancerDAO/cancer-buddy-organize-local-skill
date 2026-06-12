---
name: cancer-buddy-organize-local
description: Use when the user provides a folder / archive / single doc of cancer patient medical records (PDF / JPG / PNG / DOCX / .zip) and asks to organize / 整理病历 / 整理报告 / 整理这堆检查单, AND wants local PaddleOCR + NER PII redaction instead of cloud Claude vision. Or when any cancer-buddy / vmtb sub-skill detects missing profile.json / readiness.json on a privacy-sensitive install. Produces canonical patients/<patient_code>/ with profile.json (schema_v1, 48 fields), timeline.md (clinical events), readiness.json (8 domains + review_flags), case_text.md, files sub-categorized into the scheme_version-3 taxonomy of 14 clinical domains (+2 infra), OCR sidecars with PII double-redaction + character corrections + a modality tag, and patient_curated diary merge. Drop-in replacement for cancer-buddy-organize — same output schema, harder-OCR privacy floor, requires local Python + PaddleOCR venv.
---

# cancer-buddy-organize-local

Turn raw patient files into a canonical patient directory with **clinical-grade analysis** (irAE / trends / 6-class audit) **on top of audit-grade OCR** (local PaddleOCR + double PII redaction + character correction).

**Drop-in replacement for `cancer-buddy-organize`** — produces the exact same `profile.json` schema_v1 / `timeline.md` / `readiness.json` contract, so every downstream cancer-buddy / vmtb sub-skill works unchanged. The difference is the OCR floor: this skill runs PaddleOCR + PaddleNLP NER locally (字符精度可审计 + PII 图层遮挡 + 二次复查) instead of the default Claude vision pipeline. Trade: requires local Python venv with PaddleOCR installed (see [INSTALL.md](../../INSTALL.md)).

## Core principle

**3 layers + 1 patch channel** — each layer outputs an artifact the next layer reads, no layer rewrites another layer's output.

```
Layer 1: 本地 PaddleOCR → ocr/<basename>.md (字符 + 双层 PII 脱敏)
Layer 2: Claude vision  → 14 临床域 (+2 infra) + 子桶分类 + modality 标签 + 去重 + 字符校正补救
                       + 复制时保留原始 basename（命名不在 Layer 2 做）
Layer 2.5: 你 (LLM) 判断  → 每文件 {date, doc_type, 机构, page}
                       + 患者级 {cancer_label, first_dx_date}
                       → 写 .rename_plan.json (semantic, 不用 regex)
Layer 2.6: bash 机械执行  → 原子 mv + 冲突后缀 + manifest / sidecar SOURCE
                       / _FILENAME_MAPPING 全量回填
                       + patient_dir → <cancer>_<YYYY-MM>_<hash4>
Layer 3: Claude text    → profile.json (schema_v1) + timeline.md (临床事件) + 6 类 review_flags
Layer 3.5: 患者补充 merge → 14_患者自管补充/ 进 patient_curated 标签
```

Final artifact root: `<patient_dir>/` per [`../../references/patient-profile-schema.md`](../../references/patient-profile-schema.md). Schema is shared with vmtb-skill / cancer-buddy-mtb-lite / cancer-buddy-trial-match.

## When to use

- 用户说"整理病历 / 帮我整理这些报告 / 我有一堆检查单"
- 用户给出一个文件夹路径 / .zip / .rar / .7z / .tar.gz / 单个 .pdf / .docx
- 任何下游 cancer-buddy / vmtb sub-skill 检测到 profile.json / readiness.json 缺失，提示用户先 organize
- 用户已有 default organize 的 patient_dir，想原地切到本地 OCR 流水线（自动检测）

## When NOT to use

- 用户直接想要 MTB / vMTB 报告（→ `cancerdao-vmtb` 或 `cancer-buddy-mtb-lite`）
- 用户问"哪家医院能做 MTB"（→ `cancer-buddy-find-care`）
- 用户问治疗方案 / 副作用怎么处理（→ 主诊医生）
- 患者画像生成（→ `cancer-buddy` 父 skill 路由）

## Inputs

- `input_path` (必填)：folder / .zip / .rar / .7z / .tar.gz / .pdf / .docx 绝对路径
- `--alias <name>` (可选)：覆盖默认 `PT-<hex>` patient_code（例 `--alias 程女士-2026`）。**v2.1 警告**：`--alias` 包含真名时调用方必须主动告知用户："patient_code 会出现在所有路径 / 下游报告 / 文件系统 — 用真名意味着 PII 直接暴露在文件系统层"。生产数据建议一律 `PT-<hex>`，仅 demo / 教学 / 单人本地审阅场景才用真名 alias。
- `--merge-into <patient_code>` (可选, 显式触发 Layer 3.5)：把 input 内容作为补充材料 merge 进已有 patient_dir

## Outputs

`<patient_dir>/` 下：

- `INDEX.md` (顶部 readiness 摘要 + 关键指标 + 治疗线 + 文档索引)
- `profile.json` (schema_v1, 48 字段 + irAE 时序 + caregivers + disclosure_state)
- `timeline.md` (≤30 行临床事件流，**不是文件清单**)
- `readiness.json` (8 域评分 + blocking_gaps + review_flags)
- `review_flags.md` (review_flags 非空时自动渲染 — 🔴/🟡/🟢 三级)
- `case_text.md` (整合叙事，按身份基础信息→既往史家族史→病程文书→诊断分期→影像→分子组学→检验→治疗→手术操作→随访→会诊顺序)
- `01_身份与基础信息/` ~ `14_患者自管补充/` (14 临床域 + 子桶细分原件；见 [`references/bucket-taxonomy.md`](references/bucket-taxonomy.md) §1)
- `14_患者自管补充/` (患者补充 / 日记 / 自测 / conversation_notes — local-variant exclusive)
- `90_原始文件镜像/` (HIDDEN 字节级镜像，保留原始子目录，PII 未脱敏，仅本地审计)
- `90_原始文件镜像/_duplicates/` (SHA256 去重副本)
- `longitudinal_observations.json` (纵向流观测值；timeseries / 趋势 structured 源，见 bucket-taxonomy.md §3)
- `ocr/<basename>.md` (每文件一个，含 SOURCE/CONFIDENCE/字符校正/PII 二次脱敏/正文润色版)

完整布局见 [SPEC.md §4](SPEC.md)。

## Workflow

### Step 0 — Pre-flight

1. 解析 `input_path`，确认存在，向用户复述："我要整理 `<path>` (检测到 N 个文件 / 1 个 .zip / ...)"
2. 自动检测 14_患者自管补充/ 触发条件（见 [`references/subbucket-mapping.md`](references/subbucket-mapping.md) §3）：
   - 文件名匹配 `*timeline*.txt` / `*整理*.txt` / `*manual*` → Layer 3.5 模式
   - 否则 Layer 1-3 全 pipeline 模式
3. 检测 PaddleOCR 可用性（见 [`references/paddleocr-integration.md`](references/paddleocr-integration.md) §自检命令）：
   - `~/.venvs/mtb-ocr/bin/python -c "import paddleocr"` 不通过 → 提示用户安装 OR 走 v1 兼容降级
4. 解析 `patient_data_root`：`$CANCER_BUDDY_PATIENTS_DIR` → `$VMTB_PATIENT_DATA_ROOT` → `$HOME/CancerDAO/patients`
5. 生成 / 解析 `patient_code`：默认 `PT-<10 位 hex from SHA256(basename + mtime)>`，`--alias` 时用 alias，碰撞时追加 `_2`/`_3`。**alias 含真名时**（启发式：包含 ASCII 大写名 + 小写姓 / 中文 2-4 字 / 完整生日年份等模式），dispatcher 必须先输出："`<alias>` 看起来含真实姓名 — 默认应使用 `PT-<hex>` 避免文件系统 PII 暴露；确认仍要用 alias 吗？" 等待显式确认才继续。

### Step 1 — Dispatch organizer subagent

派发 `general-purpose` subagent，prompt = [`references/organizer-prompt.md`](references/organizer-prompt.md) 全文 + 末尾 append `## Call parameters`：

```
- input_path: <absolute path>
- patient_code: <PT-hex or alias>
- patient_data_root: <resolved>
- mode: <full | merge_only | default_upgrade>
- paddle_python: <~/.venvs/mtb-ocr/bin/python or "fallback">
- skill_dir: <absolute path to this skill — Layer 1 scripts live in $skill_dir/scripts/. Typical install: ~/.claude/skills/cancer-buddy-organize-local>
```

Subagent 跑完返回 pure JSON：

```json
{
  "role": "organizer-local",
  "patient_dir": "/abs/path/PT-XXXXXXXXXX",
  "files_classified": 63,
  "files_deduplicated": 4,
  "files_unclassified": 0,
  "ocr_sidecars_generated": 38,
  "paddleocr_used": true,
  "paddleocr_failure_count": 0,
  "vision_fallback_count": 0,
  "readiness_grade": "B",
  "readiness_score": 72,
  "blocking_gaps": ["无 PD-L1 CPS 检测", "无病理报告原件"],
  "warnings": ["PII 未做 redaction (姓名)"],
  "review_flags_total": 10,
  "review_flags_red": 4,
  "review_flags_yellow": 4,
  "review_flags_green": 2,
  "patient_curated_merged": false
}
```

### Step 2 — Verify outputs

校验返回 JSON：
- `review_flags_total` 字段必须存在（缺失 → subagent 不合规，重派一次显式提醒跑 Layer 3 §4.6）
- `profile.json` 存在 + 必填字段 (`patient_code`, `primary_cancer`, `histology`, `stage`) 全部 non-null
- 任一必填字段缺失 → 给用户明确 blocker，**不**路由到下游 sub-skill

### Step 3 — Grade readiness + surface review_flags

读 `readiness.json`：

- Grade F / D → 优先展示 information-gap checklist 🔴🟡🟢（来自 `blocking_gaps`）
- Grade B / A → 直接展示 Patient Profile Card

**review_flags 强制 surface（硬门）**：

- `review_flags_total > 0` → 读 `review_flags.md` 完整内容展示给用户（在 Patient Profile Card 之后）
  - 含 🔴 → 加一句 "进入下游 skill 之前请先逐条确认或 override 这些 🔴 项 — 它们会直接影响 trial-match / mtb-lite / vmtb 的推荐"
  - 仅 🟡/🟢 → 标 "建议核对"，不 block 下游
- `review_flags_total == 0` → 主动告诉用户："所有提取字段已通过 6 项可疑值检查 (格式/跨文档矛盾/临床逻辑/原始证据/数值趋势/患者补充冲突), 无待确认项"

### Step 4 — Display Patient Profile Card

按 [`../../references/profile-card.md`](../../references/profile-card.md) 模板渲染，使用 [`../../references/terminology.md`](../../references/terminology.md) 的中英 + 通俗解释格式。

### Step 5 — Suggest next step

按用户最初的问题路由到下游：

| 用户语境 | 推荐路径 |
|---|---|
| 想跑 vMTB / 分子肿瘤会诊 | `/cancerdao-vmtb` 或 `/cancer-buddy-mtb-lite` |
| 找做 MTB / 试验的医院 | `/cancer-buddy-find-care` |
| 患者教育手册 | `/vmtb-patient-education` 或 `/cancer-buddy-education` |
| 第二意见 packet | `/cancer-buddy-second-opinion` |
| 建个人数据仓 | `/cancer-buddy-vault` |
| 营养计划 | `/cancer-buddy-nutrition` |
| 心理筛查 | `/cancer-buddy-mind` |

## 从默认 organize 原地升级

如 `<patient_data_root>/<patient_code>/` 已存在且检测到旧 schema（无 `14_患者自管补充/` 子桶 / 无 `04_诊断与分期/病理报告/` 子桶 / OCR sidecar 缺 SOURCE 或 MODALITY 标签 / 存在已废弃的 `01_当前状态` `10_原始文件` 等旧前缀），询问用户是否原地升级：

- **是** → mode=`default_upgrade`，subagent 重新跑 Layer 1-3，原文件移到 `_default_archive_<timestamp>/` 备份
- **否** → 走默认 patient_code 碰撞规则，追加 `_local`/`_local2`/...

## 与默认 `cancer-buddy-organize` 的关键差异（用户视角）

- ✅ 新增：本地 PaddleOCR 字符级 OCR + 双层 PII 脱敏（默认版本是 Claude vision 黑盒）
- ✅ 新增：14_患者自管补充/ 通道 — 患者手写 timeline / 微信 / 语音转录 也能合并
- ✅ 新增：05_影像 / 06_分子与组学 / 07_检验 / 08_治疗 等桶下子桶细分（默认是桶级平铺）
- ✅ 新增：SHA256 文件去重（默认可能让同一份 MRI 进 2 次）
- ✅ 新增：review_flags 第 6 类 `patient_curated_vs_formal`
- ✅ 新增：英文文档 fallback Claude vision（PaddleOCR 中文模型对英文准确度差）
- ⏸ 保留：profile.json schema_v1 与 cancer-buddy-skill 主仓 / vmtb-skill 完全互通（不变）
- ⏸ 保留：timeline.md 是临床事件流而非文件清单（不变）
- ⏸ 保留：review_flags 审计（从默认 5 类扩到 6 类）

## Role behavior

| Role | 行为 |
|---|---|
| **patient** | 第一人称 "帮我整理我的病历" → 正常跑 pipeline。data_sources 里以 patient 为 source。disclosure_state=suppressed 时警告 organize 会破坏 suppression，需用户确认 |
| **caregiver** | 第二人称 "帮你家人整理报告"。首次 organize 询问 caregiver 关系 + 联系方式，写入 `profile.json.caregivers[]` |
| **family** | 拒绝："病历整理要靠主照护者操作（Ta 手里有原件）。要不要生成一份 2 页要点让 Ta 参考？" 不跑 organize |

详见 [`../../references/roles.md`](../../references/roles.md)（vendored from cancer-buddy-skill main repo）。

## Safety

- 本 skill 不做临床判断 / 治疗建议 / MTB 评估 — 这些由下游 sub-skill 处理
- 永不**捏造**字段：unreadable → `null` (JSON) 或 `[OCR_UNCERTAIN]` (text)
- `90_原始文件镜像/` 是 HIDDEN 字节级镜像 — 永远本地 only，永不患者可见 / 永不锚定，下游 skill 永远只读脱敏版
- 字符校正只能改 OCR 错字，**禁止**做语义改写（"病理示鳞癌" → "病理示宫颈鳞癌" 这是创造内容）
- review_flags 非空且含 🔴 → 必须 block 用户进下游 skill 之前明确逐项确认

完整 safety 清单见 [`../../references/safety-guardrails.md`](../../references/safety-guardrails.md)（vendored from cancer-buddy-skill main repo）。

## Verification — dogfood test

在一份典型 63-file 多次住院档案上跑期望产出（[SPEC.md §15](SPEC.md) 完整 9 项）：

- ✅ 63 文件全部分类，0 个"未知日期"
- ✅ 同一份 MRI 报告只出现 1 次
- ✅ profile.json 字段数 ≥ 40
- ✅ timeline.md ≤ 30 行 + 每行临床事件
- ✅ review_flags ≥ 8 项（含 patient_curated_vs_formal 至少 1）
- ✅ PII 全部 [REDACTED] in OCR sidecar；明文仅在 90_原始文件镜像/
- ✅ 字符校正记录 ≥ 5 项
- ✅ 5 项 ground-truth 治疗事件（后装内照射 / 胸腺法新等）依然漏 — 确认材料缺失而非 pipeline 缺陷
- ✅ 处理时长 ≤ 35 min

## References

- [SPEC.md](SPEC.md) — 完整设计 + 决策 + 验收
- [references/bucket-taxonomy.md](references/bucket-taxonomy.md) — **权威** scheme_version 3 定义（14 临床域 + 2 infra + modality + 纵向流）
- [references/ingest-adapters.md](references/ingest-adapters.md) — 按 modality 的 ingest 适配器（omics_raw / timeseries / binary_other）
- [references/document-taxonomy.md](references/document-taxonomy.md) — 文档类型 → 临床域 对照表
- [references/subbucket-mapping.md](references/subbucket-mapping.md) — 子桶 + 14_患者自管补充检测
- [references/ocr-sidecar-template.md](references/ocr-sidecar-template.md) — Layer 1+2 sidecar schema
- [references/review-flags-categories.md](references/review-flags-categories.md) — 6 类审计规则
- [references/schemas/longitudinal_observations.schema.json](references/schemas/longitudinal_observations.schema.json) — 纵向流观测值 store schema
- [references/paddleocr-integration.md](references/paddleocr-integration.md) — subprocess + venv + fallback
- [references/organizer-prompt.md](references/organizer-prompt.md) — subagent 主提示词（含 Layer 2.5/2.6 canonical 命名）
- [../../references/profile-card.md](../../references/profile-card.md) — Patient Profile Card 模板（与 cancer-buddy-organize 共享）
- [../../references/patient-profile-schema.md](../../references/patient-profile-schema.md) — schema_v1 contract（与 cancer-buddy-skill 主仓双向同步）
- [../../references/safety-guardrails.md](../../references/safety-guardrails.md) — 安全红线（与 cancer-buddy-skill 主仓双向同步）
- [../../references/roles.md](../../references/roles.md) — role routing（与 cancer-buddy-skill 主仓双向同步）
- [../../references/terminology.md](../../references/terminology.md) — 术语本
