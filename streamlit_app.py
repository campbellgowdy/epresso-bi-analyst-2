
"""E-Presso data explorer with data profiling and a rules-based assistant."""
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

import agent
import analytics

MAX_QUESTIONS = 15
DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(page_title="E-Presso Data Explorer", layout="wide")

st.markdown(
    """
    <style>
   
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Dancing+Script:wght@500;600;700&display=swap');

/* Main app background */
.stApp,
[data-testid="stAppViewContainer"] {
    background-color: #FFF7F0 !important;
    color: #642F20 !important;
    font-family: 'DM Sans', sans-serif;
}

/* Soft paper texture */
[data-testid="stAppViewContainer"] {
    background-image:
        radial-gradient(rgba(216, 143, 145, 0.07) 0.7px, transparent 0.7px);
    background-size: 6px 6px;
}

/* Pink gingham sidebar */
[data-testid="stSidebar"] > div:first-child {
    background-color: #FBE5E0 !important;
    background-image:
        linear-gradient(rgba(216, 143, 145, 0.13) 50%, transparent 50%),
        linear-gradient(90deg, rgba(216, 143, 145, 0.13) 50%, transparent 50%);
    background-size: 26px 26px;
    border-right: 1px solid #E8C4BE;
}

/* Headings */
h1, h2, h3,
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
    font-family: 'Dancing Script', cursive !important;
    color: #642F20 !important;
    font-weight: 700 !important;
}

/* Heading sizes */
h1 { font-size: 48px !important; }
h2 { font-size: 36px !important; }
h3 { font-size: 28px !important; }

/* Regular text */
.stApp p,
.stApp label,
.stApp li,
.stApp [data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"] {
    color: #642F20;
    font-family: 'DM Sans', sans-serif;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: #FFF9F4;
    border: 1px solid #E8C4BE;
    border-radius: 14px;
    padding: 18px 20px;
}

div[data-testid="stMetricLabel"] {
    color: #805348 !important;
    font-weight: 600;
}

div[data-testid="stMetricValue"] {
    color: #642F20 !important;
    font-weight: 800;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #805348 !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #642F20 !important;
    border-bottom-color: #D88F91 !important;
}

/* Buttons */
.stButton > button {
    background-color: #D88F91 !important;
    color: #FFFFFF !important;
    border: 1px solid #C77B70 !important;
    border-radius: 10px !important;
}

.stButton > button:hover {
    background-color: #C77B70 !important;
    border-color: #C77B70 !important;
    color: #FFFFFF !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #E8C4BE;
    border-radius: 12px;
    overflow: hidden;
    background-color: #FFF9F4;
    box-shadow: 0 2px 8px rgba(100, 47, 32, 0.06);
}

/* Dataframe headers */
[data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #FBE5E0 !important;
    color: #642F20 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
}

/* Dropdowns */
[data-baseweb="select"] > div {
    border: 1.5px solid #C77B70 !important;
    border-radius: 8px !important;
    background-color: #FFF9F4 !important;
}

[data-baseweb="select"] > div:focus-within {
    border: 2px solid #D88F91 !important;
    box-shadow: 0 0 0 2px rgba(216, 143, 145, 0.15) !important;
}



    </style>
    """,
    unsafe_allow_html=True,
)


st.title("E-Presso Data Explorer ☕")
st.caption("Explore data, check data quality, and ask questions about a loaded table.")


@st.cache_data(show_spinner=False)
def cached_load(file_bytes: bytes, filename: str, sheet_name=0):
    return analytics.load_table(file_bytes, filename, sheet_name)


@st.cache_data(show_spinner=False)
def cached_all_access_tables(file_path: str, table_names: tuple):
    return {
        name: analytics.load_access_table(file_path, name)
        for name in table_names
    }



@st.cache_data(show_spinner=False)
def cached_access_tables(file_path: str, table_name: str):
    return analytics.load_access_table(file_path, table_name)


with st.sidebar:
    st.header("Choose your data")

    source = st.radio(
        "Where is your file?",
        ["Files in repository", "Upload a file"],
    )

    if source == "Files in repository":
        supported = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".xlsm", ".accdb", ".mdb"}
        files = sorted(
            p for p in DATA_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in supported
        ) if DATA_DIR.exists() else []

        if not files:
            st.error("No supported data files were found in the data folder.")
            st.stop()

        selected_file = st.selectbox(
            "Select a file",
            files,
            format_func=lambda p: p.name,
        )

        if selected_file.suffix.lower() in {".accdb", ".mdb"}:
            try:
                table_names = analytics.access_table_names(str(selected_file))
            except Exception as exc:
                st.error(f"Could not read the Access database: {exc}")
                st.stop()

            if not table_names:
                st.error("No tables were found in this Access database.")
                st.stop()

            selected_table = st.selectbox("Select a table", table_names)

            try:
                df = cached_access_tables(str(selected_file), selected_table)
            except Exception as exc:
                st.error(f"Could not load that Access table: {exc}")
                st.stop()
        else:
            sheet = 0
            if selected_file.suffix.lower() in analytics.EXCEL_EXT:
                try:
                    sheet_names = analytics.excel_sheet_names(
                        selected_file.read_bytes()
                    )
                    sheet = st.selectbox("Select a sheet", sheet_names)
                except Exception as exc:
                    st.error(f"Could not read the Excel sheets: {exc}")
                    st.stop()

            try:
                df = cached_load(
                    selected_file.read_bytes(),
                    selected_file.name,
                    sheet,
                )
            except Exception as exc:
                st.error(f"Could not load that file: {exc}")
                st.stop()

        st.caption(f"Source: {selected_file.name}")

    else:
        uploaded = st.file_uploader(
            "Upload CSV, Excel, or Access-compatible data",
            type=["csv", "txt", "tsv", "xlsx", "xls", "xlsm"],
        )

        if uploaded is None:
            st.info("Upload a CSV or Excel file to continue.")
            st.stop()

        sheet = 0
        if uploaded.name.lower().endswith(analytics.EXCEL_EXT):
            sheet_names = analytics.excel_sheet_names(uploaded.getvalue())
            sheet = st.selectbox("Select a sheet", sheet_names)

        try:
            df = cached_load(uploaded.getvalue(), uploaded.name, sheet)
        except Exception as exc:
            st.error(f"Could not load that file: {exc}")
            st.stop()


# Load supporting tables for relationship checks when using repository files.
relationship_tables = {}

if source == "Files in repository":
    access_path = DATA_DIR / "Support_EX_B_Sales (1).accdb"
    stores_path = DATA_DIR / "Support_EX_B_Stores (3).csv"

    if access_path.exists() and stores_path.exists():
        try:
            relationship_tables = cached_all_access_tables(
                str(access_path),
                ("Sales", "Products", "Categories"),
            )
            relationship_tables["Stores"] = cached_load(
                stores_path.read_bytes(),
                stores_path.name,
            )
        except Exception as exc:
            st.warning(f"Could not load all tables for relationship checks: {exc}")


if relationship_tables:
    st.subheader("Relationship validation")

    relationships = [
        ("Sales", "Product ID", "Products", "Product ID"),
        ("Sales", "Category ID", "Categories", "Category ID"),
        ("Sales", "Store ID", "Stores", "ID"),
    ]


    relationship_results = []

    for source_name, source_col, target_name, target_col in relationships:
        if source_name not in relationship_tables:
            st.warning(f"Missing source table: {source_name}")
            continue

        if target_name not in relationship_tables:
            st.warning(
                f"Missing target table: {target_name}. "
                f"Tables loaded: {list(relationship_tables.keys())}"
            )
            continue

        result = analytics.check_foreign_keys(
            relationship_tables[source_name],
            source_col,
            relationship_tables[target_name],
            target_col,
        )

        relationship_results.append({
            "Source": f"{source_name}.{source_col}",
            "Target": f"{target_name}.{target_col}",
            "Unmatched rows": result["unmatched_count"],
            "Unmatched values (up to 20)": str(result["unmatched_values"]),
            "Error": result["error"],
        })


if relationship_results:
    st.dataframe(relationship_results, use_container_width=True)
else:
    st.warning("No relationship results were generated. Check the table names above.")


tab_data, tab_dash, tab_assistant = st.tabs([
    "✿ Data and Profile",
    "✧ Dashboard",
    "♡ Assistant"
])

with tab_data:
    profile = analytics.profile_table(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{profile['rows']:,}")
    c2.metric("Columns", profile["columns"])
    c3.metric("Duplicate rows", profile["duplicate_rows"])

    st.subheader("Data preview")
    st.dataframe(df.head(50), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Missing values")
        st.dataframe(profile["missing"], use_container_width=True)
    with right:
        st.subheader("Data types")
        st.dataframe(profile["dtypes"], use_container_width=True)
        
    st.subheader("ID validation")

    id_checks = {
        "Sales ID": ("Sales", "Sales ID"),
        "Product ID": ("Products", "Product ID"),
        "Category ID": ("Categories", "Category ID"),
        "Store ID": ("Stores", "ID"),
    }

    st.caption(
        "These checks run on the currently selected dataset. "
        "Only the ID column present in that dataset will be checked."
    )

    results = []
    for label, (table_name, id_col) in id_checks.items():
        if id_col in df.columns:
            result = analytics.check_unique_ids(df, id_col)
            result["table"] = table_name
            results.append(result)

if results:
    results_df = pd.DataFrame(results)

    # Add visual indicators for validation results
    for column in ["exists", "is_unique"]:
        if column in results_df.columns:
            results_df[column] = results_df[column].map(
                lambda value: "🟢 ✓" if value is True
                else "🔴 ✕" if value is False
                else value
            )

    st.dataframe(results_df, use_container_width=True)

else:
    st.info("No recognized ID column was found in this dataset.")






with tab_dash:

    # Dashboard styling
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600;700&family=DM+Sans:wght@400;500;600;700;800&display=swap');

        .dashboard-header {
            text-align: center;
            background: #FFF8F5;
            padding: 28px 15px;
            border-radius: 18px;
            border: 1px solid #F1DAD8;
            margin-bottom: 22px;
        }

        .dashboard-header h1 {
            font-family: 'Dancing Script', cursive;
            font-size: 48px;
            color: #875B58;
            margin-bottom: 4px;
        }

        .dashboard-header p {
            font-family: 'DM Sans', sans-serif;
            color: #8D706B;
            font-size: 15px;
            margin: 0;
        }

        div[data-testid="stMetric"] {
            background: #FFF8F5;
            border: 1px solid #F1DAD8;
            border-radius: 15px;
            padding: 18px;
        }

        div[data-testid="stMetricLabel"] {
            color: #8D706B;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            color: #875B58;
            font-weight: 800;
        }

        .insight-card {
            background: #FFF8F5;
            border: 1px solid #F1DAD8;
            border-left: 5px solid #D99A9A;
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 12px;
            color: #765B57;
        }
        </style>

        <div class="dashboard-header">
            <h1>☕ E-Presso Dashboard</h1>
            <p>A little look at how our coffee business is brewing</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    

    # Dashboard filter
    st.markdown("### 🎀 Dashboard Filters")

    dashboard_df = df.copy()

    if (
        relationship_tables
        and "Stores" in relationship_tables
        and "Store ID" in dashboard_df.columns
        and "StoreType" in relationship_tables["Stores"].columns
    ):
        stores_df = relationship_tables["Stores"].copy()

        store_types = sorted(
            stores_df["StoreType"].dropna().astype(str).unique().tolist()
        )

        store_type_filter = st.selectbox(
            "🏪 Store Type",
            options=["All Store Types"] + store_types,
        )

        if store_type_filter != "All Store Types":
            matching_store_ids = stores_df.loc[
                stores_df["StoreType"].astype(str) == store_type_filter,
                "ID",
            ]
            dashboard_df = dashboard_df[
                dashboard_df["Store ID"].isin(matching_store_ids)
            ]
    else:
        st.caption("Store type filtering is unavailable for this table.")

    # KPI metrics
    if "Revenue" in dashboard_df.columns:

        total_revenue = dashboard_df["Revenue"].sum()

        transaction_count = (
            dashboard_df["Sales ID"].nunique()
            if "Sales ID" in dashboard_df.columns
            else len(dashboard_df)
        )

        average_revenue = (
            total_revenue / transaction_count
            if transaction_count > 0
            else 0
        )

        store_count = (
            dashboard_df["Store ID"].nunique()
            if "Store ID" in dashboard_df.columns
            else 0
        )

        st.markdown("### ☕ At a Glance")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("💰 Total Revenue", f"${total_revenue:,.2f}")

        with col2:
            st.metric("🧾 Transactions", f"{transaction_count:,}")

        with col3:
            st.metric("☕ Average Sale", f"${average_revenue:,.2f}")

        with col4:
            st.metric("🏪 Stores", f"{store_count:,}")

    else:
        st.warning("Select the Sales table to view revenue metrics.")

    st.markdown("---")

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    # Revenue by Category
    with chart_col1:
        st.markdown("### 🍰 Revenue by Category")

        if (
            "Revenue" in dashboard_df.columns
            and "Category ID" in dashboard_df.columns
            and relationship_tables
            and "Categories" in relationship_tables
        ):
            categories_df = relationship_tables["Categories"].copy()

            categories_df = categories_df.drop_duplicates(
                subset=["Category ID"]
            )

            sales_with_categories = dashboard_df.merge(
                categories_df[["Category ID", "Category"]],
                on="Category ID",
                how="left",
                validate="many_to_one",
            )

            category_revenue = (
                sales_with_categories
                .groupby("Category", as_index=False)["Revenue"]
                .sum()
                .sort_values("Revenue", ascending=True)
            )

            if not category_revenue.empty:
                fig = px.bar(
                    category_revenue,
                    x="Revenue",
                    y="Category",
                    orientation="h",
                    text_auto=",.0f",
                    color_discrete_sequence=["#D99A9A"],
                )

                fig.update_layout(
                    xaxis_title="Revenue ($)",
                    yaxis_title="",
                    height=380,
                    font={"family": "DM Sans", "color": "#765B57"},
                    plot_bgcolor="#FFFDFC",
                    paper_bgcolor="#FFFDFC",
                    margin=dict(l=10, r=10, t=20, b=10),
                )

                fig.update_traces(
                    marker_line_color="#C98282",
                    marker_line_width=1,
                    textfont_color="#765B57",
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No category revenue data is available.")
        else:
            st.info("Category information is unavailable.")

    # Revenue by Store Type
    with chart_col2:
        st.markdown("### 🏪 Revenue by Store Type")

        if (
            "Revenue" in dashboard_df.columns
            and "Store ID" in dashboard_df.columns
            and relationship_tables
            and "Stores" in relationship_tables
        ):
            stores_df = relationship_tables["Stores"].copy()

            stores_df = stores_df.drop_duplicates(subset=["ID"])

            sales_with_stores = dashboard_df.merge(
                stores_df[["ID", "StoreType"]],
                left_on="Store ID",
                right_on="ID",
                how="left",
                validate="many_to_one",
            )

            store_type_revenue = (
                sales_with_stores
                .groupby("StoreType", as_index=False)["Revenue"]
                .sum()
            )

            if not store_type_revenue.empty:
                fig = px.pie(
                    store_type_revenue,
                    names="StoreType",
                    values="Revenue",
                    hole=0.55,
                    color_discrete_sequence=[
                        "#D99A9A",
                        "#B9827C",
                        "#E8C7BF",
                        "#A66F69",
                    ],
                )

                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                )

                fig.update_layout(
                    height=380,
                    font={"family": "DM Sans", "color": "#765B57"},
                    paper_bgcolor="#FFFDFC",
                    margin=dict(l=10, r=10, t=20, b=10),
                    showlegend=False,
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No store type revenue data is available.")
        else:
            st.info("Store information is unavailable.")

    st.markdown("---")

    # Business Insights
    st.markdown("### 💡 A Few Business Insights")

    if (
        "Revenue" in dashboard_df.columns
        and "Category ID" in dashboard_df.columns
        and relationship_tables
        and "Categories" in relationship_tables
    ):
        categories_df = relationship_tables["Categories"].copy()
        categories_df = categories_df.drop_duplicates(
            subset=["Category ID"]
        )

        insight_data = dashboard_df.merge(
            categories_df[["Category ID", "Category"]],
            on="Category ID",
            how="left",
            validate="many_to_one",
        )

        insight_revenue = (
            insight_data.groupby("Category")["Revenue"].sum()
        )

        if not insight_revenue.empty:
            top_category = insight_revenue.idxmax()
            top_category_revenue = insight_revenue.max()

            insight_col1, insight_col2, cup_col = st.columns([1, 1, 1])

            with insight_col1:
                st.markdown(
                    f"""
                    <div class="insight-card">
                        🏆 <strong>Top Category</strong><br>
                        {top_category} generated
                        ${top_category_revenue:,.2f} in revenue.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with insight_col2:
                category_share = (
                    top_category_revenue / total_revenue * 100
                    if total_revenue > 0
                    else 0
                )

                st.markdown(
                    f"""
                    <div class="insight-card">
                        📊 <strong>Category Contribution</strong><br>
                        {top_category} represents
                        {category_share:.1f}% of total revenue.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("Business insights are available when Sales and Categories data are loaded.")



with tab_assistant:
    st.caption("Mode: rules-based assistant using approved analytical functions.")
    st.session_state.setdefault("n_questions", 0)
    st.session_state.setdefault("history", [])

    for item in st.session_state["history"]:
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            st.markdown(f"**Answer:** {item['answer']['scope']}")
            st.markdown(f"**Findings:** {item['answer']['findings']}")
            if item["answer"]["interpretation"]:
                st.markdown(
                    f"**Interpretation:** {item['answer']['interpretation']}"
                )
            with st.expander("Tool-call log"):
                st.json(item["answer"]["tool_log"])

    # Prepare data for the assistant
    assistant_df = df.copy()

    if (
        "Revenue" in assistant_df.columns
        and "Store ID" in assistant_df.columns
        and relationship_tables
        and "Stores" in relationship_tables
    ):
        assistant_df = assistant_df.merge(
            relationship_tables["Stores"][["ID", "StoreType"]],
            left_on="Store ID",
            right_on="ID",
            how="left",
        )
        # Add category names for revenue-by-category questions
    if (
        "Category ID" in assistant_df.columns
        and relationship_tables
        and "Categories" in relationship_tables
    ):
        assistant_df = assistant_df.merge(
            relationship_tables["Categories"][["Category ID", "Category"]],
            on="Category ID",
            how="left",
        )

    # Question box heading
    st.markdown(
        """
        <div style="font-size: 19px; font-weight: 700; color: #765238;
                    margin-top: 18px; margin-bottom: 8px;">
            🔍 What would you like to know about your data?
        </div>
        <div style="font-size: 13px; color: #8B684B; margin-bottom: 8px;">
            Ask about revenue, categories, store types, or data quality.
        </div>
        """,
        unsafe_allow_html=True,
    )

    question = st.chat_input("Type your question here...")

    if question:
        if st.session_state["n_questions"] >= MAX_QUESTIONS:
            st.warning(
                "Question limit reached for this session. Reload the page to start over."
            )
        else:
            st.session_state["n_questions"] += 1

            thinking = st.empty()
            thinking.markdown(
                """
                <style>
                @keyframes coffee-fill {
                    from { height: 8px; }
                    to { height: 48px; }
                }
                @keyframes coffee-steam {
                    0% { opacity: 0; transform: translateY(5px); }
                    50% { opacity: 1; }
                    100% { opacity: 0; transform: translateY(-8px); }
                }
                .coffee-pot {
                    width: 54px;
                    height: 65px;
                    border: 3px solid #765238;
                    border-radius: 8px 8px 15px 15px;
                    position: relative;
                    overflow: hidden;
                    margin: 8px auto;
                    background: #FBF8F2;
                }
                .coffee-liquid {
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 8px;
                    background: #9B633B;
                    animation: coffee-fill 2.5s ease-in-out infinite alternate;
                }
                .coffee-handle {
                    position: absolute;
                    right: -17px;
                    top: 17px;
                    width: 14px;
                    height: 25px;
                    border: 3px solid #765238;
                    border-radius: 0 12px 12px 0;
                }
                .coffee-steam {
                    color: #9B8068;
                    font-size: 18px;
                    text-align: center;
                    animation: coffee-steam 1.5s ease-in-out infinite;
                }
                </style>
                <div style="text-align:center; color:#765238;">
                    <div class="coffee-steam">〰 〰</div>
                    <div style="display:inline-block; position:relative;">
                        <div class="coffee-pot">
                            <div class="coffee-liquid"></div>
                        </div>
                        <div class="coffee-handle"></div>
                    </div>
                    <div style="font-weight:700; font-size:17px;">
                        Brewing your answer...
                    </div>
                    <div style="font-size:13px; color:#8B684B;">
                        Just a moment while E-Presso prepares your insights.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            answer = agent.answer_question(
                question, assistant_df, mode="rules"
            )

            thinking.empty()

            st.session_state["history"].append(
                {"question": question, "answer": answer}
            )
            st.rerun()
