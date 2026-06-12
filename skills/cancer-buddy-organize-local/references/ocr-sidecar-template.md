# OCR Sidecar Template — cancer-buddy-organize-local

> Layer 1 (PaddleOCR + PaddleNLP NER) + Layer 2 (Claude vision 校对) 共同写入 `<patient_dir>/ocr/<basename>.md`。
> 每个图片/PDF 文件对应一个 sidecar。SOURCE/CONFIDENCE 标签是下游 skill 的 trust 凭证。

## 文件命名

`<patient_dir>/ocr/<basename>.md`，其中 `<basename>` = 重命名后的文件主名（不含扩展名）。

例：`05_影像/PET-CT/2026-01-09_PET-CT报告_宫颈癌,PET-CT,淋巴结转移.jpg` 对应 `ocr/2026-01-09_PET-CT报告_宫颈癌,PET-CT,淋巴结转移.md`

## 完整 sidecar 结构

> `MODALITY:` 是 `scheme_version: 3` 强制头部字段，描述数据本质（与临床域正交），ingest 解析分派按它走，不按桶（见 [`bucket-taxonomy.md`](bucket-taxonomy.md) §2 + [`ingest-adapters.md`](ingest-adapters.md)）。取值枚举：`text | image | structured | omics_raw | timeseries | binary_other`。

```markdown
# <basename>

> 原文件: `<original_name>` ｜ PII 遮挡: <N> 处 ｜ OCR 字符: <M>
> SOURCE: <source_type> ｜ CONFIDENCE: <high|medium|low>
> MODALITY: <text|image|structured|omics_raw|timeseries|binary_other>
> ORIGINAL: 90_原始文件镜像/<原始子目录>/<basename>
> SHA256: <16-char prefix>

## 字符校正 (Layer 2 audit)
- "1F-FDG" → "18F-FDG" (line 5, OCR 漏识别 8 字符)
- "肾孟" → "肾盂" (line 12, 形近字误识别)
- "5.7mmOl/L" → "5.7 mmol/L" (line 8, 大小写 + 空格)

## PII 二次脱敏追加 (Layer 2 audit)
- 检查号 PT26010800014 → [REDACTED] (Layer 1 NER 漏检, line 7)
- 床号 023 → [REDACTED] (Layer 1 NER 漏检, line 11)

## 文档元数据 (Layer 2 写入)
- type: PET-CT 报告
- target_directory: 05_影像/PET-CT/
- modality: image
- date: 2026-01-09
- hospital: 西安交通大学医学院第一附属医院
- summary: 宫颈癌患者 PET/CT 检查，宫颈及腹膜后、盆腔多发淋巴结代谢增高。
- classification_confidence: 0.92

## 关键指标 (Layer 2 抽取，仅当 source_type ∈ {imaging_report, lab_report, molecular_panel})
- SUVmax_cervix: 11.4
- SUVmax_pelvic_nodes: 3.5-7.5
- SUVmax_retroperitoneal_nodes: 4.7

## 异常项 (Layer 2 抽取，仅当 source_type = lab_report 且有越界值)
- 鳞状上皮细胞癌抗原 (SCC): 15.00 ng/mL (参考 < 3.0) ↑↑

## 文档正文（润色版）
<polished narrative — 由 Layer 2 校正字符 + 补全段落断句后的人类可读版>

## OCR 原文（PaddleOCR + NER 一次脱敏后）

<details><summary>点击展开原始 OCR 文本</summary>

```
<bbox-redacted PaddleOCR raw text — Layer 1 输出, 不做后处理>
```
</details>
```

## 字段语义

### SOURCE (枚举)

| 值 | 触发条件 | 默认 CONFIDENCE |
|---|---|---|
| `pathology_report` | 完整病理诊断 (大体 + 镜下 + 结论) | high |
| `discharge_summary` | 出院小结 / 出院证明书 | high |
| `admission_note` | 入院记录 / 入院小结 | high |
| `imaging_report` | 影像学报告（含放射科签字）| high |
| `lab_report` | 化验单（医院出具）| high |
| `molecular_panel` | NGS / IHC / HPV 分型 / 胚系 / 组学报告 | high |
| `prescription` | 处方笺 / 医嘱单 / 医保协议 | high |
| `colposcopy` | 阴道镜检查报告（仅观察）| high |
| `patient_note` | 患者拍照的检验单 / 报告（手机随手拍）| medium |
| `patient_curated` | 14_患者自管补充/ 下的所有材料 | low |
| `wechat_chat` | 14_患者自管补充/患者补充/ 微信聊天截图 | low |
| `voice_transcript` | 14_患者自管补充/患者补充/ 语音转录 | low |
| `handwritten_note` | 患者手写笔记 | low |

### MODALITY (枚举，scheme_version 3 强制)

描述源**数据本质**，与临床域正交，驱动 ingest 解析分派（见 [`bucket-taxonomy.md`](bucket-taxonomy.md) §2 + [`ingest-adapters.md`](ingest-adapters.md)）。

| 值 | 含义 | 例 | ingest 路径 |
|---|---|---|---|
| `text` | prose / OCR 文档 | 出院小结、病理叙述 | LLM Markdown 转写 |
| `image` | 影像 / 扫描，stub 摘要 | CT 序列、IHC 切片照 | LLM vision stub |
| `structured` | 表格数值报告 | 血常规、生化面板 | LLM 表格 → Markdown 表 |
| `omics_raw` | 原始组学载荷 | VCF / BAM / FASTQ / 表达矩阵 | omics ingest adapter |
| `timeseries` | 纵向流 | 可穿戴导出、血糖日志、PRO 量表 | timeseries adapter → longitudinal_observations.json |
| `binary_other` | 不支持/不透明二进制 | DICOM raw、专有导出 | stub + `[INGESTION_BLOCKED]`，永不静默丢弃 |

一个源 = 一个桶文件 + 一个 modality；复合源（NGS 报告 PDF + 其 VCF）算两条记录（`text` 报告 → `06`，`omics_raw` VCF → `06`）。

### CONFIDENCE (枚举)

| 值 | 含义 | 下游 skill 行为 |
|---|---|---|
| `high` | 医院盖章 / 签字 / 系统打印的正式文档 | 直接采信 |
| `medium` | OCR 有不确定性 / 患者拍照角度差 / 文字截断 | 需 `[需医嘱核对]` 标记 |
| `low` | 手写 / 患者口述 / 微信聊天 / 跨方转述 | 必须人工 review，不进 profile.json 主字段 |

**规则**：CONFIDENCE 一旦 medium / low，下游 skill（mtb-lite / vmtb / trial-match）读取时必须在引用处加 `[需医嘱核对]` 或 `[依据 patient_curated]` 标记。

### 字符校正记录

每条记录格式：`"<wrong>" → "<correct>" (line N, <reason>)`

reason 取值：
- `形近字误识别` (例: 孟/盂, 己/已, 末/未)
- `数字字母混淆` (例: 0/O, 1/I/l, 5/S)
- `OCR 漏识别` (例: "1F-FDG" 漏 "8")
- `OCR 多识别` (例: 多空格, 多标点)
- `大小写错误` (例: mmOl → mmol)
- `单位空格` (例: "5.7mmol/L" → "5.7 mmol/L")
- `中英混排断字` (例: "SUVmax11.4" → "SUVmax 11.4")

**禁止**做"语义级修正"（如把"病理示鳞癌"改成"病理示宫颈鳞癌"）— 那不是 OCR 校正，那是创造内容。

### PII 二次脱敏

Layer 1 (PaddleNLP NER) 漏检的 PII，由 Layer 2 (Claude) 二次复查。常见漏检：
- 检查号 / 报告单号 / 影像号 (regex 不规则的数字串)
- 床号 / 病区编号
- 主治医师签名（手写体）
- 患者亲属姓名（病历"陪同人:"字段）

每条记录格式：`<PII 类型> <原值> → [REDACTED] (Layer 1 NER 漏检, line N)`

### classification_confidence

Layer 2 对桶 + 子桶分类决策的自评分（0-1）。

- ≥ 0.7 → 子桶
- 0.5–0.7 → 子桶 + readiness.warnings 加 `low_confidence_classification: <basename>`
- < 0.5 → `99_无关文件/uncertain/`

## 完整 example：PET/CT 报告

```markdown
# 2026-01-09_PET-CT报告_宫颈癌,PET-CT,淋巴结转移

> 原文件: `2026.1.9 PET:CT.jpg` ｜ PII 遮挡: 5 处 ｜ OCR 字符: 866
> SOURCE: imaging_report ｜ CONFIDENCE: high
> MODALITY: image
> ORIGINAL: 90_原始文件镜像/<原始子目录>/2026-01-09_PET-CT报告_宫颈癌,PET-CT,淋巴结转移.jpg
> SHA256: a4cda42e02a0bedc

## 字符校正 (Layer 2 audit)
- "1F-FDG" → "18F-FDG" (line 5, OCR 漏识别)
- "肾孟" → "肾盂" (line 12, 形近字误识别)
- "5.7mmOl/L" → "5.7 mmol/L" (line 8, 大小写 + 单位空格)
- "SUVma3.5-7.5" → "SUVmax 3.5-7.5" (line 18, OCR 漏识别 + 中英混排断字)

## PII 二次脱敏追加 (Layer 2 audit)
- 检查号 PT26010800014 → [REDACTED] (Layer 1 NER 漏检, line 7)

## 文档元数据
- type: PET-CT 报告
- target_directory: 05_影像/PET-CT/
- modality: image
- date: 2026-01-09
- hospital: 西安交通大学医学院第一附属医院
- summary: 宫颈癌患者 PET/CT 检查，宫颈及腹膜后、盆腔多发淋巴结代谢增高，提示肿瘤浸润及淋巴结转移。
- classification_confidence: 0.92

## 关键指标
- SUVmax_cervix: 11.4
- SUVmax_pelvic_nodes: 3.5-7.5
- SUVmax_retroperitoneal_nodes: 4.7
- SUVmax_tonsil: 7.5 (反应性，非肿瘤)

## 异常项
- 宫颈代谢异常增高
- 腹膜后多发肿大淋巴结
- 盆腔多发肿大淋巴结
- 左侧肾上腺内支结节状稍低密度影 (无核素摄取)

## 文档正文（润色版）

### 检查报告：PET/CT
- **医院**：西安交通大学医学院第一附属医院
- **检查日期**：2026-01-09
- **检查部位**：躯干
- **检查号**：[REDACTED]
- **临床诊断**：宫颈癌

### 病史摘要
患者 2 月余前出现同房后出血，量不多。就诊于西北妇幼医院，行阴道镜下活检，病理示：宫颈鳞癌。此次 PET/CT 检查目的：协助分期。

### 检查过程
- 显像剂：18F-FDG
- 注射剂量：185 MBq, 静脉注射
- 血糖值：5.7 mmol/L
- 过程：禁食状态下静脉注射 18F-FDG，60 分钟后行 PET/CT 扫描，3D 采集，计算机重建横断面、冠状面、矢状面，同机图像融合。

### 影像学所见
- **颈部**：甲状腺右叶可见低密度结节影，未见异常核素分布。双侧扁桃体对称性核素摄取增高，SUVmax 7.5（反应性）。
- **胸部**：两肺野清晰，未见异常浓聚灶。
- **腹部**：左侧肾上腺内支可见结节状稍低密度影，核素摄取未见增高。腹膜后可见多发肿大淋巴结影，核素摄取增高，SUVmax 4.7。
- **盆腔**：宫颈核素摄取异常增高，SUVmax 11.4；盆腔多发肿大淋巴结（右侧为著），SUVmax 3.5-7.5。
- **骨骼**：未见异常核素分布。

### 结论
宫颈癌 PET/CT 显像：宫颈及盆腔、腹膜后多发淋巴结转移。

## OCR 原文（PaddleOCR + NER 一次脱敏后）

<details><summary>点击展开</summary>

\`\`\`
西安交通大学医学院第一附属医院
PET/CT 报告单
年龄: 43 岁
性别: 女
检查时间: 2026-01-09
检查部位: 躯干
检查号: PT26010800014
显像剂: 1F-FDG
注射剂量: 185 MBq
给药途径: 静脉注射
临床诊断: 宫颈癌
病史摘要:
2 月余前出现同房后出血，量不多，未在意...
受检者空腹血糖值为 5.7mmOl/L
...肾孟无扩张...
盆腔可见多发肿大淋巴结影 (右侧为著), 核素摄取增高, SUVma3.5-7.5
\`\`\`

</details>
```

## 反例（禁止）

❌ **不要**省略 SOURCE / CONFIDENCE — 下游 skill 拒绝读取无标签 sidecar
❌ **不要**修改 OCR 原文区块 — 那是 Layer 1 输出的审计原件
❌ **不要**在润色版里加入 OCR 没有的内容（"我推测"、"可能是" 一律不写）
❌ **不要**把 PII 删除而不在"二次脱敏"区记录（审计要求每个 [REDACTED] 都有溯源）
❌ **不要**把多张图合并到一个 sidecar — 一图一 sidecar
