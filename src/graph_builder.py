"""Multi-entity financial crime network graph builder using NetworkX.
Constructs a directed multi-relational graph with nodes for:
customers, accounts, beneficiaries, merchants, devices, and IPs.
Edges store transaction_id, timestamp, and amount.
Includes interactive Plotly and PyVis network visualizers for account-centric entity exploration.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple, Set
import networkx as nx
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pyvis.network import Network

# Standardized color scheme across Plotly & PyVis
NODE_COLORS = {
    "account": "#1f6f78",       # Deep teal
    "customer": "#3b5b7a",      # Navy blue
    "beneficiary": "#059669",   # Emerald green
    "merchant": "#475569",      # Slate grey
    "device": "#d97706",        # Amber orange
    "ip": "#7c3aed",            # Violet purple
    "alert": "#dc2626",         # Crimson red
    "unknown": "#94a3b8",       # Muted slate
}

NODE_SIZES = {
    "account": 18,
    "customer": 22,
    "beneficiary": 17,
    "merchant": 19,
    "device": 16,
    "ip": 14,
    "alert": 15,
    "unknown": 12,
}


def build_network_graph(data_dict: Dict[str, pd.DataFrame]) -> nx.MultiDiGraph:
    """Builds an in-memory directed NetworkX graph with nodes for:
    - customers
    - accounts
    - beneficiaries
    - merchants
    - devices
    - IPs
    and edges preserving transaction_id, timestamp, amount, and relationship types.
    """
    G = nx.MultiDiGraph()

    # 1. Accounts & Customers
    if "accounts" in data_dict and data_dict["accounts"] is not None and not data_dict["accounts"].empty:
        df_acc = data_dict["accounts"]
        for _, row in df_acc.iterrows():
            acc_id = str(row.get("account_id", "")).strip()
            cust_id = str(row.get("customer_id", "")).strip()
            if not acc_id:
                continue

            G.add_node(
                acc_id,
                type="account",
                label=acc_id,
                account_type=str(row.get("account_type", "CHECKING")),
                balance=float(row.get("balance", 0.0) or 0.0),
                status=str(row.get("status", "ACTIVE")),
                customer_id=cust_id,
                risk_score=0,
                flagged=False,
            )

            if cust_id:
                if cust_id not in G:
                    G.add_node(
                        cust_id,
                        type="customer",
                        label=cust_id,
                        name=cust_id,
                        risk_rating="UNKNOWN",
                        risk_score=0,
                        flagged=False,
                    )
                G.add_edge(cust_id, acc_id, type="OWNS", label="OWNS")

    # 2. Customers KYC Enrichment
    if "customers" in data_dict and data_dict["customers"] is not None and not data_dict["customers"].empty:
        df_cust = data_dict["customers"]
        for _, row in df_cust.iterrows():
            cust_id = str(row.get("customer_id", "")).strip()
            if not cust_id:
                continue
            name = str(row.get("name", cust_id)).strip()
            risk_rating = str(row.get("risk_rating", "LOW")).upper()

            if cust_id in G:
                G.nodes[cust_id]["name"] = name
                G.nodes[cust_id]["label"] = f"{name} ({cust_id})"
                G.nodes[cust_id]["risk_rating"] = risk_rating
                G.nodes[cust_id]["tax_id"] = str(row.get("tax_id", ""))
                G.nodes[cust_id]["country"] = str(row.get("country", ""))
            else:
                G.add_node(
                    cust_id,
                    type="customer",
                    label=f"{name} ({cust_id})",
                    name=name,
                    risk_rating=risk_rating,
                    tax_id=str(row.get("tax_id", "")),
                    country=str(row.get("country", "")),
                    risk_score=0,
                    flagged=False,
                )

    # 3. Transactions (Edges keeping transaction_id, timestamp, and amount)
    if "transactions" in data_dict and data_dict["transactions"] is not None and not data_dict["transactions"].empty:
        df_tx = data_dict["transactions"]
        for _, row in df_tx.iterrows():
            src = str(row.get("source_account_id", "")).strip()
            tgt = str(row.get("target_account_id", "")).strip()
            if not src or not tgt:
                continue

            amt = float(row.get("amount", 0.0) or 0.0)
            txn_id = str(row.get("transaction_id", f"TXN-{np.random.randint(1000, 9999)}")).strip()
            ts = str(row.get("timestamp", "")).strip()
            channel = str(row.get("channel", "TRANSFER")).strip()

            if src not in G:
                G.add_node(src, type="account", label=src, risk_score=0, flagged=False)
            if tgt not in G:
                G.add_node(tgt, type="account", label=tgt, risk_score=0, flagged=False)

            G.add_edge(
                src,
                tgt,
                key=txn_id,
                type="TRANSFERRED",
                label="TRANSFER",
                transaction_id=txn_id,
                amount=amt,
                timestamp=ts,
                channel=channel,
            )

    # 4. Beneficiaries
    if "beneficiaries" in data_dict and data_dict["beneficiaries"] is not None and not data_dict["beneficiaries"].empty:
        df_bene = data_dict["beneficiaries"]
        for _, row in df_bene.iterrows():
            acc_id = str(row.get("account_id", "")).strip()
            bene_acc = str(row.get("beneficiary_account", "")).strip()
            bene_id = str(row.get("beneficiary_id", f"BEN-{np.random.randint(100, 999)}")).strip()
            bene_name = str(row.get("name", bene_acc)).strip()
            rel = str(row.get("relationship", "BENEFICIARY")).strip()
            if not acc_id or not bene_acc:
                continue

            if acc_id not in G:
                G.add_node(acc_id, type="account", label=acc_id, risk_score=0, flagged=False)
            if bene_acc not in G:
                G.add_node(
                    bene_acc,
                    type="beneficiary",
                    label=f"Bene: {bene_name}",
                    name=bene_name,
                    relationship=rel,
                    risk_score=0,
                    flagged=False,
                )
            else:
                # If already present, mark as beneficiary relationship
                G.nodes[bene_acc].setdefault("is_beneficiary", True)

            G.add_edge(
                acc_id,
                bene_acc,
                key=bene_id,
                type="BENEFICIARY_OF",
                label=f"BENE: {rel}",
                relationship=rel,
                beneficiary_id=bene_id,
            )

    # 5. Merchants
    if "merchants" in data_dict and data_dict["merchants"] is not None and not data_dict["merchants"].empty:
        df_merch = data_dict["merchants"]
        for _, row in df_merch.iterrows():
            mid = str(row.get("merchant_id", "")).strip()
            if not mid:
                continue
            mname = str(row.get("merchant_name", mid)).strip()
            risk = str(row.get("risk_level", "LOW")).upper()
            cat = str(row.get("category", "Commercial")).strip()

            if mid in G:
                G.nodes[mid]["type"] = "merchant"
                G.nodes[mid]["merchant_name"] = mname
                G.nodes[mid]["label"] = f"{mname} ({mid})"
                G.nodes[mid]["risk_level"] = risk
                G.nodes[mid]["category"] = cat
            else:
                G.add_node(
                    mid,
                    type="merchant",
                    label=f"{mname} ({mid})",
                    merchant_name=mname,
                    risk_level=risk,
                    category=cat,
                    risk_score=0,
                    flagged=False,
                )

    # 6. Devices and IPs
    if "device_activity" in data_dict and data_dict["device_activity"] is not None and not data_dict["device_activity"].empty:
        df_dev = data_dict["device_activity"]
        for _, row in df_dev.iterrows():
            dev_id = str(row.get("device_id", "")).strip()
            if not dev_id:
                continue

            cust_id = str(row.get("customer_id", "")).strip()
            acc_id = str(row.get("account_id", "")).strip()
            ip = str(row.get("ip_address", "")).strip()
            loc = str(row.get("location", "")).strip()

            if dev_id not in G:
                G.add_node(dev_id, type="device", label=f"Device: {dev_id}", location=loc, risk_score=0, flagged=False)

            if cust_id:
                if cust_id not in G:
                    G.add_node(cust_id, type="customer", label=cust_id, risk_score=0, flagged=False)
                G.add_edge(cust_id, dev_id, type="USED_DEVICE", label="USED_DEVICE")

            if acc_id:
                if acc_id not in G:
                    G.add_node(acc_id, type="account", label=acc_id, risk_score=0, flagged=False)
                G.add_edge(acc_id, dev_id, type="ACC_DEVICE", label="ACC_DEVICE")

            if ip:
                if ip not in G:
                    G.add_node(ip, type="ip", label=f"IP: {ip}", location=loc, risk_score=0, flagged=False)
                G.add_edge(dev_id, ip, type="LOGGED_IP", label="LOGGED_IP")

    # 7. Fraud Alerts (Flags)
    if "fraud_alerts" in data_dict and data_dict["fraud_alerts"] is not None and not data_dict["fraud_alerts"].empty:
        df_alerts = data_dict["fraud_alerts"]
        for _, row in df_alerts.iterrows():
            alt_id = str(row.get("alert_id", "")).strip()
            ent_id = str(row.get("entity_id", "")).strip()
            alt_type = str(row.get("alert_type", "Suspicious Alert")).strip()
            sev = str(row.get("severity", "MEDIUM")).upper()
            desc = str(row.get("description", "")).strip()
            if not alt_id:
                continue

            if alt_id not in G:
                G.add_node(
                    alt_id,
                    type="alert",
                    label=f"ALERT: {alt_type}",
                    alert_type=alt_type,
                    severity=sev,
                    description=desc,
                    risk_score=90 if sev in ("CRITICAL", "HIGH") else 50,
                    flagged=True,
                )

            if ent_id:
                if ent_id in G:
                    G.nodes[ent_id]["flagged"] = True
                    G.nodes[ent_id].setdefault("alerts", []).append(alt_type)
                else:
                    G.add_node(ent_id, type="account", label=ent_id, flagged=True, alerts=[alt_type])
                G.add_edge(alt_id, ent_id, type="FLAGGED_ALERT", label=f"ALERT: {sev}")

    return G


def compute_graph_summary(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """Calculates graph metrics and entity distributions."""
    node_types: Dict[str, int] = {}
    for _, d in G.nodes(data=True):
        t = d.get("type", "unknown")
        node_types[t] = node_types.get(t, 0) + 1

    edge_types: Dict[str, int] = {}
    for _, _, d in G.edges(data=True):
        t = d.get("type", "OTHER")
        edge_types[t] = edge_types.get(t, 0) + 1

    UG = G.to_undirected()
    components = list(nx.connected_components(UG))

    total_volume = sum(
        d.get("amount", 0.0) for _, _, d in G.edges(data=True) if d.get("type") == "TRANSFERRED"
    )

    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "node_types": node_types,
        "edge_types": edge_types,
        "num_components": len(components),
        "largest_component_size": len(max(components, key=len)) if components else 0,
        "total_transfer_volume": total_volume,
    }


def get_account_connected_entities(
    G: nx.MultiDiGraph,
    account_id: str,
    max_hops: int = 1,
) -> Dict[str, Any]:
    """Extracts all connected entities (customers, accounts, beneficiaries, merchants, devices, IPs)
    and transaction edge records for a specific account.
    """
    if account_id not in G:
        return {
            "account_id": account_id,
            "exists": False,
            "connected_nodes": [],
            "transactions": [],
            "relationships": [],
            "subgraph": nx.MultiDiGraph(),
        }

    # Gather nodes within N hops (undirected traversal)
    UG = G.to_undirected()
    connected_nodes: Set[str] = {account_id}

    current_layer = {account_id}
    for _ in range(max_hops):
        next_layer = set()
        for n in current_layer:
            if n in UG:
                next_layer.update(UG.neighbors(n))
        connected_nodes.update(next_layer)
        current_layer = next_layer

    # Create induced subgraph
    sub_G = G.subgraph(connected_nodes).copy()

    # Partition transactions vs structural relationships
    transactions = []
    relationships = []

    for u, v, k, d in sub_G.edges(keys=True, data=True):
        edge_type = d.get("type", "OTHER")
        if edge_type == "TRANSFERRED":
            direction = "OUTFLOW" if u == account_id else "INFLOW" if v == account_id else "TRANSIT"
            transactions.append({
                "source": u,
                "target": v,
                "direction": direction,
                "transaction_id": d.get("transaction_id", k),
                "amount": float(d.get("amount", 0.0)),
                "timestamp": d.get("timestamp", ""),
                "channel": d.get("channel", "TRANSFER"),
            })
        else:
            relationships.append({
                "source": u,
                "target": v,
                "type": edge_type,
                "label": d.get("label", edge_type),
                "details": d.get("relationship", d.get("description", "")),
            })

    # Group connected nodes by type
    nodes_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for n in connected_nodes:
        nd = G.nodes[n]
        ntype = nd.get("type", "unknown")
        nodes_by_type.setdefault(ntype, []).append({
            "id": n,
            "type": ntype,
            "label": nd.get("label", n),
            "risk_score": nd.get("risk_score", 0),
            "flagged": nd.get("flagged", False),
        })

    # Total inflow and outflow metrics
    inflow_total = sum(t["amount"] for t in transactions if t["direction"] == "INFLOW")
    outflow_total = sum(t["amount"] for t in transactions if t["direction"] == "OUTFLOW")

    return {
        "account_id": account_id,
        "exists": True,
        "node_data": G.nodes[account_id],
        "connected_nodes": list(connected_nodes),
        "nodes_by_type": nodes_by_type,
        "transactions": transactions,
        "relationships": relationships,
        "inflow_total": inflow_total,
        "outflow_total": outflow_total,
        "net_flow": inflow_total - outflow_total,
        "subgraph": sub_G,
    }


def create_plotly_network_figure(
    G: nx.MultiDiGraph,
    highlight_nodes: Optional[List[str]] = None,
    case_title: Optional[str] = None,
) -> go.Figure:
    """NetworkX + Plotly network figure visualizing nodes and edges.
    Supports node highlighting and custom case titles.
    """
    if G.number_of_nodes() == 0:
        fig = go.Figure()
        fig.update_layout(title="No entities in current network graph", template="plotly_white")
        return fig

    # Fast layout computation (capped iterations for large graphs to prevent UI freezing)
    render_G = G
    if G.number_of_nodes() > 250 and not highlight_nodes:
        # Prioritize high-degree infrastructure hubs & flagged entities
        top_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:250]
        render_G = G.subgraph(top_nodes)

    num_n = render_G.number_of_nodes()
    iters = 15 if num_n > 100 else 30

    try:
        pos = nx.spring_layout(render_G, seed=42, iterations=iters, k=1.0 / (num_n ** 0.5) if num_n > 0 else 0.1)
    except Exception:
        pos = {n: (np.random.rand(), np.random.rand()) for n in render_G.nodes()}

    edge_x = []
    edge_y = []

    for source, target in render_G.edges():
        if source in pos and target in pos:
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        name="Connections",
    )

    node_x = []
    node_y = []
    node_texts = []
    hover_texts = []
    node_colors = []
    node_sizes = []

    highlight_set = set(highlight_nodes) if highlight_nodes else set()

    for node in render_G.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            d = render_G.nodes[node]
            ntype = d.get("type", "unknown")
            label = d.get("label", str(node))
            node_texts.append(str(node))

            lines = [f"<b>{node}</b> ({ntype.upper()})"]
            if "name" in d:
                lines.append(f"Name: {d['name']}")
            if "balance" in d:
                lines.append(f"Balance: ${d['balance']:,.2f}")
            if "risk_score" in d and d["risk_score"] > 0:
                lines.append(f"Risk Score: {d['risk_score']}/100")
            if d.get("flagged"):
                lines.append("🚩 <i>FLAGGED SUSPICIOUS</i>")
            hover_texts.append("<br>".join(lines))

            if highlight_set and node in highlight_set:
                node_colors.append("#dc2626")
                node_sizes.append(20)
            elif d.get("flagged"):
                node_colors.append("#e11d48")
                node_sizes.append(18)
            else:
                node_colors.append(NODE_COLORS.get(ntype, "#1f77b4"))
                node_sizes.append(NODE_SIZES.get(ntype, 15))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_texts,
        textposition="top center",
        hovertext=hover_texts,
        hoverinfo="text",
        name="Entities",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="white"),
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])

    title_text = case_title or f"Network Graph Visualization ({G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges)"
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=14, color="#0f172a")),
        showlegend=False,
        hovermode="closest",
        template="plotly_white",
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=540,
    )

    return fig


def create_account_ego_plotly(
    G: nx.MultiDiGraph,
    account_id: str,
    max_hops: int = 1,
) -> go.Figure:
    """Renders a focused Plotly network view centered on the picked account.
    Edges prominently show transaction_id, timestamp, and amount.
    """
    ego_data = get_account_connected_entities(G, account_id, max_hops)
    sub_G = ego_data["subgraph"]

    if sub_G.number_of_nodes() == 0:
        fig = go.Figure()
        fig.add_annotation(text=f"Account '{account_id}' not found in network.", showarrow=False)
        fig.update_layout(height=400)
        return fig

    # Layout: arrange center node in middle with spring layout
    UG = sub_G.to_undirected()
    pos = nx.spring_layout(UG, k=0.45, iterations=50, seed=42)
    # Ensure center node sits at (0, 0)
    if account_id in pos:
        pos[account_id] = np.array([0.0, 0.0])

    edge_x = []
    edge_y = []
    edge_hover = []

    # Middle scatter for edge hover labels
    mid_x = []
    mid_y = []
    mid_hover = []

    for u, v, d in sub_G.edges(data=True):
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]

        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        # Edge label
        if d.get("type") == "TRANSFERRED":
            amt_str = f"${d.get('amount', 0):,.2f}"
            txn = d.get('transaction_id', 'N/A')
            ts = d.get('timestamp', 'N/A')
            lbl = f"TRANSFER: {u} → {v}<br>Amount: {amt_str}<br>Txn ID: {txn}<br>Time: {ts}"
        else:
            lbl = f"{d.get('type', 'RELATION')}: {u} → {v}"

        mid_x.append((x0 + x1) / 2)
        mid_y.append((y0 + y1) / 2)
        mid_hover.append(lbl)

    # Edge lines trace
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.8, color="#94a3b8"),
        hoverinfo="none",
        mode="lines",
        name="Connection",
    )

    # Edge midpoint hover trace
    mid_trace = go.Scatter(
        x=mid_x,
        y=mid_y,
        mode="markers",
        marker=dict(size=8, color="#64748b", symbol="arrow-bar-up"),
        hoverinfo="text",
        text=mid_hover,
        name="Txn Details",
    )

    # Node traces grouped by entity type
    traces = [edge_trace, mid_trace]
    node_types = set(d.get("type", "unknown") for _, d in sub_G.nodes(data=True))

    for ntype in sorted(node_types):
        nx_list = []
        ny_list = []
        hover_texts = []
        marker_colors = []
        marker_sizes = []
        border_widths = []
        border_colors = []

        for node_id, d in sub_G.nodes(data=True):
            if d.get("type", "unknown") != ntype:
                continue
            if node_id not in pos:
                continue

            x, y = pos[node_id]
            nx_list.append(x)
            ny_list.append(y)

            is_center = (node_id == account_id)
            color = NODE_COLORS.get(ntype, "#64748b")
            base_size = NODE_SIZES.get(ntype, 16)

            if is_center:
                marker_colors.append("#0f766e")
                marker_sizes.append(base_size + 12)
                border_widths.append(4)
                border_colors.append("#f59e0b")  # Gold border for central account
            elif d.get("flagged"):
                marker_colors.append(color)
                marker_sizes.append(base_size + 4)
                border_widths.append(2.5)
                border_colors.append("#dc2626")
            else:
                marker_colors.append(color)
                marker_sizes.append(base_size)
                border_widths.append(1.5)
                border_colors.append("#ffffff")

            # Rich hover label
            lines = [f"<b>{node_id}</b> ({ntype.upper()})"]
            if is_center:
                lines.append("⭐ <i>SELECTED CENTRAL ACCOUNT</i>")
            if "name" in d:
                lines.append(f"Name: {d['name']}")
            if "balance" in d:
                lines.append(f"Balance: ${d['balance']:,.2f}")
            if "risk_rating" in d:
                lines.append(f"Risk Rating: {d['risk_rating']}")
            if "location" in d and d["location"]:
                lines.append(f"Location: {d['location']}")

            hover_texts.append("<br>".join(lines))

        node_trace = go.Scatter(
            x=nx_list,
            y=ny_list,
            mode="markers+text" if ntype in ("account", "customer") else "markers",
            text=[nid if nid == account_id else "" for nid in sub_G.nodes if sub_G.nodes[nid].get("type") == ntype],
            textposition="top center",
            hoverinfo="text",
            hovertext=hover_texts,
            name=ntype.capitalize(),
            marker=dict(
                color=marker_colors,
                size=marker_sizes,
                line=dict(width=border_widths, color=border_colors),
            ),
        )
        traces.append(node_trace)

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(
            text=f"Ego Network: Account <b>{account_id}</b> & Connected Entities ({sub_G.number_of_nodes()} Nodes, {sub_G.number_of_edges()} Edges)",
            font=dict(size=15, color="#0f172a"),
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        height=520,
    )

    return fig


def create_pyvis_network_html(
    G: nx.MultiDiGraph,
    center_account: Optional[str] = None,
    max_hops: int = 1,
    height: str = "560px",
) -> str:
    """Generates an interactive physics-based HTML network visualization using PyVis.
    Nodes are color-coded with badges; edges display transaction amounts, IDs, and timestamps.
    """
    if center_account and center_account in G:
        ego_data = get_account_connected_entities(G, center_account, max_hops)
        render_G = ego_data["subgraph"]
    else:
        render_G = G

    net = Network(
        height=height,
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#0f172a",
    )

    # Physics configuration for smooth repulsive force layout
    net.set_options("""
    {
      "nodes": {
        "font": { "size": 13, "face": "system-ui, sans-serif" },
        "borderWidth": 2
      },
      "edges": {
        "color": { "inherit": false, "color": "#94a3b8", "highlight": "#dc2626" },
        "smooth": { "type": "continuous", "roundness": 0.2 },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.7 } }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -55,
          "centralGravity": 0.015,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 40,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 100 }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "zoomView": true
      }
    }
    """)

    # Add Nodes
    for node_id, d in render_G.nodes(data=True):
        ntype = d.get("type", "unknown")
        color = NODE_COLORS.get(ntype, "#64748b")
        is_center = (node_id == center_account)

        label = node_id
        if "name" in d and d["name"] != node_id:
            label = f"{d['name']}\n({node_id})"

        # HTML hover tooltip
        tooltip_parts = [
            f"<b>{node_id}</b>",
            f"Type: <span style='color:{color}; font-weight:bold;'>{ntype.upper()}</span>",
        ]
        if is_center:
            tooltip_parts.append("<b style='color:#d97706;'>⭐ SELECTED CENTRAL ACCOUNT</b>")
        if "balance" in d:
            tooltip_parts.append(f"Balance: ${d['balance']:,.2f}")
        if "risk_rating" in d:
            tooltip_parts.append(f"Risk Tier: {d['risk_rating']}")
        if "location" in d and d["location"]:
            tooltip_parts.append(f"Location: {d['location']}")
        if "alerts" in d:
            tooltip_parts.append(f"Alerts: {', '.join(d['alerts'])}")

        tooltip = "<br>".join(tooltip_parts)

        # PyVis styling
        size = NODE_SIZES.get(ntype, 16)
        if is_center:
            size += 14
            border_col = "#f59e0b"
            border_w = 4
        elif d.get("flagged"):
            size += 5
            border_col = "#dc2626"
            border_w = 3
        else:
            border_col = "#334155"
            border_w = 1.5

        shape = "dot"
        if ntype == "customer":
            shape = "box"
        elif ntype == "device":
            shape = "diamond"
        elif ntype == "ip":
            shape = "hexagon"
        elif ntype == "merchant":
            shape = "square"

        net.add_node(
            node_id,
            label=label,
            title=tooltip,
            color=dict(
                background=color,
                border=border_col,
                highlight=dict(background="#e11d48", border="#0f172a"),
            ),
            size=size,
            shape=shape,
            borderWidth=border_w,
        )

    # Add Edges (Keeping transaction_id, timestamp, and amount)
    for u, v, k, d in render_G.edges(keys=True, data=True):
        edge_type = d.get("type", "OTHER")
        if edge_type == "TRANSFERRED":
            amt = d.get("amount", 0.0)
            txn_id = d.get("transaction_id", k)
            ts = d.get("timestamp", "")
            channel = d.get("channel", "TRANSFER")

            edge_label = f"${amt:,.0f}"
            edge_title = f"<b>Transaction: {txn_id}</b><br>Amount: ${amt:,.2f}<br>Time: {ts}<br>Channel: {channel}"
            edge_color = "#dc2626" if amt >= 9000 else "#2563eb" if amt >= 4000 else "#64748b"
            edge_width = 3.0 if amt >= 9000 else 1.8
        else:
            edge_label = d.get("label", edge_type)
            edge_title = f"<b>Relationship: {edge_type}</b><br>{d.get('relationship', '')}"
            edge_color = "#94a3b8"
            edge_width = 1.2

        net.add_edge(
            u,
            v,
            label=edge_label,
            title=edge_title,
            color=edge_color,
            width=edge_width,
        )

    return net.generate_html()
