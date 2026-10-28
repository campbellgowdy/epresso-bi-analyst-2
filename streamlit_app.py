
"""E-Presso data explorer with data profiling and a rules-based assistant."""
from pathlib import Path

import streamlit as st

import agent
import analytics

MAX_QUESTIONS = 15
DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(page_title="E-Presso Data Explorer", layout="wide")
st.title("E-Presso Data Explorer")
st.caption("Explore data, check data quality, and ask questions about a loaded table.")


@st.cache_data(show_spinner=False)
def cached_load(file_bytes: bytes, filename: str, sheet_name=0):
    return analytics.load_table(file_bytes, filename, sheet_name)


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

tab_data, tab_dash, tab_assistant = st.tabs(
    ["Data and profile", "Dashboard", "Assistant"]
)

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

with tab_dash:
    st.info(
        "The dashboard is not built yet. We will add business metrics, "
        "filters, and charts after confirming the data loads correctly."
    )

with tab_assistant:
    st.caption("Mode: rules-based assistant using approved analytical functions.")
    st.session_state.setdefault("n_questions", 0)
    st.session_state.setdefault("history", [])

    for item in st.session_state["history"]:
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            st.markdown(f"**Scope:** {item['answer']['scope']}")
            st.markdown(f"**Findings:** {item['answer']['findings']}")
            if item["answer"]["interpretation"]:
                st.markdown(
                    f"**Interpretation:** {item['answer']['interpretation']}"
                )
            with st.expander("Tool-call log"):
                st.json(item["answer"]["tool_log"])

    question = st.chat_input("Ask a question about the loaded data")

    if question:
        if st.session_state["n_questions"] >= MAX_QUESTIONS:
            st.warning(
                "Question limit reached for this session. Reload the page to start over."
            )
        else:
            st.session_state["n_questions"] += 1
            answer = agent.answer_question(question, df, mode="rules")
            st.session_state["history"].append(
                {"question": question, "answer": answer}
            )
            st.rerun()

