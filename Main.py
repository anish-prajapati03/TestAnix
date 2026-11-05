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
            steps = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))

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
    """Create a formatted Excel workbook with test cases and ambiguities."""
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Test Cases")

        ambiguity_df = pd.DataFrame(
            {
                "#": range(1, len(ambiguities) + 1),
                "Ambiguity": ambiguities,
            }
        )
        ambiguity_df.to_excel(writer, index=False, sheet_name="Ambiguities")

        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        header_fill = PatternFill("solid", fgColor="0E7C7B")
        header_font = Font(bold=True, color="FFFFFF")
        thin = Side(style="thin", color="D9E3E2")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        widths = {
            "Test ID": 12,
            "Scenario": 34,
            "Objective": 38,
            "Test Type": 14,
            "Preconditions": 30,
            "Test Steps": 50,
            "Test Data": 28,
            "Expected Result": 38,
            "Priority": 11,
            "Ambiguity": 90,
        }

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(
                    vertical="center",
                    horizontal="center",
                )

            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    cell.border = border

            for column_cells in worksheet.columns:
                header = column_cells[0].value
                column_letter = column_cells[0].column_letter
                worksheet.column_dimensions[column_letter].width = widths.get(header, 15)

            worksheet.auto_filter.ref = worksheet.dimensions

    return buffer.getvalue()


def steps_html(active: int, mode: str = "") -> str:
    """Build the progress indicator for either generation mode."""
    if mode == "PDF":
        labels = [
            ("Input", "PDF + prompt"),
            ("Extract", "Read requirements"),
            ("Index", "Create vector store"),
            ("Generate", "AI test cases"),
            ("Export", "CSV and Excel"),
        ]
    elif mode == "Prompt-only":
        labels = [
            ("Input", "Prompt only"),
            ("Prepare", "Feature description"),
            ("Context", "Direct prompt"),
            ("Generate", "AI test cases"),
            ("Export", "CSV and Excel"),
        ]
    else:
        labels = [
            ("Input", "PDF or prompt"),
            ("Extract", "Prepare requirements"),
            ("Context", "Build context"),
            ("Generate", "AI test cases"),
            ("Export", "CSV and Excel"),
        ]

    html = '<div class="step-row">'
    for index, (title, subtitle) in enumerate(labels):
        css_class = "step done" if index < active else "step"
        html += f'<div class="{css_class}"><b>{title}</b>{subtitle}</div>'

    return html + "</div>"


# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
for key, default in {
    "result": None,
    "df": None,
    "stats": {},
    "filename": None,
    "source_mode": None,
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
        "Requirement PDF (Optional)",
        type=["pdf"],
        help=(
            "Upload a requirement PDF, or leave this empty to generate "
            "test cases directly from your prompt."
        ),
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
        value=(
            "Generate 10 to 15 test cases for login functionality.\n"
            "Include positive, negative and boundary scenarios."
        ),
        height=150,
        help=(
            "Describe the feature and scenarios. You can use this prompt "
            "with or without uploading a PDF."
        ),
    )

    generate = st.button(
        "Generate test cases",
        type="primary",
        use_container_width=True,
    )

    st.divider()
    with st.expander("How it works"):
        st.markdown(
            "**With PDF**\n"
            "1. PDF is read page by page\n"
            "2. Text is split into chunks\n"
            "3. Chunks are embedded and stored in ChromaDB\n"
            "4. Relevant requirements are retrieved\n\n"
            "**Without PDF**\n"
            "1. Your prompt is used as the requirement description\n"
            "2. No PDF processing or vector database is needed\n\n"
            "**Both modes**\n"
            "1. Groq generates structured test cases\n"
            "2. Pydantic validates the output\n"
            "3. Results can be exported to CSV or Excel"
        )


# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>TestAnix</h1>
        <p>Turn requirement documents or feature descriptions into structured, export-ready test cases.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

progress_slot = st.empty()


# ----------------------------------------------------------------------------
# Generation pipeline: PDF mode or prompt-only mode
# ----------------------------------------------------------------------------
if generate:
    if not user_request.strip():
        st.error("Please enter a feature description or test generation request.")
    elif not coverage:
        st.error("Please select at least one test type.")
    else:
        # Clear old results so failed new generations do not show stale output.
        st.session_state.result = None
        st.session_state.df = None
        st.session_state.stats = {}
        st.session_state.filename = None
        st.session_state.source_mode = None

        selected_types = ", ".join(coverage)
        mode = "PDF" if uploaded_file is not None else "Prompt-only"

        final_request = f"""
USER REQUEST:
{user_request.strip()}

SELECTED TEST TYPES:
{selected_types}

GENERATION TARGET:
Generate approximately 10 to 15 meaningful test cases for each
individual feature when the available requirements support that level
of coverage. Do not force unnecessary or duplicate cases just to reach
this number. Do not limit the entire document to 10 to 15 cases.

SOURCE MODE:
{mode}

Use the supplied requirement context and user request. Report unclear
or missing business rules as ambiguities instead of inventing them.
"""

        try:
            progress_slot.markdown(
                steps_html(1, mode),
                unsafe_allow_html=True,
            )

            with st.status("Running TestAnix pipeline...", expanded=True) as status:
                # ------------------------------------------------------------
                # MODE 1: PDF uploaded
                # ------------------------------------------------------------
                if uploaded_file is not None:
                    st.write("PDF detected. Extracting requirements...")
                    documents = load_pdf(uploaded_file)

                    if not documents:
                        raise ValueError("No readable content was found in the PDF.")

                    st.write(f"Extracted {len(documents)} pages.")

                    progress_slot.markdown(
                        steps_html(2, mode),
                        unsafe_allow_html=True,
                    )
                    st.write("Splitting requirements into chunks...")
                    chunks = split_documents(documents)

                    if not chunks:
                        raise ValueError("No text chunks could be created from the PDF.")

                    st.write(f"Created {len(chunks)} chunks.")

                    progress_slot.markdown(
                        steps_html(3, mode),
                        unsafe_allow_html=True,
                    )
                    st.write("Building vector database...")
                    vectorstore = create_vectorstore(chunks)
                    retriever = get_retriever(vectorstore)

                    filename = uploaded_file.name
                    stats = {
                        "pages": len(documents),
                        "chunks": len(chunks),
                        "source": "PDF + prompt",
                    }

                # ------------------------------------------------------------
                # MODE 2: No PDF; use the user's prompt directly
                # ------------------------------------------------------------
                else:
                    st.write("No PDF uploaded. Using your prompt as the requirement source...")
                    retriever = None
                    filename = "Prompt_Only"
                    stats = {
                        "pages": 0,
                        "chunks": 0,
                        "source": "Prompt only",
                    }

                # ------------------------------------------------------------
                # COMMON GENERATION: both modes use the same Groq agent
                # ------------------------------------------------------------
                progress_slot.markdown(
                    steps_html(4, mode),
                    unsafe_allow_html=True,
                )
                st.write("Generating structured test cases with Groq AI...")

                result = generate_test_cases(
                    retriever=retriever,
                    user_request=final_request,
                )

                if not result.test_cases:
                    raise ValueError(
                        "The AI did not return any test cases. Try a more detailed prompt."
                    )

                status.update(
                    label="Test cases generated successfully",
                    state="complete",
                    expanded=False,
                )

            # Save results in Streamlit session state.
            df = result_to_dataframe(result)
            st.session_state.result = result
            st.session_state.df = df
            st.session_state.filename = filename
            st.session_state.stats = stats
            st.session_state.source_mode = mode

            progress_slot.markdown(
                steps_html(5, mode),
                unsafe_allow_html=True,
            )
            st.toast("Test cases are ready to export.", icon="✅")

        except Exception as error:
            st.error(f"Generation failed: {error}")


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
result = st.session_state.result
df = st.session_state.df

if result is None or df is None or df.empty:
    current_mode = "PDF" if uploaded_file is not None else "Prompt-only"
    progress_slot.markdown(
        steps_html(0, current_mode),
        unsafe_allow_html=True,
    )
    st.info(
        "Enter a feature description in the sidebar. Upload a requirement PDF "
        "if you want TestAnix to use document-based requirements, or leave it "
        "empty to generate from your prompt alone."
    )

else:
    stats = st.session_state.stats

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Test cases", len(df))
    metric2.metric(
        "High priority",
        int((df["Priority"].astype(str).str.lower() == "high").sum()),
    )
    metric3.metric("Generation mode", stats.get("source", "-"))
    metric4.metric("Ambiguities", len(result.ambiguities or []))

    tab_cases, tab_charts, tab_ambiguities = st.tabs(
        ["Test cases", "Coverage summary", "Requirement ambiguities"]
    )

    # ------------------------------------------------------------------------
    # Test cases tab
    # ------------------------------------------------------------------------
    with tab_cases:
        filter1, filter2, filter3 = st.columns([2, 1, 1])
        search = filter1.text_input(
            "Search",
            placeholder="Search scenario, objective or ID",
        )

        available_types = sorted(df["Test Type"].astype(str).unique())
        available_priorities = sorted(df["Priority"].astype(str).unique())

        selected_filter_types = filter2.multiselect(
            "Test type",
            available_types,
            default=available_types,
        )
        selected_filter_priorities = filter3.multiselect(
            "Priority",
            available_priorities,
            default=available_priorities,
        )

        view = df[
            df["Test Type"].astype(str).isin(selected_filter_types)
            & df["Priority"].astype(str).isin(selected_filter_priorities)
        ]

        if search.strip():
            search_mask = view.apply(
                lambda row: search.lower() in " ".join(map(str, row.values)).lower(),
                axis=1,
            )
            view = view[search_mask]

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
            available_ids = view["Test ID"].tolist() if not view.empty else []
            if available_ids:
                selected_id = st.selectbox("Test ID", available_ids)
                selected_row = view[view["Test ID"] == selected_id].iloc[0]

                column1, column2 = st.columns(2)
                column1.markdown(f"**Scenario**\n\n{selected_row['Scenario']}")
                column1.markdown(f"**Objective**\n\n{selected_row['Objective']}")
                column1.markdown(f"**Preconditions**\n\n{selected_row['Preconditions']}")
                column2.markdown(f"**Test steps**\n\n{selected_row['Test Steps']}")
                column2.markdown(f"**Test data**\n\n{selected_row['Test Data']}")
                column2.markdown(f"**Expected result**\n\n{selected_row['Expected Result']}")
            else:
                st.info("No test cases match the selected filters.")

    # ------------------------------------------------------------------------
    # Coverage charts tab
    # ------------------------------------------------------------------------
    with tab_charts:
        chart1, chart2 = st.columns(2)

        with chart1:
            st.markdown("**By test type**")
            st.bar_chart(df["Test Type"].value_counts(), color="#0e7c7b")

        with chart2:
            st.markdown("**By priority**")
            st.bar_chart(df["Priority"].value_counts(), color="#2a9d8f")

    # ------------------------------------------------------------------------
    # Ambiguities tab
    # ------------------------------------------------------------------------
    with tab_ambiguities:
        if result.ambiguities:
            st.caption(
                "Clarify these points with your product owner before testing."
            )
            for index, issue in enumerate(result.ambiguities, 1):
                st.warning(f"**{index}.** {issue}")
        else:
            st.success("No ambiguities were reported for this request.")

    # ------------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------------
    st.divider()
    st.subheader("Export")

    base = (st.session_state.filename or "requirements").rsplit(".", 1)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    excel_bytes = build_excel(df, list(result.ambiguities or []))

    download1, download2, _ = st.columns([1, 1, 2])

    download1.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"TestAnix_{base}_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    download2.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name=f"TestAnix_{base}_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "The Excel file includes a Test Cases sheet and an Ambiguities sheet."
    )
