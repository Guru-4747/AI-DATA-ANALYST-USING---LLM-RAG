#  PrismForge AI : LLM Powered Data Analyst

**Conversational analytics & business intelligence studio.** Upload your data, ask questions in plain English, and get answers backed by inspectable, read-only SQL, interactive charts, and downloadable reports.

> *Your data. Clearer decisions.*

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![SQLite](https://img.shields.io/badge/Engine-SQLite-003B57)
![Plotly](https://img.shields.io/badge/Charts-Plotly-3F4F75)
![License](https://img.shields.io/badge/License-MIT-green)

<!-- Add screenshots here after you take them, e.g.:
![Dashboard](docs/dashboard.png)
![Ask your data](docs/ask-your-data.png)
-->

---

## Table of contents

1. [Overview](#overview)
2. [Key features](#key-features)
3. [How it works](#how-it-works)
4. [Supported file formats](#supported-file-formats)
5. [Tech stack](#tech-stack)
6. [Project structure](#project-structure)
7. [Getting started](#getting-started)
8. [Configuration](#configuration)
9. [Usage guide](#usage-guide)
10. [Security and privacy](#security-and-privacy)
11. [Limits](#limits)
12. [Chart types](#chart-types)
13. [Known limitations](#known-limitations)
14. [Roadmap](#roadmap)
15. [Contributing](#contributing)
16. [License](#license)
17. [Author](#author)

---

## Overview

PrismForge AI is a local Streamlit application that lets non-technical users analyze their own data by asking questions in natural language. Instead of returning an unverifiable answer, it follows an **evidence-first** workflow:

**Question → structured query plan → read-only SQL → execution → evidence-based summary**

Every answer shows the SQL that produced it, the assumptions the model made, and the returned rows, so business-critical conclusions can always be verified.

The app runs without any API key in an **Offline demo** mode (fixed templates), and switches to full natural-language analysis in **AI analyst** mode using either **Google Gemini** or **OpenAI**.

---

## Key features

### ✦ Ask your data (AI analyst)
- Natural-language questions converted into a single SQLite `SELECT` / `WITH ... SELECT` query.
- Structured output through a Pydantic `Plan` schema (SQL, explanation, clarification, suggested chart, x/y columns).
- **Bounded self-correction:** if a query fails, the model gets exactly one retry with the error message, without relaxing any restrictions.
- **Clarification instead of guessing:** if a measure, relationship, or date can't be established from the schema, the model asks rather than inventing fields.
- Follow-up questions use the previous four questions and their SQL as context.
- Evidence-only summaries: direct answer, 2–4 evidence bullets, a suggested next question, and explicit notes about truncation and assumptions.
- Responds in the language the user writes in.
- Document search over PDFs, Word files and text files, with source and page citations.

### ◈ Business dashboard
- KPI cards (visible records, total, average, missing cells).
- Performance-over-time, segment contribution, segment comparison, distribution, and target gauge charts.
- Dashboard-level filters by dimension and date range.
- One-click standalone HTML dashboard export.

### ▦ Data explorer
- Table preview, per-column data-quality profile (type, missing, unique) and duplicate-row count.
- Column type conversion (numeric, ISO date, text) with currency-symbol and comma cleanup.
- Schema view showing exactly what the analyst sees.
- Safe CSV download.

### ◉ Chart studio
- 21 chart types with dimension, measure, colour split and aggregation controls.
- Add any chart directly to the report.

### ⌘ SQL workbench
- Run your own read-only SQL against all loaded tables, protected by the same authorizer as the AI queries.

### ↗ Business report
- Collect AI analyses and charts into one **self-contained, interactive HTML report** (Plotly charts embedded, SQL evidence included, tables escaped).

### 🧪 Offline demo mode
- Works without an API key. Supports `count rows`, `preview data`, and `revenue by region`.
- Ships with a synthetic 900-row retail dataset so the app is usable immediately.

---

## How it works

```
┌────────────┐   ┌──────────────┐   ┌────────────────┐   ┌───────────────────┐
│ Upload     │──▶│ Normalise    │──▶│ In-memory      │──▶│ Schema (+optional │
│ files      │   │ into tables  │   │ SQLite         │   │ 2 sample rows)    │
└────────────┘   └──────────────┘   └────────────────┘   └─────────┬─────────┘
                                                                    ▼
┌────────────┐   ┌──────────────┐   ┌────────────────┐   ┌───────────────────┐
│ Answer +   │◀──│ Evidence-only│◀──│ Execute SQL    │◀──│ LLM returns Plan  │
│ chart      │   │ summary      │   │ (authorizer)   │   │ (structured JSON) │
└────────────┘   └──────────────┘   └───────┬────────┘   └───────────────────┘
                                            │ on error: one correction attempt
                                            └───────────────▶ back to the LLM
```

1. **Ingestion (`data.py`)** – Files are parsed locally into pandas DataFrames. Column names are normalised into safe SQL identifiers and duplicates are made unique. Nested values (dicts/lists) are JSON-serialised, and bytes are hex-encoded.
2. **Execution (`sql.py`)** – Tables are loaded into a fresh in-memory SQLite database for each query, with a deny-by-default authorizer, `PRAGMA query_only=ON`, a function allow-list, length limits and a 4-second time limit.
3. **Planning (`agent.py`)** – The schema and question go to the selected LLM, which returns a validated `Plan`. Results are then summarised from the evidence only.
4. **Visualisation (`charts.py`)** – A single chart factory powers the dashboard, query results and report export.
5. **Reporting (`report.py`)** – Sections are assembled into a standalone HTML file with escaped content.

---

## Supported file formats

| Category | Extensions |
|---|---|
| Delimited text | `csv`, `tsv` (delimiter auto-detected for CSV) |
| Spreadsheets | `xlsx`, `xls`, `ods` (each sheet becomes a table) |
| JSON | `json`, `jsonl`, `ndjson` |
| Columnar | `parquet`, `feather` |
| Databases | `sqlite`, `sqlite3`, `db` (physical tables only; views and triggers are never executed) |
| Documents | `pdf` (text-based), `docx` (paragraphs and tables), `txt`, `md` |
| Markup | `xml` (flat repeated records, parsed with `defusedxml`) |

**Notes**
- PDFs, Word paragraphs and text files are loaded as text chunks (`source`, `page`, `chunk`, `text`) in a `*_documents` table. They are meant for retrieval and citation, **not** for numeric aggregation. Use CSV/XLSX for exact figures.
- Scanned PDFs without a text layer need OCR first.
- Word table cells are text; convert numeric columns in the Data explorer before aggregating.
- Nested XML should be converted to JSON or CSV first.

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Data handling | pandas, pyarrow, openpyxl, xlrd, odfpy |
| SQL engine | SQLite (in-memory, Python `sqlite3`) |
| AI | OpenAI Python SDK (used for both OpenAI and Gemini via its OpenAI-compatible endpoint) |
| Schema validation | Pydantic |
| Charts | Plotly (Express and Graph Objects) |
| Document parsing | pypdf, python-docx, defusedxml |
| Config | python-dotenv |
| Testing | pytest |

---

## Project structure

```
prismforge-ai/
├── app.py                 # Streamlit UI: sidebar, 6 tabs, session state
├── prismforge/
│   ├── __init__.py
│   ├── agent.py           # LLM planning, one-shot SQL correction, summarisation, offline templates, error messages
│   ├── charts.py          # Plotly chart factory and dark theme
│   ├── data.py            # Multi-format ingestion, name sanitising, limits, demo dataset
│   ├── report.py          # Standalone HTML report exporter
│   └── sql.py             # Sandboxed read-only SQL execution, schema and data-quality helpers
├── requirements.txt
├── .env.example           # Template for local configuration (create this)
├── .gitignore             # Must include .env
└── README.md
```

> `app.py` imports from the `prismforge` package, so keep the modules inside a `prismforge/` folder next to `app.py`.

---

## Getting started

### Prerequisites
- Python 3.11 or newer (3.12+ recommended)
- `pip`
- An API key from [Google AI Studio](https://aistudio.google.com/) (Gemini) or [OpenAI](https://platform.openai.com/), only if you want AI mode

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/prismforge-ai.git
cd prismforge-ai

# 2. Create and activate a virtual environment
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure your API key
cp .env.example .env      # Windows: copy .env.example .env
# then edit .env

# 5. Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## Configuration

Create a `.env` file in the project root (same folder as `app.py`):

```env
# Gemini (default provider in the UI)
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=<a Gemini model available to your account>

# OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4.1-mini
```

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key used when the provider is Gemini |
| `GEMINI_MODEL` | Default Gemini model name shown in the sidebar |
| `OPENAI_API_KEY` | OpenAI key used when the provider is OpenAI |
| `OPENAI_MODEL` | Default OpenAI model name (falls back to `gpt-4.1-mini`) |

You can also paste a key into the sidebar for the current session only. It is not written to disk.

> ⚠️ **Never commit `.env`.** Add it to `.gitignore`:
> ```
> .env
> .venv/
> __pycache__/
> ```

---

## Usage guide

1. **Load data.** Use the sidebar uploader (up to 10 files) and click **Load uploaded files**, or start with the built-in synthetic retail dataset. **Reset to demo data** restores it.
2. **Choose a query engine.**
   - *Offline demo* – no key needed; limited templates.
   - *AI analyst* – pick Gemini or OpenAI, enter a model and key, and tick the consent checkbox.
3. **Ask a question** in **✦ Ask your data**, for example:
   - `Compare monthly revenue by region.`
   - `Which category has the highest profit margin?`
   - `Create an executive summary of revenue by channel.`
   - `Find passages in the contract that mention termination.` (for document tables)
4. **Inspect the evidence.** Open *Query plan and execution steps* to see assumptions, SQL and the execution trace. Adjust the suggested chart if needed.
5. **Clean data if necessary** in **▦ Data explorer** (e.g. convert a text column to numeric).
6. **Export.** Add analyses and charts to the report, then download the interactive HTML report. Use your browser's *Print → Save as PDF* for a static copy.

---

## Security and privacy

PrismForge treats both **generated SQL** and **uploaded content** as untrusted.

| Area | Protection |
|---|---|
| SQL execution | Deny-by-default SQLite authorizer; only `SELECT`/recursive CTEs, reads from loaded tables, and allow-listed functions are permitted |
| Write prevention | `PRAGMA query_only=ON`; no `PRAGMA`, `ATTACH`, or DDL/DML allowed for generated or manual SQL |
| Resource limits | 4-second execution deadline, 30,000-character SQL cap, 2 MB value-length cap, 2,000-row result cap |
| Uploaded SQLite files | Opened read-only with `trusted_schema=OFF`; only physical tables are copied, triggers and views are never executed |
| Uploaded archives | Expanded size of Office archives is checked (100 MB cap) |
| XML | Parsed with `defusedxml` |
| Prompt injection | System prompts instruct the model that schema labels, cell values and past results are data, never instructions |
| CSV export | Cells beginning with `=`, `+`, `-`, `@`, tab or carriage return are prefixed to prevent spreadsheet formula injection |
| HTML reports | All titles, text, SQL and table cells are HTML-escaped |
| Secrets | No key is bundled; keys come from `.env` or a password-type session field; error messages never echo raw provider responses |
| Consent | AI mode is blocked until the user ticks the checkbox allowing the question, schema and result excerpts to be sent to the provider; sample rows are a separate opt-in |
| OpenAI retention | Requests are sent with `store=False` |

**What is sent to the AI provider:** your question, table schema (names, types, null counts), up to the last four questions with their SQL, and up to 40 result rows (fewer or truncated if the payload is large) for summarisation. Two sample rows per table are sent only if you opt in. Uploaded files stay in the local session. Provider quotas, billing and data policies apply.

**Important:** the authorizer and time limit reduce risk but are not a substitute for a hardened sandbox. Don't expose this app publicly with sensitive data without adding authentication and deployment-level isolation.

---

## Limits

| Limit | Value |
|---|---|
| File size | 20 MB per file |
| Files per upload | 10 files, 50 MB total |
| Tables per file / workspace | 30 |
| Rows per table | 100,000 |
| Rows across the workspace | 300,000 |
| Columns per table | 150 |
| PDF pages | 200 |
| Query result rows | 2,000 (use SQL aggregation for full-dataset totals) |
| Chart Studio source | First 5,000 rows of the selected table |
| AI request context | ~70,000 characters (reduce tables or disable samples if exceeded) |
| SQL timeout | 4 seconds |
| AI request timeout | 45 s (OpenAI), 120 s (Gemini), 1 retry |

---

## Chart types

`Auto` · `Bar` · `Horizontal bar` · `Stacked bar` · `Line` · `Area` · `Scatter` · `Bubble` · `Pie` · `Donut` · `Histogram` · `Box` · `Violin` · `Heatmap` (correlation) · `Treemap` · `Sunburst` · `Funnel` · `Waterfall` · `Gauge` · `Map` (country choropleth) · `Table`

`Auto` picks a line chart for date-like dimensions, a bar chart otherwise, and a KPI indicator for single-row results.

---

## Known limitations

- Currency and units are **never inferred**; numeric cells should not contain currency symbols (use the type converter).
- PDF/Word/text content is retrieval-oriented, not suitable for exact numeric analysis.
- Dashboard filters affect only the dashboard; AI and SQL always query all loaded rows, so include filters in the question.
- The AI summary is based on at most 40 returned rows. For whole-dataset conclusions, rely on aggregated SQL results.
- Correlation heatmaps indicate association, not causation.
- The workspace lives in Streamlit session state: refreshing or restarting the app clears data, history and the report.
- The offline mode supports only three fixed question templates.
- Gemini access uses the OpenAI-compatible endpoint; model availability depends on your account.

---

## Roadmap

- [ ] OCR support for scanned PDFs
- [ ] Persistent workspaces and saved reports
- [ ] Direct database connectors (PostgreSQL, MySQL) in read-only mode
- [ ] Native PDF export for reports
- [ ] Multi-user authentication
- [ ] Automated test suite and CI (pytest + GitHub Actions)
- [ ] Docker image for one-command deployment

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please keep the security model intact: don't loosen the SQL authorizer, escaping, or consent flow without discussion.

---

## License

Distributed under the MIT License. Add a `LICENSE` file to the repository root (GitHub can generate one via **Add file → Create new file → LICENSE**).

---

## Author

**Gururaghav K K**
B.Tech in Artificial Intelligence & Machine Learning, M S Ramaiah University of Applied Sciences, Bangalore

- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: *add your profile link*

If you find this project useful, consider giving it a ⭐.
