# Curated text fast path

Use this mode for a short text submission that the health-vault owner has already reviewed and explicitly approved. It is an incremental `patient_curated` write, not a medical-record ingestion job.

## Inputs

- `mode: curated_text`
- `patient_code`: an existing patient directory
- `curated_text`: non-empty UTF-8 text, at most 20,000 characters
- `source_label`: optional source such as `爸爸体温血压日记`
- `submitted_at`: ISO-8601 timestamp

Reject the request if the patient directory does not already exist. Never silently fall back to `full` or `merge_only`.

## Required fast path

1. Run local PII detection/redaction on `curated_text`. Raw text must not be sent to a cloud model. Keep the owner-approved original only in the local raw/audit surface excluded from downstream model context.
2. Make at most one text-only semantic call using the PII-masked text. Extract only supported patient-curated observations: date/time, vital signs, symptoms, medication adherence, activity, and free-form diary context.
3. Append the masked source note under the existing locale-aware patient-supplement diary bucket. Tag it `patient_curated`, `confidence: low`, and `owner_reviewed: true`.
4. Append structured time-series observations only when values and units are explicit. Do not infer missing units, dates, diagnoses, causes, or treatment changes. Never overwrite record-sourced facts.
5. Append an `update_log.json` entry with `run_mode: curated_text`, source label, timestamp, and changed paths.

Do **not** run PaddleOCR, rasterization, document classification, Phase 1, full Layer 3 synthesis, readiness regeneration, case-summary generation, or whole-vault reconciliation.

## Failure and retry rules

- Authentication errors (`invalid refresh_token`, HTTP 401/403, login required) are permanent for this run: fail immediately and do not retry.
- Rate limits may return a retryable error to the caller, but this mode must not sleep or retry internally.
- Validation or parse failure writes nothing. Return the original submission to the caller as pending.

## Result

```json
{
  "role": "organizer-local",
  "mode": "curated_text",
  "ok": true,
  "patient_curated_merged": true,
  "observations_written": 1,
  "changed_paths": ["14_patient_supplement/diary/2026-07-11.md", "longitudinal_observations.json", "update_log.json"]
}
```

The target bucket is locale-aware; paths above are examples, not hard-coded names.
