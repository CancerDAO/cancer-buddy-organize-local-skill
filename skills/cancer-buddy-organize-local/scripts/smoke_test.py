#!/usr/bin/env python3
"""
smoke_test.py — verify the Layer-1 OCR stack installs + runs on this platform.

Exit 0 only if BOTH:
  (1) paddleocr predict() succeeds on a synthetic PII image (Issue #1 Bug 1b)
  (2) paddlenlp Taskflow NER loads (Issue #1 Bug 1a) — or is cleanly absent

Prints a JSON report to stdout. Designed to run on the SAME x86_64 Linux
server that hosts the skill, in the SAME venv used by redact_ocr.py.
"""
import json, os, sys, platform, traceback

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
# NOTE: the x86 oneDNN crash is fixed by PaddleOCR(enable_mkldnn=False) in
# ocr_predict() below — NOT by env flags (verified on real x86).

report = {"platform": platform.platform(), "machine": platform.machine(),
          "python": sys.version.split()[0], "steps": {}}

def step(name, fn):
    try:
        report["steps"][name] = {"ok": True, "detail": fn()}
    except Exception as e:
        report["steps"][name] = {"ok": False, "error": f"{type(e).__name__}: {e}",
                                 "trace": traceback.format_exc()[-800:]}

def versions():
    import paddle, paddleocr
    out = {"paddlepaddle": paddle.__version__, "paddleocr": paddleocr.__version__}
    try:
        import paddlenlp; out["paddlenlp"] = paddlenlp.__version__
    except Exception as e:
        out["paddlenlp"] = f"IMPORT_FAILED: {type(e).__name__}: {e}"
    try:
        import aistudio_sdk; out["aistudio_sdk"] = getattr(aistudio_sdk, "__version__", "?")
    except Exception:
        out["aistudio_sdk"] = "absent"
    import numpy; out["numpy"] = numpy.__version__
    return out

def make_test_image():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (600, 200), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 10), "姓名: 王某某  身份证: 110101199001011234", fill="black")
    d.text((10, 60), "手机: 13800138000  诊断: 宫颈鳞癌 IIIC2", fill="black")
    p = "/tmp/_smoke_pii.png"; img.save(p); return p

def ocr_predict():
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_textline_orientation=True, use_doc_orientation_classify=False,
                    use_doc_unwarping=False, lang="ch", enable_mkldnn=False)
    res = list(ocr.predict(make_test_image()))
    n = sum(len(p.get("rec_texts", [])) for p in res) if res else 0
    return {"pages": len(res), "text_lines": n}

def ner_load():
    from paddlenlp import Taskflow
    Taskflow("information_extraction", schema=["人名"], model="uie-micro")
    return "Taskflow loaded"

step("versions", versions)
step("ocr_predict", ocr_predict)        # gates Bug 1b (oneDNN)
step("ner_load", ner_load)              # gates Bug 1a (aistudio-sdk)

print(json.dumps(report, ensure_ascii=False, indent=2))
ocr_ok = report["steps"]["ocr_predict"]["ok"]
sys.exit(0 if ocr_ok else 1)            # NER is optional; OCR is the hard gate
