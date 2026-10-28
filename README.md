# TRACING THE SMOKE
## Machine Learning Analysis of Punjab–Haryana Agricultural Fire Activity and Delhi's PM2.5 Pollution Episodes

**Applied Machine Learning (AUCML End-Semester Examination Project)**  
**Workspace:** `E:\AUCML_PROJECT`  
**Technology Stack:** React, TypeScript, Vite, Tailwind CSS, FastAPI, Python, Scikit-Learn, XGBoost, SHAP, Leaflet, ECharts

---

## 1. PROJECT OVERVIEW

This research system examines whether satellite-observed agricultural fire activity in Punjab and Haryana and wind-aware atmospheric transport features provide additional predictive information about Delhi's daily PM2.5 pollution beyond historical pollution persistence and baseline weather features.

### Key Scientific Findings (Held-Out 2024 Test Evaluation, N = 366 Days):
- **Experiment A (Baseline Environmental Model):** $R^2 = 0.8192$, MAE = 18.92 µg/m³, Severe F1 = 0.5789.
- **Experiment B (+ Basic Regional Fires):** $R^2 = 0.8355$ (+0.0163 gain), MAE = 18.20 µg/m³, Severe F1 = 0.6316.
- **Experiment C (+ Wind-Aware Transport Features):** **$R^2 = 0.8472$** (+0.0280 vs Baseline), **MAE = 17.86 µg/m³**, **Severe F1 = 0.6667** (Precision = 61.54%, Recall = 72.73%).
- **Persistence Baseline:** $R^2 = 0.6865$, MAE = 23.36 µg/m³, Severe F1 = 0.5405.
- **SHAP Reliance Breakdown:** Historical Pollution (57.17%), Meteorology (25.31%), Fire Transport (9.93% full year, surging to 34.8% during harvest peaks), Seasonality (7.59%).

---

## 2. REPRODUCIBILITY & EXECUTION COMMANDS

All commands have been verified on Windows PowerShell in `E:\AUCML_PROJECT`.

### Step 1: Environment & Dependency Setup
```powershell
# Python Backend Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# React Frontend Dependencies
cd frontend
npm install
cd ..
```

### Step 2: Running Automated Verification Tests
```powershell
# Execute backend test suite (39 tests)
.\.venv\Scripts\pytest tests/ -v
```

### Step 3: Starting the Application
```powershell
# Terminal 1: Launch FastAPI Backend (Port 8000)
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Launch Vite React Frontend (Port 5173)
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser at: `http://localhost:5173`

### Step 4: Building Frontend Production Bundle
```powershell
cd frontend
npm run build
cd ..
```

---

## 3. PROJECT ARCHITECTURE & EIGHT-PAGE DASHBOARD

1. **Environmental Overview:** Historical Multi-Source Environmental Intelligence, KPI cards, date selector, 40 eligible CAAQM stations in Delhi NCT.
2. **Fire Transport Map:** Leaflet map centered on Punjab-Haryana-Delhi corridor, B1/B2 dataset selector, date filter, upwind alignment, distance rings.
3. **Pollution Analysis:** Dual-axis PM2.5 vs FRP chart, dynamic Pearson correlation $r$, lag selector, post-monsoon harvest toggle.
4. **Model Laboratory:** Controlled Exp A/B/C ablation benchmarking, actual vs predicted time series, evaluation sample count (N = 366).
5. **Attribution & SHAP:** 4-domain donut chart, global feature ranking, local day inspection with exact mathematical TreeSHAP additive reconstruction.
6. **Severe Episode & Forecast Explorer:** Mode A (Historical Same-Day Analysis) vs Mode B (Next-Day Forecast Replay with explicit forecast origin date).
7. **Data & Methodology:** Comprehensive documentation of CPCB station network, NASA FIRMS VIIRS, ECMWF ERA5, BLH gap handling, and chronological split.
8. **Research Insights & SDGs:** Verified scientific answers to RQ1–RQ5, alignment with UN Sustainable Development Goals 3, 11, and 13.

---

## 4. ACADEMIC DELIVERABLES MANIFEST

- `reports/Tracing_the_Smoke_Final_Report.docx` — Comprehensive final academic report.
- `presentation/Tracing_the_Smoke_Final_Presentation.pptx` — 12-slide professional presentation deck.
- `presentation/FINAL_VIVA_PREPARATION.md` — Complete viva interview preparation guide.
- `audit/final/FINAL_WEBSITE_AND_PROJECT_CORRECTIONS/` — Complete verification evidence package.
- `audit/final/FINAL_WEBSITE_AND_PROJECT_VERIFICATION.zip` — Standalone verification zip archive.
