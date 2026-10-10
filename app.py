import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    TEMP_WORKSPACE_DIR,
    SAMPLE_PROJECTS_DIR,
    RESULTS_DIR,
)
from src.safety import (
    get_execution_safety_warning,
    is_docker_available,
    validate_zip_file,
)
from src.repository_loader import (
    scan_repository,
    load_repository_from_zip,
    get_file_tree,
    RepositoryInfo,
)
from src.ast_analyzer import analyze_repository_ast
from src.dependency_graph import DependencyGraph
from src.change_detector import detect_changes_snapshots, ChangeDetectionResult
from src.test_discovery import discover_tests_via_ast
from src.test_selector import TestSelector
from src.test_runner import run_tests_safe, TestExecutionResult
from src.baseline_runner import run_all_modes_comparison
from src.metrics import calculate_metrics
from src.report_generator import generate_markdown_experiment_report
from src.experiment_runner import ExperimentRunner

# Page Configuration
st.set_page_config(
    page_title="Dependency-Aware Test Selection",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "base_repo_info" not in st.session_state:
    st.session_state.base_repo_info = None
if "changed_repo_info" not in st.session_state:
    st.session_state.changed_repo_info = None
if "changes" not in st.session_state:
    st.session_state.changes = None


def render_sidebar():
    st.sidebar.title("⚡ Navigation")
    page = st.sidebar.radio(
        "Select Page",
        [
            "Overview",
            "Load Repository",
            "Analyze Code",
            "Detect Changes",
            "Select Tests",
            "Execute Tests",
            "Compare Experiments",
            "Reports & Export",
            "Research Documentation",
        ],
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("🔒 **System Security Status**")
    docker_ok = is_docker_available()
    if docker_ok:
        st.sidebar.success("Docker Container Isolation: Ready")
    else:
        st.sidebar.warning("Subprocess Isolation Active")
    
    return page


def page_overview():
    st.markdown('<div class="main-header">Dependency-Aware Regression Test Selection</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">M.Tech AI Capstone System — Static AST & Dependency Graph Driven Test Selection</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 📌 Project Overview")
        st.write(
            """
            In modern software development, running large automated test suites on every minor code change is time-consuming and computationally expensive. 
            This system implements **Dependency-Aware Regression Test Selection (RTS)** for Python repositories.
            
            By parsing source code with Python's Abstract Syntax Tree (AST) and constructing a directed dependency graph in NetworkX, the application identifies exactly which functions, classes, and modules were changed, and selects only the tests that transitively depend on those changes.
            """
        )
        
        st.markdown("### 🛠️ Core Capabilities")
        st.markdown("""
        - 📂 **Multi-Source Loading**: Local directory input & secure ZIP uploads with Zip Slip prevention.
        - 🌳 **AST Analysis**: Static extraction of functions, classes, imports, relative paths, and function call targets.
        - 🕸️ **NetworkX Dependency Graph**: Transitive graph resolution linking changed code to affected test items.
        - 🔍 **Fine-Grained Change Detection**: Git diff and AST snapshot line-diffing for function-level change identification.
        - 🧪 **Safe Pytest Execution**: Isolated subprocess execution with wall-clock timeouts and `pytest-json-report` outcome parsing.
        - 📊 **Baseline Comparisons**: Benchmarking against Full Suite execution and Changed-File heuristics.
        """)

    with col2:
        st.info(get_execution_safety_warning())
        
        st.markdown("### 🏗️ Technology Stack")
        st.json({
            "Core Language": "Python 3.10+",
            "AST Parser": "Python ast module",
            "Graph Modeling": "NetworkX 3.0",
            "Testing Framework": "pytest + pytest-json-report",
            "Dashboard": "Streamlit 1.30+",
            "Data & Charts": "Pandas, Plotly",
            "Version Control": "Git / GitPython"
        })


def page_load_repository():
    st.header("📂 Load Repository")
    st.caption("Upload a ZIP archive or select a local Python repository snapshot.")

    tab1, tab2 = st.tabs(["Demo Repositories", "Upload ZIP / Local Directory"])

    with tab1:
        st.subheader("Select Sample Benchmark Repository")
        sample_choice = st.selectbox(
            "Choose a demo scenario snapshot",
            [
                "E-Commerce v1 (Baseline All Passing)",
                "E-Commerce v2_buggy (Tax Bug Regression Introduced)",
                "E-Commerce v2_clean (Tax Refactoring Clean)",
            ]
        )
        
        path_map = {
            "E-Commerce v1 (Baseline All Passing)": SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v1",
            "E-Commerce v2_buggy (Tax Bug Regression Introduced)": SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v2_buggy",
            "E-Commerce v2_clean (Tax Refactoring Clean)": SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v2_clean",
        }
        
        selected_path = path_map[sample_choice]
        
        if st.button("Load Selected Sample Repository", type="primary"):
            repo_info = scan_repository(selected_path)
            st.session_state.changed_repo_info = repo_info
            st.session_state.base_repo_info = scan_repository(SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v1")
            st.success(f"Successfully loaded repository: `{selected_path.name}`")

    with tab2:
        uploaded_zip = st.file_uploader("Upload Repository ZIP Archive", type=["zip"])
        if uploaded_zip is not None:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                tmp_zip.write(uploaded_zip.getbuffer())
                tmp_zip_path = Path(tmp_zip.name)

            if st.button("Unpack and Validate ZIP"):
                try:
                    repo_info = load_repository_from_zip(tmp_zip_path)
                    st.session_state.changed_repo_info = repo_info
                    st.success("ZIP extracted safely!")
                except Exception as e:
                    st.error(f"Failed to load ZIP: {str(e)}")

        local_dir = st.text_input("Or enter absolute path to local directory:")
        if local_dir and st.button("Load Local Directory"):
            dir_path = Path(local_dir)
            if dir_path.exists() and dir_path.is_dir():
                repo_info = scan_repository(dir_path)
                st.session_state.changed_repo_info = repo_info
                st.success(f"Loaded local directory: `{dir_path}`")
            else:
                st.error("Directory does not exist or is invalid.")

    # Show Loaded Summary
    if st.session_state.changed_repo_info:
        r_info = st.session_state.changed_repo_info
        st.markdown("---")
        st.subheader("Repository Structure Summary")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Files", r_info.total_files)
        c2.metric("Python Files", len(r_info.python_files))
        c3.metric("Source Modules", len(r_info.source_files))
        c4.metric("Test Files", len(r_info.test_files))

        st.markdown("**Discovered Python Files:**")
        st.write([r_info.get_relative_path(f) for f in r_info.python_files])


def page_analyze_code():
    st.header("🌳 AST Code Analysis & Dependency Graph")
    if not st.session_state.changed_repo_info:
        st.warning("Please load a repository first in the 'Load Repository' page.")
        return

    repo_info = st.session_state.changed_repo_info
    
    with st.spinner("Analyzing AST and building NetworkX dependency graph..."):
        dep_graph = DependencyGraph(repo_info.root_path)
        g = dep_graph.build_graph(repo_info.python_files)

    st.subheader("Graph Overview Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Nodes", g.number_of_nodes())
    c2.metric("Total Directed Edges", g.number_of_edges())
    c3.metric("Unresolved Dependencies", len(dep_graph.unresolved_dependencies))
    c4.metric("Parsed Modules", len(dep_graph.ast_map))

    tab1, tab2, tab3 = st.tabs(["Module & Symbol Table", "Dependency Edges", "Unresolved Warnings"])

    with tab1:
        rows = []
        for mod_name, ast_info in dep_graph.ast_map.items():
            for f in ast_info.functions:
                rows.append({
                    "Module": mod_name,
                    "Symbol Name": f.name,
                    "Kind": "Test" if f.is_test else "Function",
                    "Lines": f"{f.start_line}-{f.end_line}",
                    "Calls": ", ".join(f.calls) if f.calls else "-"
                })
            for c in ast_info.classes:
                rows.append({
                    "Module": mod_name,
                    "Symbol Name": c.name,
                    "Kind": "Class",
                    "Lines": f"{c.start_line}-{c.end_line}",
                    "Calls": "-"
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with tab2:
        edge_rows = []
        for u, v, d in g.edges(data=True):
            edge_rows.append({
                "Source Node": u,
                "Relationship": d.get("relation", "depends_on"),
                "Target Node": v
            })
        st.dataframe(pd.DataFrame(edge_rows), use_container_width=True)

    with tab3:
        if dep_graph.unresolved_dependencies:
            unres_rows = [
                {
                    "Source Module": u.source_module,
                    "Target Name": u.target_name,
                    "Line": u.source_line,
                    "Reason": u.reason
                }
                for u in dep_graph.unresolved_dependencies
            ]
            st.dataframe(pd.DataFrame(unres_rows), use_container_width=True)
        else:
            st.success("No unresolved static dependencies detected!")


def page_detect_changes():
    st.header("🔍 Detect Code Changes")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Baseline Snapshot (v1)")
        base_dir = st.text_input("Baseline Directory Path:", str(SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v1"))
    with col2:
        st.subheader("Changed Snapshot (v2)")
        changed_dir = st.text_input("Changed Directory Path:", str(SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v2_buggy"))

    if st.button("Compare Snapshots & Detect Changes", type="primary"):
        base_p = Path(base_dir)
        chg_p = Path(changed_dir)
        
        if base_p.exists() and chg_p.exists():
            changes = detect_changes_snapshots(base_p, chg_p)
            st.session_state.changes = changes
            st.session_state.base_repo_info = scan_repository(base_p)
            st.session_state.changed_repo_info = scan_repository(chg_p)
            st.success("Change detection complete!")

    if st.session_state.changes:
        changes = st.session_state.changes
        st.markdown("---")
        st.subheader("Change Detection Summary")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Modified Files", len(changes.modified_files))
        c2.metric("Added Files", len(changes.added_files))
        c3.metric("Deleted Files", len(changes.deleted_files))

        if changes.changed_symbols:
            st.markdown("### Changed AST Symbols / Functions")
            sym_data = [
                {
                    "Symbol": s.symbol_name,
                    "Type": s.symbol_type,
                    "Change": s.change_type,
                    "File": s.file_path.name
                }
                for s in changes.changed_symbols
            ]
            st.table(pd.DataFrame(sym_data))


def page_select_tests():
    st.header("⚡ Test Selection")
    if not st.session_state.changed_repo_info or not st.session_state.changes:
        st.warning("Please load a repository and detect changes first.")
        return

    repo_info = st.session_state.changed_repo_info
    changes = st.session_state.changes

    dep_graph = DependencyGraph(repo_info.root_path)
    dep_graph.build_graph(repo_info.python_files)

    all_tests = discover_tests_via_ast(repo_info.test_files, repo_info.root_path)
    selector = TestSelector(dep_graph, all_tests)

    st.sidebar.markdown("### Selection Parameters")
    mode = st.sidebar.selectbox("Selection Mode", ["dependency_aware", "changed_file", "full"])
    conservative = st.sidebar.checkbox("Conservative Expansion Mode", value=True)

    rationale = selector.select_tests(mode, changes, conservative=conservative)

    st.subheader(f"Selection Mode: `{mode.upper()}`")
    
    c1, c2 = st.columns(2)
    c1.metric("Selected Tests", f"{len(rationale.selected_test_ids)} / {len(all_tests)}")
    c2.metric("Selection Ratio", f"{(len(rationale.selected_test_ids) / max(1, len(all_tests))) * 100:.1f}%")

    st.markdown("### Selected Test List & Rationale")
    for t_id in rationale.selected_test_ids:
        with st.expander(f"🧪 {t_id}"):
            st.write(f"**Explanation:** {rationale.explanations.get(t_id, 'No explanation provided.')}")
            if t_id in rationale.dependency_paths and rationale.dependency_paths[t_id]:
                st.code(" -> ".join(rationale.dependency_paths[t_id]))

    if rationale.uncertainty_warnings:
        st.warning("⚠️ **Uncertainty Warnings:**")
        for w in rationale.uncertainty_warnings:
            st.write(f"- {w}")


def page_execute_tests():
    st.header("▶️ Safe Test Execution")
    if not st.session_state.changed_repo_info or not st.session_state.changes:
        st.warning("Please load a repository and detect changes first.")
        return

    repo_info = st.session_state.changed_repo_info
    changes = st.session_state.changes

    dep_graph = DependencyGraph(repo_info.root_path)
    dep_graph.build_graph(repo_info.python_files)
    all_tests = discover_tests_via_ast(repo_info.test_files, repo_info.root_path)
    selector = TestSelector(dep_graph, all_tests)

    mode = st.selectbox("Select Mode to Execute", ["dependency_aware", "changed_file", "full"])
    rationale = selector.select_tests(mode, changes)

    st.info(f"Selected **{len(rationale.selected_test_ids)}** out of **{len(all_tests)}** available tests.")

    st.warning("🔒 Safety Check: Executing tests runs arbitrary Python code in an isolated process space.")
    confirm = st.checkbox("I confirm that I want to run tests on this repository snapshot.")

    if confirm and st.button("Run Selected Tests", type="primary"):
        with st.spinner("Running tests in isolated pytest process..."):
            res = run_tests_safe(
                repo_root=repo_info.root_path,
                test_ids=rationale.selected_test_ids,
                total_discovered_count=len(all_tests),
                timeout_sec=60
            )

        st.subheader("Test Execution Outcomes")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Passed", res.passed_count)
        c2.metric("Failed", res.failed_count)
        c3.metric("Skipped", res.skipped_count)
        c4.metric("Duration", f"{res.duration_seconds:.3f}s")

        if res.test_outcomes:
            t_df = pd.DataFrame([
                {
                    "Test ID": o.test_id,
                    "Status": o.status,
                    "Duration (s)": f"{o.duration:.3f}",
                    "Failure Message": o.failure_message or "-"
                }
                for o in res.test_outcomes
            ])
            st.dataframe(t_df, use_container_width=True)


def page_compare_experiments():
    st.header("📊 Benchmark & Experiment Comparison")
    if not st.session_state.changed_repo_info or not st.session_state.changes:
        st.warning("Please load a repository and detect changes first.")
        return

    repo_info = st.session_state.changed_repo_info
    changes = st.session_state.changes

    if st.button("Run Full Baseline Comparison", type="primary"):
        with st.spinner("Executing Mode 1 (Full), Mode 2 (Changed-File), and Mode 3 (Dependency-Aware)..."):
            results_map = run_all_modes_comparison(
                repo_root=repo_info.root_path,
                changes=changes,
                timeout_sec=60
            )
            st.session_state.last_comparison = results_map

    if "last_comparison" in st.session_state:
        results_map = st.session_state.last_comparison
        
        full_res = results_map["full"].execution_result
        
        metrics_list = []
        for m_name, m_data in results_map.items():
            m = calculate_metrics(
                mode_name=m_name,
                selected_result=m_data.execution_result,
                full_suite_result=full_res,
                rationale=m_data.rationale
            )
            metrics_list.append(m)

        st.subheader("Quantitative Evaluation Table")
        m_df = pd.DataFrame([
            {
                "Mode": m.mode_name,
                "Selected / Available": f"{m.tests_selected} / {m.total_tests_available}",
                "Selection Ratio (%)": f"{m.selection_ratio * 100:.1f}%",
                "Exec Time (s)": f"{m.execution_time_seconds:.3f}s",
                "Time Reduction (%)": f"{m.time_reduction_percent:.1f}%",
                "Regressions Detected": f"{m.regressions_detected} / {m.total_known_regressions}",
                "Detection Rate (%)": f"{m.failure_detection_rate:.1f}%",
                "Missed Regressions": m.missed_regressions_count
            }
            for m in metrics_list
        ])
        st.table(m_df)

        st.subheader("Visual Comparisons")
        c1, c2 = st.columns(2)

        with c1:
            fig_time = px.bar(
                m_df,
                x="Mode",
                y="Exec Time (s)",
                title="Execution Time Comparison (Seconds)",
                color="Mode",
                text="Exec Time (s)"
            )
            st.plotly_chart(fig_time, use_container_width=True)

        with c2:
            fig_savings = px.bar(
                m_df,
                x="Mode",
                y="Time Reduction (%)",
                title="Execution Time Savings (%) vs Full Suite",
                color="Mode",
                text="Time Reduction (%)"
            )
            st.plotly_chart(fig_savings, use_container_width=True)


def page_reports():
    st.header("📄 Experiment Reports & Data Export")
    
    csv_file = RESULTS_DIR / "experiment_results.csv"
    json_file = RESULTS_DIR / "experiment_results.json"
    summary_file = RESULTS_DIR / "experiment_summary.md"

    if summary_file.exists():
        st.subheader("Latest Generated Markdown Summary Report")
        st.markdown(summary_file.read_text(encoding="utf-8"))

        st.markdown("### Download Artifacts")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "Download CSV Results",
                data=csv_file.read_text(encoding="utf-8"),
                file_name="experiment_results.csv",
                mime="text/csv"
            )
        with col2:
            st.download_button(
                "Download JSON Results",
                data=json_file.read_text(encoding="utf-8"),
                file_name="experiment_results.json",
                mime="application/json"
            )
        with col3:
            st.download_button(
                "Download Markdown Report",
                data=summary_file.read_text(encoding="utf-8"),
                file_name="experiment_summary.md",
                mime="text/markdown"
            )
    else:
        st.info("No saved experiment results found. Run `experiments/run_experiments.py` or execute a comparison run.")


def page_research():
    st.header("🔬 Research Documentation & Paper Draft")
    st.markdown("""
    ### Research Question
    > *"Can dependency-aware regression test selection reduce test execution time while maintaining adequate regression-failure detection compared with running the full test suite?"*
    
    ### Scope & Academic Disclaimer
    - **Academic Integrity**: This implementation evaluates static AST dependency graph modeling on synthetic Python benchmarks.
    - **Non-Novelty Notice**: Regression test selection is an established field in software engineering. This project implements graph-based selection for Python 3 AST without claiming unverified worldwide novelty.
    - **Threats to Validity**: Static AST analysis cannot resolve all dynamic imports (`importlib`), reflection (`getattr`), or runtime monkey-patching. Conservative mode falls back to module or full-suite execution to avoid missing failures.
    """)
    
    paper_file = BASE_DIR / "research" / "ieee_paper_draft.md"
    if paper_file.exists():
        st.markdown("---")
        st.subheader("IEEE Paper Draft Preview")
        st.markdown(paper_file.read_text(encoding="utf-8")[:3000] + "\n\n*(Full draft available in `research/ieee_paper_draft.md`)*")


def main():
    selected_page = render_sidebar()
    
    if selected_page == "Overview":
        page_overview()
    elif selected_page == "Load Repository":
        page_load_repository()
    elif selected_page == "Analyze Code":
        page_analyze_code()
    elif selected_page == "Detect Changes":
        page_detect_changes()
    elif selected_page == "Select Tests":
        page_select_tests()
    elif selected_page == "Execute Tests":
        page_execute_tests()
    elif selected_page == "Compare Experiments":
        page_compare_experiments()
    elif selected_page == "Reports & Export":
        page_reports()
    elif selected_page == "Research Documentation":
        page_research()


if __name__ == "__main__":
    main()
