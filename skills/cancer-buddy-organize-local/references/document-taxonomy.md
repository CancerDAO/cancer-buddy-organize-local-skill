# 医疗文档分类法 — Document Taxonomy

本文档为 Agent 分类医疗文档时的参考手册（`scheme_version: 3`）。Agent 应通过阅读和理解文档内容来判断文档类别，而非依赖关键词匹配。

> 目标目录列 = [`bucket-taxonomy.md`](bucket-taxonomy.md) §1 的 14 临床域 (+2 infra) 子桶。冲突以 `bucket-taxonomy.md` 为准。
> 单一分类轴 = **临床域**（modality-agnostic）。modality（text/image/structured/omics_raw/timeseries/binary_other）是正交标签，由 ingest 解析分派读取，不决定桶（见 `bucket-taxonomy.md` §2 + [`ingest-adapters.md`](ingest-adapters.md)）。

## 分类对照表

| 文档类型 | 目标目录 | 文档特征描述 | 提取字段 |
|----------|----------|-------------|----------|
| 出院小结 | `03_病程与叙事文书/出院小结/` | 医院出具的出院证明或出院小结，包含入院/出院日期、住院期间诊治经过、出院诊断和出院医嘱。通常有"出院小结"、"出院证明"等标题。 | admission_date, discharge_date, diagnosis, treatment_during_stay, discharge_instructions |
| 入院记录 | `03_病程与叙事文书/入院记录/` | 患者入院时的记录，包含主诉、现病史、入院诊断和初步治疗计划。有"入院记录"、"入院小结"等标题，但不含出院相关内容。 | admission_date, chief_complaint, admission_diagnosis, history_of_present_illness, initial_treatment_plan |
| 病程记录 | `03_病程与叙事文书/病程记录/` | 日常病程记录 / 查房记录，记录住院期间病情演变与处置。 | record_date, course_notes, plan_updates |
| 门诊病历 | `03_病程与叙事文书/门诊病历/` | 门诊就诊记录（visit note），包含就诊日期、接诊医生、门诊诊断和处置（非处方笺本体）。 | visit_date, doctor, diagnosis, disposition |
| CT报告 | `05_影像/CT/` | 计算机断层扫描（CT）的影像学检查报告，包含扫描部位、影像学发现和诊断意见。报告标题或内容涉及CT平扫、增强CT、计算机断层等。 | scan_date, scan_region, findings, impression |
| MRI报告 | `05_影像/MRI/` | 磁共振成像（MRI）检查报告，包含扫描部位和影像发现。报告涉及磁共振、MRI、核磁共振等检查方式。 | scan_date, scan_region, findings, impression |
| PET-CT报告 | `05_影像/PET-CT/` | PET-CT 或 PET/CT 代谢显像报告，包含 SUV 摄取值和代谢活性描述。通常用于肿瘤分期或疗效评估。 | scan_date, findings, SUVmax, impression |
| 超声报告 | `05_影像/超声/` | 超声/B超/彩超检查报告，包含超声探查部位和声像图描述。常见于腹部、甲状腺、乳腺等脏器检查。 | scan_date, scan_region, findings, impression |
| X光/DR报告 | `05_影像/X光DR/` | X射线或数字化摄影（DR）检查报告，包含拍摄部位和影像学发现。常见于胸部X光、骨骼X光等。报告标题常含"DR"、"X线"、"X光"、"放射"等字样。 | scan_date, scan_region, findings, impression |
| 核医学/骨扫描 | `05_影像/核医学/` | 核素显像 / 骨扫描 / SPECT（非 PET-CT）报告，包含核素分布与异常摄取灶描述。 | scan_date, tracer, findings, impression |
| 内镜影像 | `05_影像/内镜影像/` | 胃镜/肠镜/支气管镜/阴道镜（仅观察 + 拟诊，无活检结论）的内镜检查报告。 | scan_date, scope_type, findings, impression |
| 血常规 | `07_检验/血常规/` | 血液常规检验报告，包含白细胞、红细胞、血红蛋白、血小板等血细胞计数和分类结果。 | test_date, WBC, RBC, HGB, PLT, abnormal_items |
| 生化/肝肾功能 | `07_检验/生化肝肾功/` | 血液生化检验报告，包含肝功能（ALT、AST、胆红素等）、肾功能（肌酐、尿素氮等）、电解质、血脂、血糖等项目。也包括单项肝功、肾功检测报告。 | test_date, ALT, AST, creatinine, BUN, abnormal_items |
| 肿瘤标志物 | `07_检验/肿瘤标志物/` | 肿瘤标志物检测报告，包含 CEA、CA-199、AFP、CA-125 等肿瘤相关蛋白或抗原的血清浓度值。报告标题常含"肿瘤标志物"、"癌胚抗原"等。 | test_date, CEA, CA199, AFP, CA125, other_markers |
| 凝血 | `07_检验/凝血/` | 凝血功能检验报告（PT/INR/APTT/D-dimer/纤维蛋白原）。 | test_date, PT, INR, APTT, D_dimer, fibrinogen |
| 尿便常规 | `07_检验/尿便/` | 尿常规 / 便常规检验报告。 | test_date, items, abnormal_items |
| 其他检验（免疫/淋巴亚群/甲功/性激素/心标/ESR/CRP/PCT/Vit D 等） | `07_检验/其他/` | 不属于上列子桶的检验项目，含免疫球蛋白/补体/自身抗体/病毒筛查/淋巴亚群/甲功/性激素/心脏标志物/ESR/CRP/PCT/Vit D/B12/HbA1c 等。 | test_date, items, abnormal_items |
| 基因检测/NGS | `06_分子与组学/NGS报告/` | 体细胞基因检测或二代测序（NGS）报告，包含基因突变位点、突变频率（VAF）、MSI状态、TMB数值和药物敏感性分析。 | test_date, mutations, MSI_status, TMB, drug_sensitivity |
| 免疫组化 | `06_分子与组学/免疫组化/` | 免疫组化（IHC）单独报告，仅包含免疫组化染色标记物结果（如 PD-L1、HER2、Ki-67、MLH1、MSH2等蛋白表达情况），不含完整病理诊断。 | test_date, markers, expression_levels |
| 胚系检测 | `06_分子与组学/胚系检测/` | 胚系（遗传性）突变检测报告（如 BRCA / Lynch panel）。 | test_date, germline_variants, classification |
| HPV 分型 | `06_分子与组学/其他/` | HPV PCR 基因分型报告（16/18/31/33/...），常见于宫颈/口咽/肛管癌。 | test_date, hpv_genotypes, result |
| WES/WGS · 转录组 · 甲基化 · 蛋白代谢 · 微生物组 | `06_分子与组学/{WES-WGS,转录组,甲基化,蛋白-代谢,微生物组}/` | 各类组学测序报告，按组学类型落到对应子桶。 | assay, platform, summary |
| 病理报告 | `04_诊断与分期/病理报告/` | 完整的病理检查报告，包含标本大体描述、镜下描述、病理诊断（组织学类型、分化程度、分期等）。可能附带免疫组化结果，但主体是病理诊断。包括活检病理和术后病理。 | biopsy_date, specimen_source, histology, grade, stage, margins |
| 分期评估 | `04_诊断与分期/分期评估/` | TNM/FIGO 分期评估文书。 | stage_date, staging_system, stage |
| 诊断证明 | `04_诊断与分期/诊断证明/` | 医院开具的诊断证明书，用于证明患者疾病诊断，通常包含医院名称、就诊/住院日期、临床诊断、治疗概况和医生建议。格式较简短，主要用途为对外证明（如请假、保险等）。 | hospital, admission_date, discharge_date, diagnosis, treatment_summary, recommendations |
| 手术记录 | `09_手术与操作/手术记录/` | 手术记录单，含术式、术中所见、切除范围。 | op_date, procedure, findings, specimen |
| 麻醉记录 | `09_手术与操作/麻醉记录/` | 麻醉记录单。 | op_date, anesthesia_type, course |
| 内镜操作/活检手术 | `09_手术与操作/内镜操作/` | 内镜下治疗/活检操作记录（含阴道镜下活检 + ECC 手术记录，无病理结论）。 | op_date, procedure, findings |
| 化疗记录 | `08_治疗/化疗/` | 化疗医嘱 / 出库单 / 化疗执行记录。 | cycle_date, regimen, cycle_no |
| 放疗记录 | `08_治疗/放疗/` | 外照射 / 后装腔内 / 立体定向 / 质子放疗记录。 | rt_date, modality, dose_fractions |
| 免疫/靶向/内分泌治疗 | `08_治疗/{免疫治疗,靶向,内分泌}/` | 免疫检查点抑制剂 / TKI单抗 / 内分泌治疗记录，按治疗类落子桶。 | tx_date, drug, line |
| 处方/医嘱 | `08_治疗/处方医嘱/` | 处方笺或医嘱单（prescription 本体），含就诊日期、接诊医生、处方用药信息。 | visit_date, doctor, prescriptions |
| 支持治疗 | `08_治疗/支持治疗/` | 升白/升板/升红/镇痛/止吐/营养等支持治疗记录。 | tx_date, supportive_drug |
| 随访复查 | `10_随访与监测/随访复查/` | 随访 / 复查记录。 | followup_date, summary |
| 可穿戴/PRO/居家监测导出 | `10_随访与监测/{可穿戴导出,PRO自报,居家监测}/` | 纵向流原始导出文件（设备 CSV / PRO 量表系列 / 居家血压血糖体温日志）；解析后观测值进 longitudinal_observations.json。 | series, date_span, metrics |
| 会诊/转诊/MDT/第二意见 | `11_会诊与转诊/{MDT,会诊,转诊,第二意见}/` | 多学科会诊纪要 / 单科会诊意见 / 转诊单 / 第二意见文书。 | date, specialty, opinion |
| 既往史/家族史/过敏史/用药史 | `02_既往史与家族史/{既往病史,手术史,过敏史,用药史,家族史,胚系遗传}/` | 既往病史 / 既往手术史 / 过敏史 / 长期用药史 / 家族肿瘤遗传史叙述。 | items |
| 身份/参保信息 | `01_身份与基础信息/{身份证件,人口学,参保信息}/` | 身份证件影印 / 人口学基础信息 / 医保参保凭证。 | demographics, insurance |
| 心理/营养/康复/缓和/社工 | `12_心理社会与支持/{心理评估,营养,康复,缓和,社工}/` | 心理量表 / 营养方案 / 康复计划 / 缓和医疗 / 社工记录。 | date, assessment |
| 知情同意/费用/医保报销/证明 | `13_行政与财务/{知情同意,费用发票,医保报销,证明材料}/` | 知情同意书 / 费用清单发票 / 医保报销凭证 / 对外证明（非诊断证明）。 | date, document_type |
| 患者补充材料 | `14_患者自管补充/{患者补充,日记,自测,conversation_notes}/` | 患者/家属手工整理材料 / 日记 / 自测数据 / chat-captured 事实。 | source, confidence |

## 分类优先级规则

当文档内容涉及多种文档类型特征时，按以下优先级判定：

### 规则 1：出院小结/出院证明优先

如果文档的主要内容是出院相关信息（出院小结、出院证明书），**直接归类为出院小结**，即使文档中附带了检验结果或影像报告摘要。

> 理由：出院小结是综合性文档，通常包含患者住院期间所有检查结果的摘要。

### 规则 1b：入院小结识别

如果文档主体是入院时的记录（入院小结、入院记录），且不涉及出院内容，归类为**入院小结**。

> 理由：入院小结记录患者入院时的初始状态和诊断，与出院小结是独立文档类型。

### 规则 2：完整病理报告 > 单独免疫组化

如果文档同时包含病理诊断和免疫组化结果：
- 如果有完整的病理诊断（包括大体描述、镜下描述、病理诊断结论），归入 **病理报告**
- 如果仅有免疫组化标记物结果表格，无完整病理诊断，归入 **免疫组化**

### 规则 3：基因检测 vs 免疫组化

如果文档同时涉及基因检测和免疫组化内容：
- 主要内容是基因突变位点列表、变异频率（VAF）、MSI/TMB → **基因检测**
- 主要内容是蛋白表达水平、IHC评分 → **免疫组化**

### 规则 4：影像学子类判定

影像报告的子类型根据检查方式判定：
1. PET代谢显像 → PET-CT
2. 磁共振成像 → MRI
3. CT断层扫描 → CT
4. X射线/DR摄影 → X光DR
5. 超声探查 → 超声

### 规则 5：检验报告子类判定

检验报告根据检测项目的主体内容判定：
1. 以肿瘤标志物（CEA、CA-199、AFP、CA-125等）为主 → 肿瘤标志物
2. 以血细胞计数为主（白细胞、红细胞、血红蛋白、血小板） → 血常规
3. 以生化指标为主（肝功、肾功、电解质、CRP等） → 生化肝肾功

### 规则 6：诊断证明识别

如果文档是医院开具的诊断证明书（通常较短，用于对外证明用途），归入 **诊断证明**，不要与出院小结混淆。

### 规则 7：无法判断

如果以上规则均不能确定文档类别，归入 `99_无关文件/uncertain/`，并提示用户手动确认分类。

## 各类型详细提取指南

### 出院小结

需提取的关键信息：
- 入院日期、出院日期
- 入院诊断、出院诊断
- 住院期间治疗经过（手术、化疗、放疗等）
- 出院医嘱、随访建议
- 出院带药

### 入院小结

需提取的关键信息：
- 入院日期
- 主诉（chief complaint）
- 入院诊断
- 现病史（起病经过、症状演变）
- 初步治疗方案（入院后拟定）

### 影像报告（CT / MRI / PET-CT / 超声 / X光DR）

需提取的关键信息：
- 检查日期、检查部位
- 主要影像学发现（病灶大小、位置、数量变化）
- 淋巴结状态
- 对比既往：是否有新发病灶、病灶增大/缩小
- 影像学印象/结论

### 检验报告（血常规 / 生化 / 肿瘤标志物）

需提取的关键信息：
- 检验日期
- 所有数值结果（含参考范围）
- 标注异常项（高于/低于参考范围）
- 对于肿瘤标志物：CEA、CA-199、AFP、CA-125 等具体数值

### 病理报告

需提取的关键信息：
- 取材部位、标本类型
- 组织学类型（腺癌、鳞癌等）
- 分化程度
- 分期（TNM 分期如有）
- 切缘状态
- 脉管/神经侵犯

### 基因检测 / 免疫组化

需提取的关键信息：
- 检测平台/方法
- 基因突变列表及突变频率
- MSI 状态、TMB 数值
- PD-L1 TPS/CPS 评分
- HER2 状态
- 药物敏感性提示

### 诊断证明

需提取的关键信息：
- 医院名称
- 就诊/住院日期（入院、出院）
- 临床诊断
- 治疗概况
- 医生建议/注意事项
