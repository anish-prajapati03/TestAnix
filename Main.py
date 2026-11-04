import io
from datetime import datetime

import pandas as pd
import streamlit as st

from RequirementLoader.pdf import load_pdf
from RequirementLoader.text_splitter import split_documents
from VectorStore.chroma_db import create_vectorstore, get_retriever
from Agents.test_case_agent import generate_test_cases


# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="TestAnix | QA Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --ink: #0f2a2e;
        --teal: #0e7c7b;
        --teal-dark: #0a5c5b;
        --mint: #e6f4f1;
        --line: #d9e3e2;
        --muted: #5d7275;
    }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.01em; }

    .hero {
        background: linear-gradient(120deg, #0a5c5b 0%, #0e7c7b 60%, #2a9d8f 100%);
        border-radius: 14px;
        padding: 28px 34px;
        color: #fff;
        margin-bottom: 1.4rem;
    }
    .hero h1 { color: #fff; margin: 0; font-size: 2.1rem; }
    .hero p { margin: 6px 0 0; font-size: 1.02rem; opacity: .92; }

    .step-row { display: flex; gap: 10px; margin: 0 0 1.2rem; flex-wrap: wrap; }
    .step {
        flex: 1; min-width: 140px; padding: 10px 14px; border-radius: 10px;
        border: 1px solid var(--line); background: #fff; font-size: .88rem; color: var(--muted);
    }
    .step b { color: var(--ink); display: block; font-size: .92rem; }
    .step.done { background: var(--mint); border-color: #b7dcd5; }
    .step.done b { color: var(--teal-dark); }

    div[data-testid="stMetric"] {
        background: #fff; border: 1px solid var(--line);
        border-radius: 12px; padding: 14px 18px;
    }
    div[data-testid="stMetricLabel"] { color: var(--muted); }

    .stButton > button[kind="primary"], .stDownloadButton > button {
        border-radius: 10px; font-weight: 600;
    }
    section[data-testid="stSidebar"] { border-right: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def result_to_dataframe(result) -> pd.DataFrame:
    rows = []
    for case in result.test_cases:
        steps = case.test_steps
        if isinstance(steps, (list, tuple)):
            steps = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        rows.append(
            {
                "Test ID": case.test_id,
                "Scenario": case.scenario,
                "Objective": case.objective,
                "Test Type": case.test_type,
                "Preconditions": case.preconditions,
                "Test Steps": steps,
                "Test Data": case.test_data,
                "Expected Result": case.expected_result,
                "Priority": case.priority,
            }
        )
    return pd.DataFrame(rows)


def build_excel(df: pd.DataFrame, ambiguities: list) -> bytes:
    """Create a formatted .xlsx with a Test Cases sheet and an Ambiguities sheet."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Test Cases")
        amb_df = pd.DataFrame(
            {"#": range(1, len(ambiguities) + 1), "Ambiguity": ambiguities}
        )
        amb_df.to_excel(writer, index=False, sheet_name="Ambiguities")

        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

        header_fill = PatternFill("solid", fgColor="0E7C7B")
        header_font = Font(bold=True, color="FFFFFF")
        thin = Side(style="thin", color="D9E3E2")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        widths = {
            "Test ID": 12, "Scenario": 34, "Objective": 38, "Test Type": 14,
            "Preconditions": 30, "Test Steps": 50, "Test Data": 28,
            "Expected Result": 38, "Priority": 11,
        }

        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(vertical="center", horizontal="center")
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    cell.border = border
            for col_cells in ws.columns:
                header = col_cells[0].value
                letter = col_cells[0].column_letter
                ws.column_dimensions[letter].width = widths.get(
                    header, 90 if header == "Ambiguity" else 8
                )
            ws.auto_filter.ref = ws.dimensions
    return buffer.getvalue()


def steps_html(active: int) -> str:
    labels = [
        ("Upload", "PDF requirements"),
        ("Process", "Extract and chunk"),
        ("Index", "Vector database"),
        ("Generate", "AI test cases"),
        ("Export", "CSV and Excel"),
    ]
    html = '<div class="step-row">'
    for i, (title, sub) in enumerate(labels):
        cls = "step done" if i < active else "step"
        html += f'<div class="{cls}"><b>{title}</b>{sub}</div>'
    return html + "</div>"


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
for key, default in {
    "result": None,
    "df": None,
    "stats": {},
    "filename": None,
}.items():
    st.session_state.setdefault(key, default)


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧪 TestAnix")
    st.caption("AI-powered QA testing agent")
    st.divider()

    uploaded_file = st.file_uploader(
        "Requirement document", type=["pdf"], help="Upload a software requirement PDF."
    )

    st.markdown("**Test coverage**")
    coverage = st.multiselect(
        "Test types to include",
        ["Positive", "Negative", "Boundary", "Security", "Performance", "Usability"],
        default=["Positive", "Negative", "Boundary", "Security"],
        label_visibility="collapsed",
    )

    user_request = st.text_area(
        "Test generation request",
        value="Generate test cases for login functionality.\nInclude positive, negative and boundary scenarios.",
        height=130,
        help="Describe the functionality and scenarios you want TestAnix to cover.",
    )

    generate = st.button("Generate test cases", type="primary", use_container_width=True)

    st.divider()
    with st.expander("How it works"):
        st.markdown(
            "1. PDF is read page by page\n"
            "2. Text is split into 1000-character chunks (200 overlap)\n"
            "3. Chunks are embedded and stored in ChromaDB\n"
            "4. The 4 most relevant chunks are retrieved\n"
            "5. Groq LLM writes structured test cases\n"
            "6. Output is validated and ready to export"
        )


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>TestAnix</h1>
        <p>Turn requirement documents into structured, export-ready test cases.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

progress_slot = st.empty()


# ----------------------------------------------------------------------------
# Generation pipeline
# ----------------------------------------------------------------------------
if generate:
    if uploaded_file is None:
        st.error("Upload a requirement PDF in the sidebar to continue.")
    elif not user_request.strip():
        st.error("Please enter your test generation request.")
    else:
        selected_types = ", ".join(coverage)
        final_request = f"""
User Request:
{user_request}

Selected Test Types:
{selected_types if selected_types else "All applicable test types"}

Generate 10 to 15 test cases for each individual feature
identified in the uploaded requirements document.

Do not limit the entire document to 10 to 15 test cases.
"""

        try:
            progress_slot.markdown(steps_html(1), unsafe_allow_html=True)
            with st.status("Running TestAnix pipeline...", expanded=True) as status:
                st.write("Extracting PDF requirements...")
                documents = load_pdf(uploaded_file)
                st.write(f"Extracted {len(documents)} pages.")

                progress_slot.markdown(steps_html(2), unsafe_allow_html=True)
                st.write("Splitting requirements into chunks...")
                chunks = split_documents(documents)
                st.write(f"Created {len(chunks)} chunks.")

                progress_slot.markdown(steps_html(3), unsafe_allow_html=True)
                st.write("Building vector database...")
                vectorstore = create_vectorstore(chunks)
                retriever = get_retriever(vectorstore)

                progress_slot.markdown(steps_html(4), unsafe_allow_html=True)
                st.write("Generating test cases with AI...")
                result = generate_test_cases(retriever, final_request)

                status.update(label="Test cases generated", state="complete", expanded=False)

            df = result_to_dataframe(result)
            st.session_state.result = result
            st.session_state.df = df
            st.session_state.filename = uploaded_file.name
            st.session_state.stats = {"pages": len(documents), "chunks": len(chunks)}
            progress_slot.markdown(steps_html(5), unsafe_allow_html=True)
            st.toast("Test cases are ready to export.", icon="✅")

        except Exception as e:
            st.error(f"Generation failed: {e}")


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
result = st.session_state.result
df = st.session_state.df

if result is None or df is None or df.empty:
    progress_slot.markdown(steps_html(1 if uploaded_file else 0), unsafe_allow_html=True)
    st.info(
        "Upload a requirement PDF, choose the coverage you need, then select "
        "**Generate test cases** in the sidebar."
    )
else:
    stats = st.session_state.stats

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Test cases", len(df))
    m2.metric("High priority", int((df["Priority"].astype(str).str.lower() == "high").sum()))
    m3.metric("Pages read", stats.get("pages", "-"))
    m4.metric("Ambiguities", len(result.ambiguities or []))

    tab_cases, tab_charts, tab_amb = st.tabs(
        ["Test cases", "Coverage summary", "Requirement ambiguities"]
    )

    # ---- Test cases tab
    with tab_cases:
        f1, f2, f3 = st.columns([2, 1, 1])
        search = f1.text_input("Search", placeholder="Search scenario, objective or ID")
        types = sorted(df["Test Type"].astype(str).unique())
        prios = sorted(df["Priority"].astype(str).unique())
        sel_types = f2.multiselect("Test type", types, default=types)
        sel_prios = f3.multiselect("Priority", prios, default=prios)

        view = df[
            df["Test Type"].astype(str).isin(sel_types)
            & df["Priority"].astype(str).isin(sel_prios)
        ]
        if search.strip():
            mask = view.apply(
                lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1
            )
            view = view[mask]

        st.caption(f"Showing {len(view)} of {len(df)} test cases")
        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True,
            height=460,
            column_config={
                "Test Steps": st.column_config.TextColumn(width="large"),
                "Scenario": st.column_config.TextColumn(width="medium"),
                "Expected Result": st.column_config.TextColumn(width="medium"),
            },
        )

        with st.expander("Read a single test case"):
            pick = st.selectbox("Test ID", view["Test ID"].tolist() if len(view) else [])
            if pick:
                row = view[view["Test ID"] == pick].iloc[0]
                c1, c2 = st.columns(2)
                c1.markdown(f"**Scenario**\n\n{row['Scenario']}")
                c1.markdown(f"**Objective**\n\n{row['Objective']}")
                c1.markdown(f"**Preconditions**\n\n{row['Preconditions']}")
                c2.markdown(f"**Test steps**\n\n{row['Test Steps']}")
                c2.markdown(f"**Test data**\n\n{row['Test Data']}")
                c2.markdown(f"**Expected result**\n\n{row['Expected Result']}")

    # ---- Charts tab
    with tab_charts:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**By test type**")
            st.bar_chart(df["Test Type"].value_counts(), color="#0e7c7b")
        with c2:
            st.markdown("**By priority**")
            st.bar_chart(df["Priority"].value_counts(), color="#2a9d8f")

    # ---- Ambiguities tab
    with tab_amb:
        if result.ambiguities:
            st.caption("Clarify these points with your product owner before testing.")
            for i, issue in enumerate(result.ambiguities, 1):
                st.warning(f"**{i}.** {issue}")
        else:
            st.success("No ambiguities were reported for this document.")

    # ---- Export
    st.divider()
    st.subheader("Export")
    base = (st.session_state.filename or "requirements").rsplit(".", 1)[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    xlsx_bytes = build_excel(df, list(result.ambiguities or []))

    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"TestAnix_{base}_{stamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    d2.download_button(
        "Download Excel",
        data=xlsx_bytes,
        file_name=f"TestAnix_{base}_{stamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
    st.caption("The Excel file includes a Test Cases sheet and an Ambiguities sheet.")