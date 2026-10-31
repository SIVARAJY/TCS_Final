"""AI Financial Crime Network Investigator - Streamlit Application.
Multi-entity AML & fraud intelligence platform supporting partial CSV uploads, NetworkX graph modeling,
modular anomaly detectors, and Gemini-powered cited investigation reports.
"""
from __future__ import annotations
import json
import os
import sys

# Prevent OpenBLAS/MKL thread contention and memory allocation locks on Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from typing import Dict, Any, Optional
import pandas as pd
import streamlit as st

# Ensure local imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.loader import FILE_SCHEMAS, load_csv, generate_sample_dataset
from src.graph_builder import (
    build_network_graph,
    compute_graph_summary,
    create_plotly_network_figure,
    get_account_connected_entities,
    create_account_ego_plotly,
    create_pyvis_network_html,
)
import streamlit.components.v1 as components
from src.detectors import run_all_detectors, DETECTOR_REGISTRY
from src.investigation import (
    build_investigation_cases,
    compile_case_evidence_package,
    generate_ai_investigation_report,
)

# Page Configuration
st.set_page_config(
    page_title="AI Financial Crime Network Investigator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .badge-critical {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #f87171;
    }
    .badge-high {
        background-color: #ffedd5;
        color: #9a3412;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #fb923c;
    }
    .badge-medium {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #facc15;
    }
    .badge-low {
        background-color: #f1f5f9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #cbd5e1;
    }
    .badge-pattern {
        background-color: #e0e7ff;
        color: #3730a3;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
        border: 1px solid #a5b4fc;
        letter-spacing: 0.5px;
    }
    .badge-valid {
        background-color: #dcfce7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
        border: 1px solid #86efac;
    }
    .badge-missing {
        background-color: #f1f5f9;
        color: #64748b;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.75rem;
        border: 1px solid #cbd5e1;
    }
    .finding-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .finding-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .chip-entity {
        display: inline-block;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 1px 6px;
        margin-right: 4px;
        margin-bottom: 3px;
        font-size: 0.75rem;
        font-family: monospace;
        color: #1e293b;
    }
    .report-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.2rem;
        margin-top: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "data_dict" not in st.session_state:
    st.session_state["data_dict"] = {}
if "validation_info" not in st.session_state:
    st.session_state["validation_info"] = {}
if "loaded_file_signatures" not in st.session_state:
    st.session_state["loaded_file_signatures"] = {}
if "reports_cache" not in st.session_state:
    st.session_state["reports_cache"] = {}
if "analysis_triggered" not in st.session_state:
    st.session_state["analysis_triggered"] = False


# -------------------------------------------------------------
# SIDEBAR: File Uploads & Settings
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛡️ FIU Network Investigator")
    st.caption("AI-Powered Multi-Entity Financial Crime Platform")
    st.markdown("---")

    # Demo Dataset Button
    col_demo1, col_demo2 = st.columns([1.2, 0.8])
    with col_demo1:
        if st.button("⚡ Load Demo Dataset", help="Populates all 7 synthetic CSV files with planted fraud rings"):
            sample_data = generate_sample_dataset()
            st.session_state["data_dict"] = sample_data
            st.session_state["validation_info"] = {}
            st.session_state["loaded_file_signatures"] = {"demo": "active"}
            st.session_state.pop("cached_analysis", None)
            for k, df in sample_data.items():
                from src.loader import validate_dataframe
                st.session_state["validation_info"][k] = validate_dataframe(df, k)
            st.session_state["reports_cache"] = {}
            st.session_state["analysis_triggered"] = True
            st.success("Planted 7 demo files loaded!")
            st.rerun()

    with col_demo2:
        if st.button("🗑️ Clear Data"):
            st.session_state["data_dict"] = {}
            st.session_state["validation_info"] = {}
            st.session_state["loaded_file_signatures"] = {}
            st.session_state["reports_cache"] = {}
            st.session_state["analysis_triggered"] = False
            st.session_state.pop("cached_analysis", None)
            st.rerun()

    st.markdown("#### 📂 Upload 7 Entities (CSVs)")
    st.caption("Partial files supported. Analysis runs on whatever is uploaded.")

    # Uploaders for each of the 7 CSVs
    uploaded_raw = {}
    for file_key, schema in FILE_SCHEMAS.items():
        disp = schema["display_name"]
        up_file = st.file_uploader(
            f"{disp} ({file_key}.csv)",
            type=["csv"],
            key=f"uploader_{file_key}",
            help=f"Required columns: {', '.join(schema['required_columns'][:3])}...",
        )
        if up_file is not None:
            uploaded_raw[file_key] = up_file

    # Process newly uploaded files only when changed
    if uploaded_raw:
        for file_key, buff in uploaded_raw.items():
            sig = f"{getattr(buff, 'name', file_key)}_{getattr(buff, 'size', 0)}"
            if st.session_state["loaded_file_signatures"].get(file_key) != sig:
                df, info = load_csv(buff, file_key)
                if df is not None:
                    st.session_state["data_dict"][file_key] = df
                    st.session_state["validation_info"][file_key] = info
                    st.session_state["loaded_file_signatures"][file_key] = sig
                    st.session_state.pop("cached_analysis", None)

    # Upload Status Summary
    st.markdown("##### Ingestion Status:")
    for file_key in FILE_SCHEMAS:
        has_file = file_key in st.session_state["data_dict"] and st.session_state["data_dict"][file_key] is not None
        v_info = st.session_state["validation_info"].get(file_key, {})
        is_val = v_info.get("is_valid", False)

        if has_file and is_val:
            st.markdown(f"• **{file_key}**: <span class='badge-valid'>✅ Valid ({v_info.get('row_count', 0)} rows)</span>", unsafe_allow_html=True)
        elif has_file and not is_val:
            st.markdown(f"• **{file_key}**: <span class='badge-critical'>⚠️ Missing Required Cols</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"• **{file_key}**: <span class='badge-missing'>⚪ Not uploaded</span>", unsafe_allow_html=True)

    st.markdown("---")

    # AI Configuration (Optional)
    with st.expander("🤖 AI Report Model Settings", expanded=False):
        api_key_input = st.text_input(
            "Gemini API Key (Optional)",
            type="password",
            value="",
            help="Leave empty to use GEMINI_API_KEY from environment, or use template fallback.",
        )
        selected_model = st.selectbox(
            "Gemini Model",
            ["gemini-2.5-flash", "gemini-1.5-pro"],
            index=0,
        )

    # Run Analysis Button
    has_any_data = any(df is not None and not df.empty for df in st.session_state["data_dict"].values())
    if st.button("🚀 Run Network Investigation", type="primary", disabled=not has_any_data):
        st.session_state["analysis_triggered"] = True
        st.session_state["reports_cache"] = {}
        st.rerun()


# -------------------------------------------------------------
# MAIN VIEW: Dashboard & Tabs
# -------------------------------------------------------------
st.markdown("<div class='main-title'>AI Financial Crime Network Investigator</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Deterministic Graph Analytics · Multi-Relational Entity Linking · Automated AI Case Reports</div>",
    unsafe_allow_html=True,
)

# Check if data exists
if not has_any_data:
    st.markdown("### 📂 CSV Ingestion & Data Upload Center")
    st.markdown("Upload any combination of the 7 financial crime CSV files below. The platform validates mandatory columns, normalizes headers, and runs graph detectors on whatever data is supplied (partial files gracefully supported).")

    # Quick demo button
    col_demo_main1, col_demo_main2 = st.columns([1.5, 2.5])
    with col_demo_main1:
        if st.button("⚡ Load 7 Pre-Planted Demo CSVs", type="primary", use_container_width=True):
            sample_data = generate_sample_dataset()
            st.session_state["data_dict"] = sample_data
            st.session_state["validation_info"] = {}
            for k, df in sample_data.items():
                from src.loader import validate_dataframe
                st.session_state["validation_info"][k] = validate_dataframe(df, k)
            st.session_state["reports_cache"] = {}
            st.session_state["analysis_triggered"] = True
            st.rerun()
    with col_demo_main2:
        st.caption("👈 **Instant One-Click Demo**: Populates all 7 files with planted money laundering rings (circular transactions, shared devices, rapid fund movement, funnel/dispersal accounts).")

    st.markdown("---")

    # Multi-file batch dropzone
    st.markdown("#### ⚡ Batch Upload (Drop Multiple CSVs at Once)")
    batch_files = st.file_uploader(
        "Drop all your CSVs here (automatically matched by name: transactions.csv, customers.csv, accounts.csv, beneficiaries.csv, merchants.csv, device_activity.csv, fraud_alerts.csv)",
        type=["csv"],
        accept_multiple_files=True,
        key="batch_uploader_main",
    )
    if batch_files:
        new_processed = 0
        for b_file in batch_files:
            fname = b_file.name.lower()
            matched_key = None
            if "trans" in fname:
                matched_key = "transactions"
            elif "cust" in fname:
                matched_key = "customers"
            elif "acc" in fname:
                matched_key = "accounts"
            elif "bene" in fname:
                matched_key = "beneficiaries"
            elif "merch" in fname:
                matched_key = "merchants"
            elif "dev" in fname:
                matched_key = "device_activity"
            elif "alert" in fname or "fraud" in fname:
                matched_key = "fraud_alerts"

            if matched_key:
                sig = f"{b_file.name}_{b_file.size}"
                if st.session_state["loaded_file_signatures"].get(matched_key) != sig:
                    df, info = load_csv(b_file, matched_key)
                    if df is not None:
                        st.session_state["data_dict"][matched_key] = df
                        st.session_state["validation_info"][matched_key] = info
                        st.session_state["loaded_file_signatures"][matched_key] = sig
                        st.session_state.pop("cached_analysis", None)
                        new_processed += 1
        if new_processed > 0:
            st.success(f"Processed {new_processed} uploaded file(s)!")
            st.rerun()

    st.markdown("---")

    # Individual file uploaders in a 2-column card grid
    st.markdown("#### 📋 Or Upload Individual CSV Files:")
    grid_cols = st.columns(2)
    for idx, (k, s) in enumerate(FILE_SCHEMAS.items()):
        with grid_cols[idx % 2]:
            st.markdown(f"**{s['display_name']}** (`{k}.csv`)")
            st.caption(f"{s['description']}")
            st.markdown(f"*Required:* `{', '.join(s['required_columns'])}`")
            ind_file = st.file_uploader(
                f"Upload {k}.csv",
                type=["csv"],
                key=f"main_ind_{k}",
                label_visibility="collapsed",
            )
            if ind_file is not None:
                sig = f"{ind_file.name}_{ind_file.size}"
                if st.session_state["loaded_file_signatures"].get(k) != sig:
                    df, info = load_csv(ind_file, k)
                    if df is not None:
                        st.session_state["data_dict"][k] = df
                        st.session_state["validation_info"][k] = info
                        st.session_state["loaded_file_signatures"][k] = sig
                        st.session_state.pop("cached_analysis", None)
                        st.rerun()
            st.markdown("---")

    st.stop()


# -------------------------------------------------------------
# GRAPH BUILDING & DETECTOR EXECUTION (HIGH-PERFORMANCE SESSION CACHED)
# -------------------------------------------------------------
data_dict = st.session_state["data_dict"]

# Compute fingerprint of loaded data to run heavy analysis strictly once per upload change
data_fingerprint = f"{len(data_dict)}_{sum(len(df) for df in data_dict.values() if df is not None)}"

if "cached_analysis" not in st.session_state or st.session_state.get("cached_fingerprint") != data_fingerprint:
    with st.spinner("⚡ Ingesting entities, constructing graph & running 10 detectors..."):
        G = build_network_graph(data_dict)
        graph_summary = compute_graph_summary(G)
        all_findings, detector_status = run_all_detectors(G, data_dict)
        cases = build_investigation_cases(G, all_findings)

        st.session_state["cached_analysis"] = {
            "G": G,
            "graph_summary": graph_summary,
            "all_findings": all_findings,
            "detector_status": detector_status,
            "cases": cases,
        }
        st.session_state["cached_fingerprint"] = data_fingerprint
else:
    cached = st.session_state["cached_analysis"]
    G = cached["G"]
    graph_summary = cached["graph_summary"]
    all_findings = cached["all_findings"]
    detector_status = cached["detector_status"]
    cases = cached["cases"]

# Main Navigation Tabs
tab_ingest, tab_graph, tab_detectors, tab_cases = st.tabs([
    "📁 Data Ingestion & Previews",
    "🕸️ Multi-Entity Network Graph",
    "🚨 Anomaly & Syndicate Detectors",
    "🕵️ AI Case Investigation & Reports",
])


# -------------------------------------------------------------
# TAB 1: Data Ingestion & Previews
# -------------------------------------------------------------
with tab_ingest:
    st.markdown("### 📁 CSV Upload Center, Ingestion & Validation")
    st.caption("Upload additional or replacement CSVs, inspect column validations, and examine data health metrics.")

    # High-level KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    uploaded_count = sum(1 for df in data_dict.values() if df is not None and not df.empty)
    total_records = sum(len(df) for df in data_dict.values() if df is not None)
    active_detectors = sum(1 for s in detector_status if s["status"] == "EXECUTED")

    kpi1.metric("Uploaded CSVs", f"{uploaded_count} / 7")
    kpi2.metric("Total Records Ingested", f"{total_records:,}")
    kpi3.metric("Network Entities Extracted", f"{graph_summary['num_nodes']:,}")
    kpi4.metric("Active Detectors Available", f"{active_detectors} / {len(detector_status)}")

    # In-tab uploader
    with st.expander("📤 Upload / Replace CSV Files Here", expanded=False):
        st.markdown("Drop one or multiple CSV files to add or update your dataset:")
        tab_batch_files = st.file_uploader(
            "Upload CSV files",
            type=["csv"],
            accept_multiple_files=True,
            key="tab1_batch_uploader",
        )
        if tab_batch_files:
            new_tab_processed = 0
            for b_file in tab_batch_files:
                fname = b_file.name.lower()
                matched_key = None
                if "trans" in fname:
                    matched_key = "transactions"
                elif "cust" in fname:
                    matched_key = "customers"
                elif "acc" in fname:
                    matched_key = "accounts"
                elif "bene" in fname:
                    matched_key = "beneficiaries"
                elif "merch" in fname:
                    matched_key = "merchants"
                elif "dev" in fname:
                    matched_key = "device_activity"
                elif "alert" in fname or "fraud" in fname:
                    matched_key = "fraud_alerts"

                if matched_key:
                    sig = f"{b_file.name}_{b_file.size}"
                    if st.session_state["loaded_file_signatures"].get(matched_key) != sig:
                        df, info = load_csv(b_file, matched_key)
                        if df is not None:
                            st.session_state["data_dict"][matched_key] = df
                            st.session_state["validation_info"][matched_key] = info
                            st.session_state["loaded_file_signatures"][matched_key] = sig
                            st.session_state.pop("cached_analysis", None)
                            new_tab_processed += 1
            if new_tab_processed > 0:
                st.success(f"Updated {new_tab_processed} file(s) successfully!")
                st.rerun()

    st.markdown("---")

    # Grid of the 7 Files
    for file_key, schema in FILE_SCHEMAS.items():
        disp = schema["display_name"]
        df = data_dict.get(file_key)
        info = st.session_state["validation_info"].get(file_key, {})

        with st.expander(f"{disp} ({file_key}.csv) — {'✅ Ready' if df is not None and info.get('is_valid') else '⚠️ Incomplete' if df is not None else '⚪ Not Uploaded'}", expanded=(df is not None)):
            if df is not None:
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                c1.metric("Rows", f"{info.get('row_count', len(df)):,}")
                c2.metric("Columns", f"{info.get('column_count', len(df.columns))}")
                c3.metric("Duplicates", f"{info.get('duplicate_rows', 0)}")
                
                # Required columns status
                missing_req = info.get("missing_required", [])
                if missing_req:
                    c4.error(f"Missing required columns: {', '.join(missing_req)}")
                else:
                    c4.success("All required columns matched & normalized!")

                # Schema checklist
                present_cols = [f"`{c}`" for c in df.columns]
                st.caption(f"**Columns Present:** {', '.join(present_cols)}")

                # Preview Table
                st.markdown("##### Sample Preview (First 5 Rows):")
                st.dataframe(df.head(5), use_container_width=True)

                # Null value analysis
                nulls = info.get("null_percentages", {})
                flagged_nulls = {k: v for k, v in nulls.items() if v > 0}
                if flagged_nulls:
                    st.caption(f"Missing Values: {', '.join(f'{k}: {v}%' for k, v in flagged_nulls.items())}")
            else:
                st.info(f"File `{file_key}.csv` is currently omitted. The system will continue running without it. (Prerequisite for: {schema['description']})")


# -------------------------------------------------------------
# TAB 2: Multi-Entity Network Graph
# -------------------------------------------------------------
with tab_graph:
    st.markdown("### 🕸️ Interactive Financial Crime Network Graph")
    st.caption("Multi-entity graph linking Accounts, Customers, Devices, IPs, Beneficiaries, and Merchants via NetworkX.")

    # Graph KPIs
    gk1, gk2, gk3, gk4 = st.columns(4)
    gk1.metric("Total Nodes", f"{graph_summary['num_nodes']:,}")
    gk2.metric("Total Edges / Links", f"{graph_summary['num_edges']:,}")
    gk3.metric("Connected Sub-Clusters", f"{graph_summary['num_components']:,}")
    gk4.metric("Transfer Volume Tracked", f"${graph_summary['total_transfer_volume']:,.2f}")

    st.markdown("---")

    # SECTION 1: Account Entity Explorer
    st.markdown("### 🎯 Account Entity Explorer (Pick an Account)")
    st.caption("Select any account to inspect its connected entities: customer owners, counterparties, hardware devices, IPs, beneficiaries, and merchants.")

    account_ids = sorted([n for n, d in G.nodes(data=True) if d.get("type") == "account"])
    if not account_ids:
        st.info("No account nodes found in the current dataset.")
    else:
        col_pick1, col_pick2, col_pick3 = st.columns([1.5, 1.2, 0.8])
        with col_pick1:
            selected_acc = st.selectbox(
                "Pick an Account to Inspect",
                options=account_ids,
                index=0,
                key="picked_account_selector",
            )
        with col_pick2:
            viz_engine = st.radio(
                "Visualization Engine",
                ["PyVis (Interactive Physics)", "Plotly (2D Graph)"],
                horizontal=True,
                index=0,
            )
        with col_pick3:
            hop_count = st.slider("Hop Distance", min_value=1, max_value=2, value=1, help="1-hop: immediate connected entities. 2-hop: second-degree indirect trail.")

        ego_details = get_account_connected_entities(G, selected_acc, max_hops=hop_count)

        # Account Metrics Row
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        node_d = ego_details.get("node_data", {})
        m_col1.metric("Account Type", node_d.get("account_type", "CHECKING"))
        m_col2.metric("Total Inflow", f"${ego_details.get('inflow_total', 0):,.2f}")
        m_col3.metric("Total Outflow", f"${ego_details.get('outflow_total', 0):,.2f}")
        m_col4.metric("Net Flow", f"${ego_details.get('net_flow', 0):,.2f}", delta=f"${ego_details.get('net_flow', 0):,.2f}")

        # Connected Entity Counts
        n_types = ego_details.get("nodes_by_type", {})
        counts_summary = [f"**{k.capitalize()}s**: {len(v)}" for k, v in n_types.items()]
        st.markdown("**Connected Entities:** " + " · ".join(counts_summary))

        # Render Selected Visualization Engine
        if "PyVis" in viz_engine:
            pyvis_html = create_pyvis_network_html(G, center_account=selected_acc, max_hops=hop_count, height="520px")
            components.html(pyvis_html, height=540, scrolling=True)
            st.caption("💡 **PyVis Interactive Canvas:** Drag nodes, zoom/pan with mouse wheel, or hover over edges to inspect `transaction_id`, `amount`, and `timestamp`.")
        else:
            fig_ego = create_account_ego_plotly(G, selected_acc, max_hops=hop_count)
            st.plotly_chart(fig_ego, use_container_width=True)

        # Detailed Connected Entities & Transaction Tables
        tab_txns, tab_rels = st.tabs(["💸 Connected Transactions (Edges)", "🔗 Entity Relationships & Metadata"])

        with tab_txns:
            tx_list = ego_details.get("transactions", [])
            if not tx_list:
                st.info(f"No direct financial transactions linked to {selected_acc}.")
            else:
                df_ego_tx = pd.DataFrame(tx_list)
                st.dataframe(
                    df_ego_tx[["direction", "source", "target", "transaction_id", "amount", "timestamp", "channel"]],
                    use_container_width=True,
                )

        with tab_rels:
            rel_list = ego_details.get("relationships", [])
            if not rel_list:
                st.info(f"No non-transactional relationships found for {selected_acc}.")
            else:
                df_ego_rel = pd.DataFrame(rel_list)
                st.dataframe(df_ego_rel, use_container_width=True)

    st.markdown("---")

    # SECTION 2: Full Network Graph Overview
    st.markdown("---")
    st.markdown("### 🌐 Global Multi-Entity Network Overview")
    node_type_counts = graph_summary.get("node_types", {})
    st.markdown(
        "**Global Network Breakdown:** " + " · ".join(f"**{k.capitalize()}**: {v}" for k, v in node_type_counts.items())
    )

    with st.expander("🌐 Render Global Network Graph (All Entities)", expanded=False):
        fig_network = create_plotly_network_figure(G)
        st.plotly_chart(fig_network, use_container_width=True)

    # Top Connected Entities Table
    st.markdown("#### 🏆 Top Connected Entities by Degree (Transaction & Infrastructure Hubs)")
    top_nodes = sorted(G.nodes(data=True), key=lambda x: G.degree(x[0]), reverse=True)[:10]
    top_data = []
    for nid, d in top_nodes:
        top_data.append({
            "Entity ID": nid,
            "Type": d.get("type", "unknown").upper(),
            "Total Connections": G.degree(nid),
            "In-Degree": G.in_degree(nid) if hasattr(G, "in_degree") else "-",
            "Out-Degree": G.out_degree(nid) if hasattr(G, "out_degree") else "-",
            "Risk Score": d.get("risk_score", 0),
            "Flagged": "🚩 Yes" if d.get("flagged") else "No",
        })
    st.dataframe(pd.DataFrame(top_data), use_container_width=True)


# -------------------------------------------------------------
# TAB 3: Anomaly & Syndicate Detectors
# -------------------------------------------------------------
with tab_detectors:
    st.markdown("### 🚨 Forensic Anomaly & Syndicate Detectors")
    st.caption("10 modular AML detectors covering graph topologies, rapid fund velocity, infrastructure sharing, and entity reuse.")

    # Detectors summary
    dk1, dk2, dk3, dk4 = st.columns(4)
    crit_count = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
    high_count = sum(1 for f in all_findings if f.get("severity") == "HIGH")
    med_low_count = sum(1 for f in all_findings if f.get("severity") in ("MEDIUM", "LOW"))
    syndicates_count = len(cases)

    dk1.metric("Total Anomalies Detected", f"{len(all_findings):,}")
    dk2.metric("Critical Flags (Cycles/Rapid Flow)", f"{crit_count}", delta=f"{crit_count} Critical" if crit_count > 0 else None, delta_color="inverse")
    dk3.metric("High Severity Flags", f"{high_count}")
    dk4.metric("Medium / Low (Shared IP/Dev Capped)", f"{med_low_count}")

    st.markdown("---")

    # Modular Detector Status Table with Methodologies
    st.markdown("#### ⚙️ Modular Detector Status & Methodology Reference")
    
    detector_why_map = {
        "G05": "Groups beneficiaries by account/name across distinct source accounts/owners",
        "G06": "Multi-accounting on identical hardware fingerprint (strictly capped at Low/Medium, never Critical)",
        "G07": "Concentrated sessions from identical network IP (strictly capped at Low/Medium, never Critical)",
        "T06": "Time logic: Inflow immediately followed by comparable outflow within <= 2 hours",
        "T08": "nx.simple_cycles directed graph loop discovery (round-trip layering)",
        "A07": "In-degree counts identifying aggregation hubs receiving from >= 3 distinct sources",
        "A09": "Out-degree counts identifying dispersal hubs distributing to >= 3 distinct destinations",
        "K03": "Pandas groupby on phone, email, and tax ID to detect synthetic/shared identities",
        "D04": "Set comparison between historical baseline devices and session device logs",
        "B02": "Single formula: Top payee volume / total account outflow >= 70% (min $5,000)",
    }

    status_rows = []
    for s in detector_status:
        p_id = s["id"]
        status_rows.append({
            "Pattern": p_id,
            "Detector Name": s["name"],
            "Status": "✅ EXECUTED" if s["status"] == "EXECUTED" else f"⚪ SKIPPED ({s['description']})",
            "Findings Count": s["findings_count"],
            "Core Logic / Constraint": detector_why_map.get(p_id, s["description"]),
        })
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True)

    st.markdown("---")

    # Findings Breakdown Header
    st.markdown(f"#### 🔎 Detected Suspicious Patterns ({len(all_findings)} Findings)")

    # Multi-dimensional Filtering Controls
    f_col1, f_col2, f_col3 = st.columns([1, 1, 1.5])
    with f_col1:
        sev_filter = st.selectbox(
            "Filter by Severity",
            ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
            index=0,
            key="findings_sev_filter",
        )
    with f_col2:
        available_pats = ["ALL"] + sorted(list(set(f.get("pattern_id", "OTHER") for f in all_findings)))
        pat_filter = st.selectbox(
            "Filter by Pattern ID",
            available_pats,
            index=0,
            key="findings_pat_filter",
        )
    with f_col3:
        search_query = st.text_input(
            "Search Findings (Entity, Finding ID, or Keyword)",
            value="",
            placeholder="e.g. ACC-101, FND-T08, DEV-7, 192.168...",
            key="findings_search_query",
        )

    # Apply Filters
    filtered_findings = all_findings
    if sev_filter != "ALL":
        filtered_findings = [f for f in filtered_findings if f.get("severity") == sev_filter]
    if pat_filter != "ALL":
        filtered_findings = [f for f in filtered_findings if f.get("pattern_id") == pat_filter]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_findings = [
            f for f in filtered_findings
            if q in f.get("finding_id", "").lower()
            or q in f.get("pattern_name", "").lower()
            or q in f.get("description", "").lower()
            or any(q in str(e).lower() for e in f.get("entities", []))
            or any(q in str(t).lower() for t in f.get("transaction_ids", []))
        ]

    st.caption(f"Displaying **{len(filtered_findings)}** of **{len(all_findings)}** findings:")

    if not filtered_findings:
        st.info("No findings matching the selected filters.")
    else:
        for idx, f in enumerate(filtered_findings):
            sev = f.get("severity", "MEDIUM")
            badge_class = (
                "badge-critical" if sev == "CRITICAL"
                else "badge-high" if sev == "HIGH"
                else "badge-medium" if sev == "MEDIUM"
                else "badge-low"
            )
            score = f.get("risk_score", f.get("score", 0))
            fid = f.get("finding_id", f"FND-{idx+1:03d}")
            pid = f.get("pattern_id", "DET")
            pname = f.get("pattern_name", f.get("title", "Suspicious Activity"))
            desc = f.get("description", "")
            entities = f.get("entities", [])
            tx_ids = f.get("transaction_ids", [])
            evidence = f.get("evidence", [])
            alt = f.get("alternative_explanation", f.get("legitimate_alternative", "No benign explanation recorded."))
            rec = f.get("recommended_review", "Conduct manual compliance review and verify customer KYC.")
            score_reasons = f.get("score_reasons", {})

            # Clean card representation
            with st.container():
                st.markdown(
                    f"""
                    <div class='finding-card'>
                        <div class='finding-header'>
                            <div>
                                <span class='badge-pattern'>{pid}</span>
                                <b style='font-size: 1.05rem; color: #0f172a; margin-left: 8px;'>{pname}</b>
                                <span style='font-size: 0.8rem; color: #64748b; margin-left: 10px; font-family: monospace;'>[{fid}]</span>
                            </div>
                            <div>
                                <span class='{badge_class}'>{sev}</span>
                                <span style='background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 0.75rem; color: #1e293b; margin-left: 6px;'>
                                    Risk Score: {score}/100
                                </span>
                            </div>
                        </div>
                        <p style='font-size: 0.88rem; color: #334155; margin: 6px 0;'>{desc}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Entity chips and details
                with st.expander(f"📋 Forensic Evidence Dossier & Score Breakdown ({fid})", expanded=False):
                    det_col1, det_col2 = st.columns([1.2, 1])

                    with det_col1:
                        st.markdown("**Entities Involved:**")
                        chips_html = "".join(f"<span class='chip-entity'>{e}</span>" for e in entities)
                        st.markdown(chips_html, unsafe_allow_html=True)

                        if tx_ids:
                            st.markdown(f"**Linked Transactions ({len(tx_ids)}):**")
                            tx_chips = "".join(f"<span class='chip-entity'>{t}</span>" for t in tx_ids[:10])
                            if len(tx_ids) > 10:
                                tx_chips += f"<span class='chip-entity'>+{len(tx_ids)-10} more</span>"
                            st.markdown(tx_chips, unsafe_allow_html=True)

                        st.markdown("**Forensic Evidence Points:**")
                        for ev in evidence:
                            st.markdown(f"- {ev}")

                    with det_col2:
                        st.markdown("**Risk Score Breakdown:**")
                        if score_reasons:
                            st.json(score_reasons)
                        else:
                            st.caption(f"Calculated base score: {score}/100")

                        st.markdown("**💡 Alternative Benign Explanation:**")
                        st.info(alt)

                        st.markdown("**🛡️ Recommended Compliance Review:**")
                        st.success(rec)


# -------------------------------------------------------------
# TAB 4: AI Case Investigation & Reports
# -------------------------------------------------------------
with tab_cases:
    st.markdown("### 🕵️ AI Case Investigation & Evidence Dossier")
    st.caption("Synthesizes multi-entity case findings into a cited investigation report with competing hypotheses.")

    if not cases:
        st.info("No cases clustered from current data.")
    else:
        # Case Selector
        case_options = {c["id"]: f"{c['id']} — {c['title']} (Risk: {c['risk_score']}/100, {c['entity_count']} Entities)" for c in cases}
        selected_case_id = st.selectbox(
            "Select Investigation Case to Review",
            options=list(case_options.keys()),
            format_func=lambda x: case_options[x],
        )

        selected_case = next(c for c in cases if c["id"] == selected_case_id)

        # Case Metrics
        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("Risk Score", f"{selected_case['risk_score']} / 100", delta=selected_case['risk_level'], delta_color="inverse")
        cm2.metric("Evidence Strength", selected_case['evidence_strength'])
        cm3.metric("Investigation Confidence", f"{selected_case['confidence']} / 100")
        cm4.metric("Entities in Ring", f"{selected_case['entity_count']}")

        # Case Subgraph View
        st.markdown("#### 🔬 Syndicate Cluster Subgraph")
        case_entities = selected_case.get("entities", [])
        sub_G = G.subgraph(case_entities) if G.number_of_nodes() > 0 else G
        fig_sub = create_plotly_network_figure(
            sub_G,
            highlight_nodes=case_entities,
            case_title=f"{selected_case['id']} Syndicate Subgraph ({len(case_entities)} Entities)",
        )
        st.plotly_chart(fig_sub, use_container_width=True)

        st.markdown("---")

        # AI Report Generation Section
        st.markdown("#### 📑 Formal Case Investigation Report")

        evidence_pkg = compile_case_evidence_package(G, selected_case, data_dict)

        col_rep1, col_rep2 = st.columns([1.5, 3])
        with col_rep1:
            gen_btn = st.button("✨ Generate AI Case Report", type="primary", key=f"btn_gen_{selected_case_id}")

        if gen_btn or selected_case_id in st.session_state["reports_cache"]:
            if gen_btn:
                with st.spinner("Analyzing transaction patterns, formulating competing hypotheses, and writing case brief..."):
                    report_result = generate_ai_investigation_report(
                        evidence=evidence_pkg,
                        api_key=api_key_input if api_key_input else None,
                        model=selected_model,
                    )
                    st.session_state["reports_cache"][selected_case_id] = report_result

            report = st.session_state["reports_cache"].get(selected_case_id)

            if report:
                # Render Report Container
                st.markdown("<div class='report-box'>", unsafe_allow_html=True)

                # Report Header & Verdict
                verdict_str = report.get("verdict", "suspicious").replace("_", " ").upper()
                verdict_color = "#991b1b" if "FRAUD" in verdict_str else "#9a3412" if "SUSPICIOUS" in verdict_str else "#166534"
                
                st.markdown(
                    f"""
                    <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px;'>
                        <h3 style='margin:0; color:#0f172a;'>Case Dossier: {selected_case_id}</h3>
                        <span style='background: {verdict_color}15; color: {verdict_color}; border: 1px solid {verdict_color}50; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 0.85rem;'>
                            VERDICT: {verdict_str}
                        </span>
                    </div>
                    <div style='font-size: 0.8rem; color: #64748b; margin-bottom: 12px;'>
                        <b>Report Source:</b> {report.get('source', 'System')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Executive Summary
                st.markdown("##### 📌 Executive Summary")
                st.write(report.get("summary", ""))

                # Structural Pattern Analysis
                if report.get("pattern_analysis"):
                    st.markdown("##### 🔄 Multi-Transaction Pattern Analysis")
                    st.write(report.get("pattern_analysis"))

                # Competing Hypotheses
                hypotheses = report.get("hypotheses", [])
                if hypotheses:
                    st.markdown("##### ⚖️ Competing Investigative Hypotheses")
                    for h in hypotheses:
                        conf_pct = int(h.get("confidence", 0.5) * 100)
                        st.markdown(f"**{h.get('title', 'Hypothesis')}** (Confidence: {conf_pct}%)")
                        st.progress(conf_pct / 100.0)
                        if h.get("note"):
                            st.caption(h.get("note"))
                        
                        sup = h.get("supporting", [])
                        against = h.get("against", [])
                        if sup:
                            st.markdown(f"• *Supporting Evidence IDs:* `{', '.join(sup)}`")
                        if against:
                            st.markdown(f"• *Counter-Evidence / Contradictions:* `{', '.join(against)}`")
                        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

                # Narrative
                if report.get("narrative"):
                    st.markdown("##### 📝 Case Narrative")
                    st.write(report.get("narrative"))

                # Legitimate Alternatives
                alts = report.get("legitimate_alternatives", [])
                if alts:
                    st.markdown("##### 🛡️ Legitimate Alternative Explanations to Rule Out")
                    for a in alts:
                        exp = a.get("explanation", "")
                        verify = a.get("how_to_verify", "")
                        st.markdown(f"• **Explanation:** {exp}")
                        if verify:
                            st.caption(f"  *Verification Step:* {verify}")

                # Recommended Actions
                actions = report.get("recommended_actions", [])
                if actions:
                    st.markdown("##### 🎯 Recommended Next Compliance Actions")
                    for act in actions:
                        st.markdown(f"- [ ] {act}")

                st.markdown("</div>", unsafe_allow_html=True)

                # Download Buttons
                col_dl1, col_dl2 = st.columns([1, 1])
                with col_dl1:
                    st.download_button(
                        "📥 Download Report as JSON",
                        data=json.dumps(report, indent=2),
                        file_name=f"{selected_case_id}_investigation_report.json",
                        mime="application/json",
                    )
                with col_dl2:
                    md_text = f"# Investigation Case Report: {selected_case_id}\n\n"
                    md_text += f"**Verdict:** {verdict_str}\n"
                    md_text += f"**Risk Score:** {selected_case['risk_score']}/100 ({selected_case['risk_level']})\n\n"
                    md_text += f"## Executive Summary\n{report.get('summary', '')}\n\n"
                    md_text += f"## Pattern Analysis\n{report.get('pattern_analysis', '')}\n\n"
                    md_text += f"## Narrative\n{report.get('narrative', '')}\n\n"
                    md_text += f"## Recommended Actions\n" + "\n".join(f"- {a}" for a in actions)
                    st.download_button(
                        "📄 Download Report as Markdown",
                        data=md_text,
                        file_name=f"{selected_case_id}_case_report.md",
                        mime="text/markdown",
                    )
