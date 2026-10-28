# E-Presso BI Analyst (starter)

> Replace this README as you build. Your final version should cover every section below.

## What this application does
_One paragraph for a manager, not a programmer._

## Live app
_URL here. Note that the app may take a moment to wake up._

## How to use it
_Upload files, use filters, ask the assistant. Include the file names and sheets it expects._

## Data model
_Grain of each table, keys, and how they are joined. Include your merge checks._

## Metric definitions
_What "revenue" means here, and anything it does not mean._

## Assistant
_State exactly what you built (live language-model agent, or rules-based assistant). List each tool, what it calculates, and what the assistant is not allowed to do._

## Validation
_Link to or summarize your Power BI comparison, independent check, and $1,000 test._

## Limitations
_Revenue is not profit. What else can this app not tell a manager?_

## Files
| File | Purpose |
|---|---|
| `streamlit_app.py` | Screen layout and interaction |
| `analytics.py` | Metrics and analytical functions (no Streamlit code) |
| `agent.py` | Tool registry, dispatcher, and routers |
| `tests/` | Tests with hand-checkable answers |
| `requirements.txt` | Packages the hosted app needs |

## Run it
Hosted: deploy from this repository on share.streamlit.io with main file `streamlit_app.py`.


## Secrets
Never commit API keys. Use Streamlit Secrets (see `.streamlit/secrets.toml.example`).


## Grain Statements for E-Presso Data

### 1. Sales Table

**Grain:** Each row represents one sales record associated with a specific product, category, store, date, and store year.

**Key fields:** `Sales ID` identifies the sales record. `Store ID`, `Category ID`, and `Product ID` identify the related store, category, and product.

**Measures:** `Revenue` records the monetary value associated with each sales record.

**Data quality checks:** Verify that `Sales ID` is unique and check for missing values in key fields, dates, and revenue.

### 2. Products Table

**Grain:** Each row represents one product in the E-Presso product catalog.

**Key field:** `Product ID` identifies the product.

**Attributes:** `Product` contains the product name.

**Data quality checks:** Verify that `Product ID` is unique and check for missing product IDs or product names.

### 3. Categories Table

**Grain:** Each row represents one product category in the E-Presso product catalog.

**Key field:** `Category ID` identifies the category.

**Attributes:** `Category` contains the category name.

**Data quality checks:** Verify that `Category ID` is unique and check for missing category IDs or category names.

4. Stores Dataset

Grain: Each row represents one E-Presso store location.

Key field: ID identifies the store.

Attributes: The dataset includes City, State, Postal Code, Phone, Store Type, Market, Location, and Manager, which describe the store and its characteristics.

Data quality checks: Verify that each ID is unique and check for missing store IDs, locations, and other important fields.
### 5. Survey Dataset

**Purpose:** To track market survey results for E-Presso stores on an annual basis.

**Grain:** Each row represents a market survey record for E-Presso. The dataset includes `Market` and `Survey` fields. The exact level of detail represented by each row should be confirmed by inspecting the data.

**Data quality checks:** Investigate the unnamed column to determine what it contains, and check for missing values and duplicate records.

## Data Quality Profiles

### Sales Table

The Sales table contains 25,200 rows and 7 columns: Sales ID, Date, Store ID, StoreYear, Category ID, Product ID, and Revenue. The initial data-quality assessment identified 0 duplicate rows and 0 missing values across all seven columns. These results suggest that the table is complete with respect to missing values and contains no fully duplicated rows. Additional checks are needed to confirm that Sales ID is unique, dates and revenue values are valid, and joins to other datasets do not duplicate records.
### Products Table

The Products table contains 20 rows and 2 columns: Product ID and Product. The initial data-quality assessment identified 0 duplicate rows and 0 missing values across both columns. These results indicate that the table has no fully duplicated rows or missing values. An additional check is needed to confirm that Product ID is unique.
### Categories Table

The Categories table contains 5 rows and 2 columns: Category ID and Category. The initial data-quality assessment identified 0 duplicate rows and 0 missing values across both columns. These results indicate that the table has no fully duplicated rows or missing values. An additional check is needed to confirm that Category ID is unique.
### Stores Dataset

The Stores dataset contains 21 rows and 9 columns: ID, City, State, PostalCode, Phone, StoreType, Market, Location, and Manager. The initial data-quality assessment identified 0 duplicate rows. Three columns contain missing values: City has 1 missing value (4.76%), State has 1 missing value (4.76%), and PostalCode has 1 missing value (4.76%). The remaining six columns have no missing values. Further investigation is needed to determine whether these missing values refer to the same store and whether they affect store identification or analysis. An additional check is needed to confirm that each store ID is unique.
### Survey Dataset

The Survey dataset contains 4 rows and 2 columns: `E-Presso Market Survey` and `Unnamed: 1`. The initial data-quality assessment identified 0 duplicate rows. The `E-Presso Market Survey` column has 1 missing value (25%), while the `Unnamed: 1` column has 3 missing values (75%). These results indicate that the dataset contains substantial missing data, particularly in the unnamed column. The contents and purpose of the unnamed column should be investigated before using the dataset for analysis. Because the dataset contains only 4 rows, conclusions should be interpreted cautiously.
