"""Read-only runtime probe. Does not open the camera or send OS input."""
import hashlib
import importlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    packages = {"PySide6": "PySide6", "opencv-contrib-python": "cv2", "mediapipe": "mediapipe", "numpy": "numpy", "mss": "mss", "pytest": "pytest"}
    results = {}
    for name, module in packages.items():
        try:
            importlib.import_module(module)
            results[name] = {"version": importlib.metadata.version(name), "status": "PASS"}
        except Exception as error:
            results[name] = {"status": "FAIL", "error": str(error)}
    model = ROOT / "models/hand_landmarker.task"
    digest = hashlib.sha256(model.read_bytes()).hexdigest() if model.exists() else None
    expected = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"
    report = {"python": sys.version, "platform": platform.platform(), "architecture": platform.machine(), "packages": results,
              "model_sha256": digest, "model_verified": digest == expected, "camera": "NOT_OPENED", "os_input": "NOT_SENT"}
    report["status"] = "PASS" if digest == expected and all(v["status"] == "PASS" for v in results.values()) else "FAIL"
    (ROOT / "docs/validation/environment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
