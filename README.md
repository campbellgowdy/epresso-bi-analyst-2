# E-Presso · Coffee & clarity

A business intelligence application for the fictional E-Presso coffee business. Managers can explore recorded revenue across time, channels, stores, categories, and products; inspect data quality; replace source tables; and ask a constrained analytical assistant for calculations. Cream, blush pink, and chocolate brown preserve the existing café design.

## Live application

https://appapppy-uviy4xjvdz9vuzrndmo6fc.streamlit.app/

**This URL belongs to the existing deployment. The revised files must be committed to its connected GitHub branch before it runs this version. Local tests are not evidence of a completed redeployment.**

Repository: https://github.com/campbellgowdy/epresso-bi-analyst-2

## Run and deploy

Install Python 3.11 or newer and system package `mdbtools`. On Ubuntu: `sudo apt-get install mdbtools`.

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Streamlit Community Cloud reads `packages.txt` to install mdbtools and `requirements.txt` for Python dependencies. Entry point: `streamlit_app.py`. All original data stays in `data/`; the tiny `.accdb` at repository root is not the source database.

To deploy this revision, replace the changed/new files in the existing repository, retaining `data/`, then commit to the branch selected in Streamlit Cloud (normally `main`). No API key is needed for the default rules-based assistant. Open the live app and verify the baseline total before submission.

## Use the application

1. Open Dashboard. The supplied repository data loads automatically. There is no need to choose the Sales table.
2. Choose any combination of year, channel, store ID, category, and product in the sidebar. Empty selections mean all. Every chart and KPI uses the same explicit scope.
3. Open Analytical assistant. Ask a supported question and expand its tool-call log. Every answer begins with its scope. An explicitly named year, store ID, recognized city, channel, category, or product can override its corresponding sidebar filter. Use store IDs when asking about a particular store; cities may identify multiple stores.
4. Use Update data to upload a CSV/TSV table, Excel workbook with named source-table sheets, or Access database with Sales, Products, and Categories tables. A recognized uploaded table replaces that table; other supporting tables stay available. Multiple uploads apply in listed order, with the last copy of a table winning. Remove uploads to restore originals.
5. Validation lab exports current-scope reconciliation values and generates a Sales CSV with one row increased by exactly $1,000. Upload that copy to test the actual update path. It is deliberately not loaded by default.

Example questions: `What is total revenue?`, `Revenue by channel`, `Monthly revenue`, `Revenue by category`, `Revenue for SH11 in 2026`, `Which stores declined between 2028 and 2029?`, `Are there missing values?`

## Data model and grain

| Table | Source | Grain | Key | Original rows |
|---|---|---|---|---:|
| Sales | data/Support_EX_B_Sales (1).accdb | One monthly store/product/category revenue record in the supplied data | Sales ID | 25,200 |
| Products | same Access file | One catalog product | Product ID | 20 |
| Categories | same Access file | One catalog category | Category ID | 5 |
| Stores | data/Support_EX_B_Stores (3).csv | One location or website sales channel | ID | 21 |
| Survey | Survey Results sheet of data/Support_EX_B_Survey (2).xlsx | One store-year survey result | Survey ID | 105 |

The survey workbook contains documentation and question-definition sheets as well as the actual results. The loader locates the real header by column names, rather than treating the first documentation sheet as the survey. Satisfaction uses a 0–5 scale and Interest a 0–100 scale. Survey results are profiled separately and are not joined to Sales; a store-year survey is a different grain from monthly product revenue. No survey/cause inference is made.

Sales has three audited left many-to-one joins: Product ID → Products.Product ID; Category ID → Categories.Category ID; Store ID → Stores.ID. Every merge must preserve rows and revenue. Duplicate or missing required keys stop analysis with a readable message. Unmatched foreign keys retain sales and are reported. Unrecognized dimension labels become Unknown so revenue remains visible. The original three merges retain 25,200 rows and $42,174,440 each, with no unmatched foreign-key rows. See evidence/merge_checks.json.

`StoreYear` is retained as source metadata, not used as a revenue measure. Year and month are derived from Date. StoreType defines Channel. Missing geography on SH00 is expected because it represents Website.

## Definitions and data quality

Revenue = sum of the numeric source Revenue column, with no hardcoded totals. Revenue is not profit. Sales records count rows; average revenue per record divides by records with valid revenue. These records are monthly product totals, so neither count nor average is labeled transactions or average customer order value. Stores represented = distinct Store ID in scope.

Invalid/missing revenue is excluded and reported. Negative revenue is retained and flagged for review. Invalid/missing dates remain in total revenue but are excluded from dated charts, so time-chart sums can differ from total revenue; inspect quality reports. Dimensions with missing descriptions appear as Unknown. Required missing columns, keys, or unsafe joins produce plain errors. Data-quality profiles include every source table and sheet.

All filter values come from current data. Uploaded content bytes participate in the cache key. Access uploads are read from temporary files, not a static cached path. Uploads change a snapshot fingerprint; stale chat answers are cleared. Question count remains capped across data changes.

## Assistant and controls

Default is **Option B: rules-based analytical assistant**, eligible for up to 12/15 assistant points under the guide. It is not advertised as an unconstrained AI analyst. Four business tools take explicit parameters and return tool, value, definition, scope, rows_used, caveats, and error:

- revenue_summary: total revenue, valid record count, per-record average, stores represented.
- revenue_breakdown: revenue grouped by one allowed dimension or period.
- compare_years: store revenue change between two existing years, retaining missing-period status instead of assuming zero.
- quality: missing/invalid values, duplicate IDs, negative revenue counts.

A central dispatcher validates function names and arguments, invokes Python functions, and logs the complete result. Unknown filter values return an error, not a fabricated zero. Answers contain Findings, Interpretation, and Next steps. Only deterministic tool results supply numerical findings. Unsupported profit, causation, forecasts, and prescriptive decisions are declined. Fifteen questions per session, visible raw logs, snapshot labels, and downloads support review.

### Optional live model selection

The app can use OpenAI Chat Completions function calling to select one approved tool and enumerated parameters. Configure these in **Streamlit Cloud Secrets**, never in the repository:

```toml
OPENAI_API_KEY = "your-key-entered-only-in-Streamlit-Secrets"
OPENAI_MODEL = "gpt-4.1-mini"
```

Only questions, active filter labels, and fictional dataset dimension values are sent; source sales rows are not sent. The model selects a tool; deterministic Python executes it and formats the findings. Unsupported-judgment guards apply before API calls. Provider errors fall back to rules mode with an explicit notice. This is a live model-assisted router with deterministic explanations; do not claim a fully model-written narrative. **No live paid API call was performed during this revision**. Failure handling is tested with a simulated service failure. Validate your actual model/key configuration before claiming Option A implementation or points.

Official API reference: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

## Validation and tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python validate_project.py
```

Tests cover hand-calculable arithmetic, scoped queries, join fan-out rejection, unknown parameters, overlapping missing values, comparisons with no decline/missing periods, unsupported profit/causation questions, API-failure fallback, and the Streamlit app's fresh load, filter change, chat, quota, upload-byte cache invalidation and restoration in one session. AppTest simulates a file upload by substituting the uploader result; it does not prove the external hosted browser upload works.

Evidence files include:

- Independent calculation: raw Access export → standard-library CSV parser → Decimal sum, separate from pandas/application summation.
- Power BI comparison CSV: current app results for total, channel, year, month and sales records. **Power BI results remain explicitly pending; none are invented.**
- $1,000 prediction recorded before source round-trip, expected/actual scopes, assistant before/after, and restored originals.
- Five assistant test outputs with raw logs, plus documented defects/fixes and retests.
- A team-review reflection draft, contribution worksheet and defense notes.

Baseline source total is $42,174,440.00. This number is validation evidence, not an application constant. The selected update test increases S0020250101 from $6,780 to $7,780, so the predicted total is $42,175,440.00.

## Submission work only the team can complete

Read evidence/START_HERE.md. Confirm the live revision, actual Power BI results, screenshots of deployed numerical tool logs, contributions, and reflection. Each teammate must make a real commit under their own account. This revision does not fabricate contributions, commit identities, Power BI outputs, screenshots, or a successful hosted deployment.

## Code map

streamlit_app.py: presentation, source selection, filters, chat session and validation controls. data_model.py: source loading/schema validation/audited joins. analytics.py: reusable profiling and generic test helpers. business_tools.py: business calculations and fixed tool contract. agent.py: approved registry, dispatcher, rules/model routing and findings. validate_project.py: reproducible evidence generator. tests/: hand-checkable and application integration tests.

## Limits

Revenue alone cannot establish profitability, causation, customer purchase count, or whether to close a store. No cost data or causal design is supplied. A keyword router has a finite vocabulary; use supported examples or the filters rather than assuming arbitrary language is understood. The hosted app and the optional paid model service need their own final live checks. Keep the public fictional-data app deployed until grades are posted. Never upload real customer, payment, employee or confidential business records to this course app.
