"""Build and verify the final verification ZIP package for Tracing the Smoke.
Saves to E:/AUCML_PROJECT/audit/final/TRACING_THE_SMOKE_FINAL_VERIFICATION.zip.
"""

import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path("E:/AUCML_PROJECT")
AUDIT_FINAL = PROJECT_ROOT / "audit" / "final"
ZIP_OUT = AUDIT_FINAL / "TRACING_THE_SMOKE_FINAL_VERIFICATION.zip"

FILES_TO_PACK = [
    # Checkpoint & summary
    ("EXECUTION_CHECKPOINT.md", AUDIT_FINAL / "EXECUTION_CHECKPOINT.md"),
    ("EXECUTION_CHECKPOINT.json", AUDIT_FINAL / "EXECUTION_CHECKPOINT.json"),
    ("DASHBOARD_INTEGRATION_VERIFICATION.md", AUDIT_FINAL / "DASHBOARD_INTEGRATION_VERIFICATION.md"),
    ("FINAL_DATA_QUALITY_SUMMARY.json", AUDIT_FINAL / "FINAL_DATA_QUALITY_SUMMARY.json"),
    ("FINAL_DAILY_DATA_QUALITY_TABLE.csv", AUDIT_FINAL / "FINAL_DAILY_DATA_QUALITY_TABLE.csv"),
    ("FEATURE_DICTIONARY.json", AUDIT_FINAL / "FEATURE_DICTIONARY.json"),
    ("FINAL_MODEL_EVALUATION_SUMMARY.json", AUDIT_FINAL / "FINAL_MODEL_EVALUATION_SUMMARY.json"),
    ("MODEL_COMPARISON_TABLE.csv", AUDIT_FINAL / "MODEL_COMPARISON_TABLE.csv"),
    ("PREDICTIONS_2024_TEST.csv", AUDIT_FINAL / "PREDICTIONS_2024_TEST.csv"),
    ("GLOBAL_SHAP_IMPORTANCE.csv", AUDIT_FINAL / "GLOBAL_SHAP_IMPORTANCE.csv"),
    
    # Reports
    ("reports/Tracing_the_Smoke_Academic_Report.docx", PROJECT_ROOT / "reports" / "Tracing_the_Smoke_Academic_Report.docx"),
    ("reports/academic_report.md", PROJECT_ROOT / "reports" / "academic_report.md"),
    
    # Presentations & Viva
    ("presentation/Tracing_the_Smoke_Presentation.pptx", PROJECT_ROOT / "presentation" / "Tracing_the_Smoke_Presentation.pptx"),
    ("presentation/presentation_slides.md", PROJECT_ROOT / "presentation" / "presentation_slides.md"),
    ("presentation/viva_preparation.md", PROJECT_ROOT / "presentation" / "viva_preparation.md"),
    
    # Test suite
    ("tests/test_end_to_end.py", PROJECT_ROOT / "tests" / "test_end_to_end.py"),
]

def build_package():
    print(f"Building final verification ZIP package at: {ZIP_OUT}")
    with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, file_path in FILES_TO_PACK:
            if not file_path.exists():
                raise FileNotFoundError(f"Missing required file: {file_path}")
            print(f"  Adding: {arcname} ({file_path.stat().st_size:,} bytes)")
            zf.write(file_path, arcname=arcname)
            
    print(f"\nVerification package built successfully. Total size: {ZIP_OUT.stat().st_size:,} bytes.")
    
    # Verify contents
    with zipfile.ZipFile(ZIP_OUT, "r") as zf:
        namelist = zf.namelist()
        print(f"Verified {len(namelist)} items in archive:")
        for name in namelist:
            info = zf.getinfo(name)
            print(f"  - {name}: {info.file_size:,} bytes (compressed: {info.compress_size:,} bytes)")

if __name__ == "__main__":
    build_package()
