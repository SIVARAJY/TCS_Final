"""Module for loading, validating, and generating financial crime investigation datasets.
Handles the 7 core CSV entities with column validation, flexible aliasing, and partial-file support.
"""
from __future__ import annotations
import io
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np

# Canonical schemas for the 7 CSV files
FILE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "transactions": {
        "display_name": "Transactions",
        "description": "Financial transfer ledger connecting accounts with amounts and timestamps.",
        "required_columns": [
            "transaction_id",
            "source_account_id",
            "target_account_id",
            "amount",
            "timestamp",
        ],
        "optional_columns": ["currency", "channel", "description", "transaction_type"],
        "aliases": {
            "transaction_id": ["txn_id", "id", "trans_id", "tx_id", "reference_no"],
            "source_account_id": ["source_account", "source", "from_account", "sender_account", "src_acc"],
            "target_account_id": ["target_account", "target", "to_account", "receiver_account", "dest_acc", "beneficiary_acc"],
            "amount": ["amt", "value", "tx_amount", "sum"],
            "timestamp": ["date", "time", "datetime", "txn_time", "created_at", "trans_date"],
            "currency": ["curr", "ccy"],
            "channel": ["txn_channel", "payment_channel", "mode"],
            "description": ["memo", "narrative", "notes", "remark"],
        },
    },
    "customers": {
        "display_name": "Customers",
        "description": "KYC client records containing identity, risk tier, and contact information.",
        "required_columns": [
            "customer_id",
            "name",
        ],
        "optional_columns": ["risk_rating", "tax_id", "dob", "phone", "email", "address", "country"],
        "aliases": {
            "customer_id": ["cust_id", "id", "client_id", "c_id", "party_id"],
            "name": ["full_name", "customer_name", "client_name", "party_name"],
            "risk_rating": ["risk_level", "risk_score", "aml_risk", "kyc_risk"],
            "tax_id": ["ssn", "tin", "pan", "national_id"],
            "dob": ["date_of_birth", "birth_date"],
            "phone": ["phone_number", "mobile", "tel"],
            "email": ["email_address", "mail"],
            "country": ["nationality", "jurisdiction"],
        },
    },
    "accounts": {
        "display_name": "Accounts",
        "description": "Deposit, checking, or crypto accounts mapped to customer owners.",
        "required_columns": [
            "account_id",
            "customer_id",
        ],
        "optional_columns": ["account_type", "balance", "status", "currency", "open_date"],
        "aliases": {
            "account_id": ["acc_id", "id", "account_no", "account_number", "acct_id"],
            "customer_id": ["cust_id", "owner_id", "client_id", "party_id"],
            "account_type": ["type", "acct_type", "product"],
            "balance": ["current_balance", "bal", "available_balance"],
            "status": ["acc_status", "state"],
            "open_date": ["opened_at", "created_date", "creation_date"],
        },
    },
    "beneficiaries": {
        "display_name": "Beneficiaries",
        "description": "Pre-authorized external payee relationships linked to accounts.",
        "required_columns": [
            "beneficiary_id",
            "account_id",
            "beneficiary_account",
        ],
        "optional_columns": ["name", "bank_code", "relationship", "date_added"],
        "aliases": {
            "beneficiary_id": ["id", "bene_id", "payee_id"],
            "account_id": ["source_account_id", "owner_account_id", "acc_id", "customer_id"],
            "beneficiary_account": ["beneficiary_account_id", "target_account", "bene_account", "payee_account"],
            "name": ["beneficiary_name", "payee_name"],
            "bank_code": ["routing_number", "swift_code", "ifsc", "sort_code"],
            "relationship": ["rel_type", "relation"],
            "date_added": ["created_at", "added_at"],
        },
    },
    "merchants": {
        "display_name": "Merchants",
        "description": "Commercial entities and payment endpoints with risk classification.",
        "required_columns": [
            "merchant_id",
            "merchant_name",
        ],
        "optional_columns": ["category", "mcc_code", "risk_level", "country"],
        "aliases": {
            "merchant_id": ["id", "m_id", "mid"],
            "merchant_name": ["name", "business_name", "merchant"],
            "category": ["industry", "business_type", "mcc_desc"],
            "mcc_code": ["mcc", "merchant_category_code"],
            "risk_level": ["risk", "risk_rating", "tier"],
        },
    },
    "device_activity": {
        "display_name": "Device Activity",
        "description": "Digital login sessions, device fingerprints, and IP telemetry.",
        "required_columns": [
            "device_id",
        ],
        "optional_columns": ["customer_id", "account_id", "ip_address", "timestamp", "location", "user_agent"],
        "aliases": {
            "device_id": ["dev_id", "device", "fingerprint", "hardware_id"],
            "customer_id": ["cust_id", "client_id", "user_id"],
            "account_id": ["acc_id", "source_account_id"],
            "ip_address": ["ip", "ip_addr", "network_ip"],
            "timestamp": ["login_time", "time", "date", "created_at"],
            "location": ["geo", "country", "city"],
        },
    },
    "fraud_alerts": {
        "display_name": "Fraud Alerts",
        "description": "Pre-existing rule flags, SAR triggers, and transaction screening alerts.",
        "required_columns": [
            "alert_id",
            "entity_id",
            "alert_type",
        ],
        "optional_columns": ["severity", "timestamp", "description", "status"],
        "aliases": {
            "alert_id": ["id", "flag_id", "case_id"],
            "entity_id": ["account_id", "customer_id", "transaction_id", "target_id", "flagged_entity"],
            "alert_type": ["type", "rule_name", "reason", "alert_name"],
            "severity": ["risk_score", "priority", "level", "urgency"],
            "timestamp": ["created_at", "date", "time", "alert_time"],
        },
    },
}


def normalize_column_names(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    """Map user's column variants to canonical schema column names."""
    col_map: Dict[str, str] = {}
    lower_to_orig = {str(c).strip().lower(): str(c) for c in df.columns}
    aliases = schema.get("aliases", {})

    for canonical, alias_list in aliases.items():
        if canonical.lower() in lower_to_orig:
            col_map[lower_to_orig[canonical.lower()]] = canonical
            continue
        for alias in alias_list:
            if alias.lower() in lower_to_orig:
                col_map[lower_to_orig[alias.lower()]] = canonical
                break

    # Also match direct exact names case-insensitively
    for req in schema.get("required_columns", []) + schema.get("optional_columns", []):
        if req.lower() in lower_to_orig and lower_to_orig[req.lower()] not in col_map:
            col_map[lower_to_orig[req.lower()]] = req

    df_norm = df.rename(columns=col_map).copy()
    return df_norm


def validate_dataframe(df: pd.DataFrame, file_key: str) -> Dict[str, Any]:
    """Validate DataFrame against required schema, check types, compute previews & null stats."""
    if file_key not in FILE_SCHEMAS:
        raise ValueError(f"Unknown file key: {file_key}")

    schema = FILE_SCHEMAS[file_key]
    required = schema["required_columns"]
    present_cols = list(df.columns)

    missing_required = [c for c in required if c not in present_cols]
    
    # Special relaxation for device_activity: requires device_id, plus at least customer_id OR account_id
    if file_key == "device_activity":
        missing_required = []
        if "device_id" not in present_cols:
            missing_required.append("device_id")
        if "customer_id" not in present_cols and "account_id" not in present_cols:
            missing_required.append("customer_id or account_id")

    is_valid = len(missing_required) == 0

    # Clean amount column if present
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(
            df["amount"].astype(str).str.replace(r"[^\d.-]", "", regex=True),
            errors="coerce"
        ).fillna(0.0)

    # Clean string ID columns
    id_cols = [c for c in df.columns if c.endswith("_id") or c in ("name", "device_id", "alert_type")]
    for col in id_cols:
        df[col] = df[col].astype(str).str.strip()

    null_counts = df.isnull().sum().to_dict()
    null_percentages = {col: round(cnt / max(len(df), 1) * 100, 1) for col, cnt in null_counts.items()}

    return {
        "file_key": file_key,
        "display_name": schema["display_name"],
        "is_valid": is_valid,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": present_cols,
        "missing_required": missing_required,
        "null_counts": null_counts,
        "null_percentages": null_percentages,
        "duplicate_rows": int(df.duplicated().sum()),
        "sample": df.head(5),
    }


def load_csv(file_buffer, file_key: str) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """Load a CSV file buffer, normalize columns, and return clean DataFrame and validation dict."""
    schema = FILE_SCHEMAS.get(file_key, {})
    try:
        # Support both streamlit UploadedFile and bytes/strings
        if hasattr(file_buffer, "read"):
            if hasattr(file_buffer, "seek"):
                try:
                    file_buffer.seek(0)
                except Exception:
                    pass
            content = file_buffer.read()
            if hasattr(file_buffer, "seek"):
                try:
                    file_buffer.seek(0)
                except Exception:
                    pass
            if isinstance(content, str):
                stream = io.StringIO(content)
            else:
                stream = io.BytesIO(content)
        else:
            stream = file_buffer

        # Try standard UTF-8 first, fallback to latin-1
        try:
            df = pd.read_csv(stream, encoding="utf-8")
        except UnicodeDecodeError:
            if hasattr(stream, "seek"):
                stream.seek(0)
            df = pd.read_csv(stream, encoding="latin-1")

        df = normalize_column_names(df, schema)
        info = validate_dataframe(df, file_key)
        return df, info

    except Exception as e:
        return None, {
            "file_key": file_key,
            "display_name": schema.get("display_name", file_key),
            "is_valid": False,
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "missing_required": [f"Parsing error: {str(e)}"],
            "null_counts": {},
            "null_percentages": {},
            "duplicate_rows": 0,
            "sample": pd.DataFrame(),
        }


def generate_sample_dataset() -> Dict[str, pd.DataFrame]:
    """Generates synthetic multi-entity data with planted financial crime rings.
    Includes:
    1. Mule fan-in/fan-out network
    2. Smurfing / Structuring ring ($9,500-$9,900)
    3. Circular money cycle flow (A -> B -> C -> A)
    4. Shared device syndicate (multiple unrelated customers on 1 device)
    5. High-risk shell merchant funneling
    6. Fraud alerts
    """
    np.random.seed(42)

    # 1. CUSTOMERS
    customers = [
        {"customer_id": "CUS-101", "name": "Alexander Hayes", "risk_rating": "HIGH", "tax_id": "TX-9941", "phone": "+1-555-0199", "email": "alex.hayes@apexgroup.com", "country": "USA"},
        {"customer_id": "CUS-102", "name": "Elena Vance", "risk_rating": "MEDIUM", "tax_id": "TX-1024", "phone": "+1-555-0122", "email": "elena.vance@gmail.com", "country": "USA"},
        {"customer_id": "CUS-103", "name": "Marcus Kane", "risk_rating": "HIGH", "tax_id": "TX-9941", "phone": "+1-555-0199", "email": "marcus.kane@apexgroup.com", "country": "CYP"}, # Reused tax_id & phone with CUS-101
        {"customer_id": "CUS-104", "name": "Sophia Chen", "risk_rating": "LOW", "tax_id": "TX-3412", "phone": "+1-555-0144", "email": "sophia.chen@techcorp.io", "country": "USA"},
        {"customer_id": "CUS-105", "name": "Liam Bennett", "risk_rating": "LOW", "tax_id": "TX-5519", "phone": "+44-20-7946-0912", "email": "liam.b@outlook.co.uk", "country": "GBR"},
        {"customer_id": "CUS-106", "name": "Devin Miller", "risk_rating": "HIGH", "tax_id": "TX-7731", "phone": "+1-555-0177", "email": "syndicate.ops@protonmail.ch", "country": "USA"},
        {"customer_id": "CUS-107", "name": "Chloe Dupont", "risk_rating": "MEDIUM", "tax_id": "TX-9901", "phone": "+33-1-4268-5500", "email": "chloe.dupont@orange.fr", "country": "FRA"},
        {"customer_id": "CUS-108", "name": "Viktor Morozov", "risk_rating": "HIGH", "tax_id": "TX-4402", "phone": "+357-25-884100", "email": "syndicate.ops@protonmail.ch", "country": "CYP"}, # Reused email with CUS-106
        {"customer_id": "CUS-109", "name": "Isabella Rossi", "risk_rating": "LOW", "tax_id": "TX-1188", "phone": "+39-06-6987-1200", "email": "isabella.rossi@libero.it", "country": "ITA"},
        {"customer_id": "CUS-110", "name": "Noah Patel", "risk_rating": "MEDIUM", "tax_id": "TX-6623", "phone": "+1-555-0188", "email": "noah.patel@globalbiz.com", "country": "USA"},
        {"customer_id": "CUS-111", "name": "Aria Stark", "risk_rating": "LOW", "tax_id": "TX-3321", "phone": "+1-555-0133", "email": "aria.stark@winterfell.org", "country": "USA"},
        {"customer_id": "CUS-112", "name": "Lucas Grey", "risk_rating": "HIGH", "tax_id": "TX-5544", "phone": "+507-833-9100", "email": "lucas.grey@panama-advisory.pa", "country": "PAN"},
    ]
    df_customers = pd.DataFrame(customers)

    # 2. ACCOUNTS
    accounts = [
        {"account_id": "ACC-MULE-1", "customer_id": "CUS-101", "account_type": "CHECKING", "balance": 18500.0, "status": "ACTIVE"},
        {"account_id": "ACC-FEED-A", "customer_id": "CUS-102", "account_type": "SAVINGS", "balance": 45000.0, "status": "ACTIVE"},
        {"account_id": "ACC-FEED-B", "customer_id": "CUS-103", "account_type": "CHECKING", "balance": 38000.0, "status": "ACTIVE"},
        {"account_id": "ACC-FEED-C", "customer_id": "CUS-104", "account_type": "CHECKING", "balance": 29000.0, "status": "ACTIVE"},
        {"account_id": "ACC-FEED-D", "customer_id": "CUS-105", "account_type": "SAVINGS", "balance": 31000.0, "status": "ACTIVE"},
        {"account_id": "ACC-OFFSHORE-9", "customer_id": "CUS-108", "account_type": "CHECKING", "balance": 92000.0, "status": "ACTIVE"},
        {"account_id": "ACC-STRUC-1", "customer_id": "CUS-106", "account_type": "BUSINESS", "balance": 64000.0, "status": "ACTIVE"},
        {"account_id": "ACC-STRUC-2", "customer_id": "CUS-106", "account_type": "CHECKING", "balance": 52000.0, "status": "ACTIVE"},
        {"account_id": "ACC-CYCLE-A", "customer_id": "CUS-107", "account_type": "CHECKING", "balance": 22000.0, "status": "ACTIVE"},
        {"account_id": "ACC-CYCLE-B", "customer_id": "CUS-110", "account_type": "BUSINESS", "balance": 28000.0, "status": "ACTIVE"},
        {"account_id": "ACC-CYCLE-C", "customer_id": "CUS-112", "account_type": "SAVINGS", "balance": 34000.0, "status": "ACTIVE"},
        {"account_id": "ACC-DEV-1", "customer_id": "CUS-101", "account_type": "CHECKING", "balance": 12000.0, "status": "ACTIVE"},
        {"account_id": "ACC-DEV-2", "customer_id": "CUS-103", "account_type": "CHECKING", "balance": 14500.0, "status": "ACTIVE"},
        {"account_id": "ACC-DEV-3", "customer_id": "CUS-108", "account_type": "CHECKING", "balance": 19000.0, "status": "ACTIVE"},
        {"account_id": "ACC-NORM-1", "customer_id": "CUS-109", "account_type": "SAVINGS", "balance": 15000.0, "status": "ACTIVE"},
        {"account_id": "ACC-NORM-2", "customer_id": "CUS-111", "account_type": "CHECKING", "balance": 8500.0, "status": "ACTIVE"},
    ]
    df_accounts = pd.DataFrame(accounts)

    # 3. TRANSACTIONS
    txns = [
        # Mule Fan-In (Multiple accounts feed ACC-MULE-1 in quick succession)
        {"transaction_id": "TXN-001", "source_account_id": "ACC-FEED-A", "target_account_id": "ACC-MULE-1", "amount": 4850.0, "timestamp": "2026-10-28 09:15:00", "channel": "WIRE"},
        {"transaction_id": "TXN-002", "source_account_id": "ACC-FEED-B", "target_account_id": "ACC-MULE-1", "amount": 4900.0, "timestamp": "2026-10-28 09:40:00", "channel": "WIRE"},
        {"transaction_id": "TXN-003", "source_account_id": "ACC-FEED-C", "target_account_id": "ACC-MULE-1", "amount": 4800.0, "timestamp": "2026-10-28 10:10:00", "channel": "P2P"},
        {"transaction_id": "TXN-004", "source_account_id": "ACC-FEED-D", "target_account_id": "ACC-MULE-1", "amount": 4950.0, "timestamp": "2026-10-28 10:35:00", "channel": "WIRE"},
        # Rapid Fan-Out (Mule disperses funds offshore within 1 hour)
        {"transaction_id": "TXN-005", "source_account_id": "ACC-MULE-1", "target_account_id": "ACC-OFFSHORE-9", "amount": 19200.0, "timestamp": "2026-10-28 11:20:00", "channel": "SWIFT"},

        # Structuring / Smurfing (Amounts intentionally just below $10,000 threshold)
        {"transaction_id": "TXN-006", "source_account_id": "ACC-STRUC-1", "target_account_id": "ACC-STRUC-2", "amount": 9650.0, "timestamp": "2026-10-29 08:30:00", "channel": "INTERNAL"},
        {"transaction_id": "TXN-007", "source_account_id": "ACC-STRUC-1", "target_account_id": "ACC-STRUC-2", "amount": 9800.0, "timestamp": "2026-10-29 11:15:00", "channel": "INTERNAL"},
        {"transaction_id": "TXN-008", "source_account_id": "ACC-STRUC-1", "target_account_id": "ACC-STRUC-2", "amount": 9500.0, "timestamp": "2026-10-29 14:45:00", "channel": "INTERNAL"},
        {"transaction_id": "TXN-009", "source_account_id": "ACC-STRUC-1", "target_account_id": "ACC-STRUC-2", "amount": 9900.0, "timestamp": "2026-10-29 17:05:00", "channel": "INTERNAL"},

        # Circular Flow Cycle (ACC-CYCLE-A -> ACC-CYCLE-B -> ACC-CYCLE-C -> ACC-CYCLE-A)
        {"transaction_id": "TXN-010", "source_account_id": "ACC-CYCLE-A", "target_account_id": "ACC-CYCLE-B", "amount": 16000.0, "timestamp": "2026-10-30 09:00:00", "channel": "WIRE"},
        {"transaction_id": "TXN-011", "source_account_id": "ACC-CYCLE-B", "target_account_id": "ACC-CYCLE-C", "amount": 15800.0, "timestamp": "2026-10-30 11:00:00", "channel": "WIRE"},
        {"transaction_id": "TXN-012", "source_account_id": "ACC-CYCLE-C", "target_account_id": "ACC-CYCLE-A", "amount": 15650.0, "timestamp": "2026-10-30 14:00:00", "channel": "WIRE"},

        # Merchant Funneling to High-Risk Shell Entity
        {"transaction_id": "TXN-013", "source_account_id": "ACC-OFFSHORE-9", "target_account_id": "MERCH-CRYPTO-1", "amount": 25000.0, "timestamp": "2026-10-28 14:30:00", "channel": "CARD"},
        {"transaction_id": "TXN-014", "source_account_id": "ACC-STRUC-2", "target_account_id": "MERCH-SHELL-2", "amount": 38000.0, "timestamp": "2026-10-30 16:00:00", "channel": "WIRE"},

        # Benign / Routine Traffic & Dispersal
        {"transaction_id": "TXN-015", "source_account_id": "ACC-NORM-1", "target_account_id": "MERCH-RETAIL-1", "amount": 124.50, "timestamp": "2026-10-29 12:00:00", "channel": "CARD"},
        {"transaction_id": "TXN-016", "source_account_id": "ACC-NORM-2", "target_account_id": "ACC-NORM-1", "amount": 450.0, "timestamp": "2026-10-29 18:20:00", "channel": "P2P"},
        {"transaction_id": "TXN-017", "source_account_id": "ACC-FEED-C", "target_account_id": "MERCH-RETAIL-2", "amount": 89.90, "timestamp": "2026-10-30 10:15:00", "channel": "CARD"},
        {"transaction_id": "TXN-018", "source_account_id": "ACC-FEED-A", "target_account_id": "ACC-NORM-1", "amount": 3500.0, "timestamp": "2026-10-28 12:00:00", "channel": "WIRE"},
        {"transaction_id": "TXN-019", "source_account_id": "ACC-FEED-A", "target_account_id": "ACC-NORM-2", "amount": 4200.0, "timestamp": "2026-10-28 12:15:00", "channel": "WIRE"},
    ]
    df_txns = pd.DataFrame(txns)

    # 4. BENEFICIARIES
    beneficiaries = [
        {"beneficiary_id": "BEN-01", "account_id": "ACC-MULE-1", "beneficiary_account": "ACC-OFFSHORE-9", "name": "Global Shield Holdings", "relationship": "VENDOR"},
        {"beneficiary_id": "BEN-02", "account_id": "ACC-CYCLE-A", "beneficiary_account": "ACC-CYCLE-B", "name": "Apex Consulting", "relationship": "AFFILIATE"},
        {"beneficiary_id": "BEN-03", "account_id": "ACC-CYCLE-B", "beneficiary_account": "ACC-CYCLE-C", "name": "Zenith Ventures", "relationship": "SUBSIDIARY"},
        {"beneficiary_id": "BEN-04", "account_id": "ACC-CYCLE-C", "beneficiary_account": "ACC-CYCLE-A", "name": "Apex Consulting", "relationship": "PARTNER"},
        {"beneficiary_id": "BEN-05", "account_id": "ACC-NORM-2", "beneficiary_account": "ACC-NORM-1", "name": "Isabella Rossi", "relationship": "FAMILY"},
        {"beneficiary_id": "BEN-06", "account_id": "ACC-FEED-A", "beneficiary_account": "ACC-OFFSHORE-9", "name": "Global Shield Holdings", "relationship": "VENDOR"},
        {"beneficiary_id": "BEN-07", "account_id": "ACC-FEED-B", "beneficiary_account": "ACC-OFFSHORE-9", "name": "Global Shield Holdings", "relationship": "VENDOR"},
    ]
    df_beneficiaries = pd.DataFrame(beneficiaries)

    # 5. MERCHANTS
    merchants = [
        {"merchant_id": "MERCH-CRYPTO-1", "merchant_name": "Nexus Peer Crypto Exchange", "category": "Cryptocurrency Exchange", "risk_level": "HIGH", "country": "CYP"},
        {"merchant_id": "MERCH-SHELL-2", "merchant_name": "Pan-Atlantic Consulting LLC", "category": "Corporate Consulting / Shell", "risk_level": "CRITICAL", "country": "PAN"},
        {"merchant_id": "MERCH-RETAIL-1", "merchant_name": "Metro Grocery Superstore", "category": "Supermarkets", "risk_level": "LOW", "country": "USA"},
        {"merchant_id": "MERCH-RETAIL-2", "merchant_name": "AeroTravel Direct", "category": "Airlines & Travel", "risk_level": "LOW", "country": "USA"},
    ]
    df_merchants = pd.DataFrame(merchants)

    # 6. DEVICE ACTIVITY (Shared Device Syndicate & New Device Detection)
    device_activity = [
        {"device_id": "DEV-SUSP-99", "customer_id": "CUS-101", "account_id": "ACC-DEV-1", "ip_address": "194.180.174.5", "location": "Limassol, Cyprus", "timestamp": "2026-10-28 08:50:00"},
        {"device_id": "DEV-SUSP-99", "customer_id": "CUS-103", "account_id": "ACC-DEV-2", "ip_address": "194.180.174.5", "location": "Limassol, Cyprus", "timestamp": "2026-10-28 09:05:00"},
        {"device_id": "DEV-SUSP-99", "customer_id": "CUS-108", "account_id": "ACC-DEV-3", "ip_address": "194.180.174.5", "location": "Limassol, Cyprus", "timestamp": "2026-10-28 11:10:00"},
        {"device_id": "DEV-NORM-1", "customer_id": "CUS-104", "account_id": "ACC-FEED-C", "ip_address": "66.249.70.1", "location": "New York, USA", "timestamp": "2026-10-28 10:05:00"},
        {"device_id": "DEV-NEW-88", "customer_id": "CUS-104", "account_id": "ACC-FEED-C", "ip_address": "198.51.100.12", "location": "Miami, USA", "timestamp": "2026-10-30 16:45:00"}, # Triggers D04 New Device
        {"device_id": "DEV-NORM-2", "customer_id": "CUS-109", "account_id": "ACC-NORM-1", "ip_address": "82.165.197.1", "location": "Rome, Italy", "timestamp": "2026-10-29 11:55:00"},
    ]
    df_device = pd.DataFrame(device_activity)

    # 7. FRAUD ALERTS
    fraud_alerts = [
        {"alert_id": "ALT-901", "entity_id": "ACC-MULE-1", "alert_type": "Rapid Velocity Inflow", "severity": "HIGH", "timestamp": "2026-10-28 10:45:00", "description": "4 distinct external wires received within 80 minutes"},
        {"alert_id": "ALT-902", "entity_id": "ACC-OFFSHORE-9", "alert_type": "High-Risk Jurisdiction Hop", "severity": "CRITICAL", "timestamp": "2026-10-28 11:35:00", "description": "Immediate wire forwarding to Cyprus offshore endpoint"},
        {"alert_id": "ALT-903", "entity_id": "CUS-106", "alert_type": "CTR Threshold Structuring", "severity": "HIGH", "timestamp": "2026-10-29 17:30:00", "description": "4 transactions totaling $38,850 all within 5% below $10k reporting limit"},
    ]
    df_alerts = pd.DataFrame(fraud_alerts)

    return {
        "transactions": df_txns,
        "customers": df_customers,
        "accounts": df_accounts,
        "beneficiaries": df_beneficiaries,
        "merchants": df_merchants,
        "device_activity": df_device,
        "fraud_alerts": df_alerts,
    }
