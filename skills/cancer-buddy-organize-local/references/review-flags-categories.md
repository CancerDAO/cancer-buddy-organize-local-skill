# Review Flags — 6 类可疑值审计 (cancer-buddy-organize-local)

> Layer 3 (Claude text 综合) 在写完 profile.json 之后，对每个抽取字段跑这 6 项审计。
> `blocking_gaps` 覆盖**缺失**；`review_flags` 覆盖**已抽取但可疑**。两者并行，缺一不可。
> 即使一项都没触发，也必须写 `"review_flags": []` —— 缺这个字段视为 organizer 不合规。

## 6 类审计

| # | category | 触发逻辑 | severity 默认 |
|---|---|---|---|
| 1 | `format_violation` | 字段值违反已知标准格式 | red |
| 2 | `cross_doc_contradiction` | 同一概念在 2+ 源文档中冲突 | red |
| 3 | `clinical_logic_anomaly` | 术语用错语境 / 逻辑不自洽 | red 或 yellow |
| 4 | `unverified_critical_field` | 下游 eligibility 关键字段仅来自 progress note，无原件 | red |
| 5 | `value_trend_anomaly` | 数值时序变化非生理性，源文档无解释 | yellow |
| 6 | `patient_curated_vs_formal` | 14_患者自管补充/ 内容与正式文档冲突 | yellow |

## Severity 校准

每条 flag 必须落到 🔴 / 🟡 / 🟢 之一：

- 🔴 **red** — 改变下游推荐 (eligibility / line counting / dosing)
  - 例：分期前缀错误 (复发 vs 初诊)、未验证驱动突变 (trial-match 基础)、化疗线编号歧义
- 🟡 **yellow** — 应核对，但不卡下游
  - 例：周期数双计、术语误用无后果、数值趋势可疑
- 🟢 **green** — 提示性
  - 例：M1a/b/c 子字母未指定、ECOG 由 KPS 推断、可选精度缺失

## 完整 5 类详细规则

### 1. `format_violation`

字段必须符合的标准：

| 字段 | 标准 | trip 例 |
|---|---|---|
| `stage` (TNM) | AJCC 8th 前缀 ∈ {c, p, yp, r, a} | `rpT4aN2aM1` ("rp" 不在白名单) |
| `stage` (FIGO 妇瘤) | FIGO 2018，可加后缀 r (imaging) / p (pathologic) | `IIIC2x` (无 x 后缀) |
| `treatment_response` | RECIST 1.1 ∈ {CR, PR, SD, PD, NE} | `MR` (RECIST 无 MR), `PR-like` (非标准) |
| `ecog` | 0-4 整数 | 1.5, "G2" (混淆 CTCAE) |
| `kps` | 0-100，10 的倍数 | 75, 33 |
| `irAE_grade` | CTCAE v5: 1-5 整数 | "中度" (非数值) |
| `histology` | WHO 5th 命名 | "腺鳞癌" (应为 "腺鳞上皮癌") |
| 药品名 | NMPA / FDA 已批准的通用名 / 商品名 | "PD1 抗体" (非具体药) |
| 日期 | YYYY-MM-DD | "2026.1.5" (但 OCR 原文允许保留) |

### 2. `cross_doc_contradiction`

**触发条件**：同一概念在 2+ 文档中值不一致 + 患者无明显病情转变可解释。

例：
- 1/12 门诊病历写 IB2 期，1/9 PET/CT 已显示腹膜后 LN+，1/19 出院诊断改为 IIIC2r
- 文档 A 写"已完成 2 周期化疗"，文档 B 写"第 3 周期化疗第 1 天"，时间相隔 < 3 天

**必填字段**：
- `current_value` = 你最终采纳的值
- `source_evidence[]` = 所有冲突文档路径
- `suggested_value` = 优先以最权威的为准 (出院诊断 > 门诊病历, 报告 > 转录, 最新 > 早期)
- `rationale_for_suggestion` = 为什么按这个权重选

### 3. `clinical_logic_anomaly`

医学语义层面不自洽：

| 不自洽模式 | 例 |
|---|---|
| 辅助治疗 + RECIST 评估 | "辅助化疗 ... PR" (辅助 = 无可测病灶) |
| 新辅助 + 上来就手术 | "新辅助化疗" 但 timeline 显示 D0 上来就切 |
| ECOG 0 + KPS 50 | 两个评分严重不一致 |
| 完全缓解 + 肿标升高 | "CR" 同期 SCC 由 1 → 8 |
| 复发 + 前缀 c | 复发病灶应用 r 前缀，写 c 不对 |

### 4. `unverified_critical_field`

**关键字段**（影响下游 eligibility）：
- 驱动突变（EGFR/ALK/ROS1/KRAS/BRAF/Her2/MET 等）
- TMB / MSI / dMMR
- PD-L1 (CPS / TPS)
- HRD
- 病理类型（鳞 / 腺 / 神经内分泌）
- 分期 + 转移部位
- 现行治疗的 line of therapy 编号

**触发条件**：上述任何字段被写进 profile.json 的依据**只来自**：
- 入院记录 / 门诊病历的"既往史"叙述段
- 出院诊断的"诊断"列表
- 患者口述

**而无**原始 NGS 报告 PDF / 病理报告 PDF / IHC 染色单原件。

**必做**：标 🔴 + suggested_action: "调取原报告"。

### 5. `value_trend_anomaly`

数值时序非生理性变化，源文档**无解释**。

| 模式 | 例 | 严重性 |
|---|---|---|
| 短时大幅波动 | TSH 6.49 → 6.16 → 0.80 µIU/mL within 8 weeks，无甲状腺干预 | yellow |
| 单次跨数量级跳跃 | CEA 1.2 → 65.4 → 0.9 三次连续测量 | yellow |
| 治疗后反向 | 化疗后 SCC 反弹 > 20%，但影像未提示 PD | yellow |
| 实验室同日不一致 | HGB 90 (上午) vs HGB 130 (下午) | red (录入错误嫌疑) |

**典型**：irAE 甲状腺炎破坏期 TSH 暴跌是合理的 → **不触发**（因为有 irAE 解释）；但**临床决策记录缺失**（无医嘱调整）应**另触发** category 3 (clinical_logic_anomaly)。

### 6. `patient_curated_vs_formal`

**触发条件**：14_患者自管补充/ 下的内容（manual timeline / 微信 / 语音转录）与 01–13 正式文档冲突。

| 冲突类型 | 例 | severity |
|---|---|---|
| 患者写有事件，正式文档无 | manual: 2026-02-26 第 3 次免疫；目录无对应医嘱单 | yellow (材料缺失) |
| 患者写日期 vs 正式文档日期 | manual: 1/14 第 1 次化疗; 出院记录写 D1 (q3w 反推 = 1/14, 一致) | green (确认) |
| 患者把后续诊断回填到早期记录 | manual: "1/7 出院诊断 = 鳞癌"，但 1/7 出院记录原文写"病检未归" | red (错误回填) |
| 患者口述 vs 正式分期 | 患者: "我是 IB 期"，出院诊断: IIIC2r | red (患者认知偏差) |

**默认采信**：正式文档 > 患者补充。把患者补充的差异挂到 review_flags，让用户决定。

## review_flags[] 的完整 schema

```json
{
  "id": "RF-001",
  "severity": "red",                            // red | yellow | green
  "category": "format_violation",               // 6 类之一
  "field_path": "stage",                        // profile.json 字段路径
  "current_value": "rpT4aN2aM1 IV期",
  "issue": "AJCC 8th 前缀只有 c/p/yp/r/a, 'rp' 不在其中",
  "source_evidence": [                          // 必填; 至少 1 条
    "04_诊断与分期/诊断证明/出院诊断证明_2024-07-05.jpg"
  ],
  "suggested_value": "pT4aN2aM1 IV期",
  "suggested_action": "改写为 p 前缀; 在 data_sources 注明医院原写法",
  "rationale_for_suggestion": "首诊→手术≤30 天 + 术后才启动'辅助'化疗 → 切除标本应 treatment-naive",
  "user_confirmed": false,                      // 等待用户确认; 用户 review 后改为 true
  "resolution": null                            // 用户 review 后写: "accept_suggestion" | "keep_original" | "custom_value:<v>" | "defer"
}
```

## review_flags.md 渲染（人类可读）

`review_flags` 数组非空时，自动写入 `<patient_dir>/review_flags.md`：

```markdown
# 🔍 待人工确认 — <patient_code>

> 已成功提取并写入 profile.json 的字段, 但其值或写法可疑 / 不规范 / 互相矛盾。
> Source of truth: readiness.json.review_flags[]. 本文件由 organize 自动重新生成。

总数: <N> 项 (🔴 <R> / 🟡 <Y> / 🟢 <G>)

---

## 🔴 高优先级 (影响下游推荐)

### RF-001: <一句话标题>
- **现写**: `field_path: current_value`
- **可疑点**: <issue>
- **源证据**:
  - <source_evidence 1>
  - <source_evidence 2>
- **建议**: <suggested_value> + <suggested_action>
- **理由**: <rationale_for_suggestion>
- **确认**: ⬜ 接受建议 / ⬜ 保留原写 / ⬜ 自定义值: ___ / ⬜ 暂缓

## 🟡 中优先级 (建议核对)
...

## 🟢 低优先级 (提示)
...
```

## SKILL.md 集成检查清单

Layer 3 完成 review_flags 审计后必须：

1. ✅ 写 `readiness.json.review_flags[]`（即使是空数组）
2. ✅ 若数组非空，写 `<patient_dir>/review_flags.md`
3. ✅ 若有 🔴，在最终输出告诉用户："进入下游 skill 之前请先逐条确认或 override 这些 🔴 项"
4. ✅ 若数组为空，告诉用户："所有提取字段已通过 6 项可疑值检查 (格式/跨文档矛盾/临床逻辑/原始证据/数值趋势/患者补充冲突), 无待确认项"
