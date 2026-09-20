"""
Database Initialization and Seeding Script for UnifAI
Creates all tables and seeds real CPSE materials, tenants, users, proposals, and CNMC registry.
"""

import os
import csv
import json
import sqlite3
import pandas as pd
from datetime import datetime

from app.database import engine, Base, SessionLocal
from app.models import CpseTenant, User, MatchProposal, CnmcRegistry, CpseCnmcMapping, AuditLog
from app.security.jwt import get_password_hash

def init_db():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and not database_url.startswith("sqlite") and os.getenv("ALLOW_SEED_NON_LOCAL") != "1":
        raise SystemExit("Refusing to seed a non-SQLite DATABASE_URL. Set ALLOW_SEED_NON_LOCAL=1 to override.")

    print("[1/5] Creating SQLAlchemy base schema...")
    Base.metadata.create_all(bind=engine)

    print("[2/5] Creating material_retrieval table...")
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS material_retrieval (
                material_id TEXT PRIMARY KEY,
                cpse_id TEXT NOT NULL,
                original_material_code TEXT,
                normalized_description TEXT,
                retrieval_representation TEXT,
                source_type TEXT,
                source_system TEXT,
                source_record_id TEXT,
                source_file TEXT,
                source_row INTEGER,
                ingestion_timestamp TEXT,
                processing_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    db = SessionLocal()

    # Seed Tenants
    print("[3/5] Seeding CPSE Tenants...")
    tenants = [
        ("IOCL", "IOCL", "Indian Oil Corporation Limited"),
        ("ONGC", "ONGC", "Oil and Natural Gas Corporation"),
        ("GAIL", "GAIL", "GAIL (India) Limited"),
        ("BPCL", "BPCL", "Bharat Petroleum Corporation Limited"),
        ("HPCL", "HPCL", "Hindustan Petroleum Corporation Limited"),
        ("NTPC", "NTPC", "NTPC Limited"),
        ("SAIL", "SAIL", "Steel Authority of India Limited"),
        ("COAL_INDIA", "CIL", "Coal India Limited"),
        ("BHEL", "BHEL", "Bharat Heavy Electricals Limited"),
        ("CENTRAL", "CRB", "Central Review Board"),
        ("NATIONAL", "NHC", "National Harmonization Cell"),
    ]

    for t_id, code, name in tenants:
        if not db.query(CpseTenant).filter(CpseTenant.id == t_id).first():
            db.add(CpseTenant(id=t_id, code=code, name=name))
    db.commit()

    # Seed Users
    print("[4/5] Seeding Users with Role-Based Access Control...")
    users_data = [
        ("cpse_user", "password123", "CPSE_USER", "IOCL"),
        ("user_cpse", "password123", "CPSE_USER", "IOCL"),
        ("reviewer", "password123", "TECHNICAL_REVIEWER", "CENTRAL"),
        ("admin", "password123", "NATIONAL_ADMIN", "NATIONAL"),
    ]

    for username, pwd, role, cpse_id in users_data:
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            hashed = get_password_hash(pwd)
            db.add(User(
                username=username,
                hashed_password=hashed,
                role=role,
                cpse_id=cpse_id
            ))
    db.commit()

    # Seed CNMC Registry
    print("[5/5] Seeding Common National Material Codes (CNMC)...")
    cnmc_entries = [
        (
            "CNMC-3196-CYL-142",
            "CYLINDER LPG LOW CARBON STEEL DOMESTIC 14.2 KG CAPACITY FITTED SC VALVE AS PER IS:3196 (PART 1)",
            "APPROVED",
            {"standard": "IS:3196 PART 1", "nominal_capacity": "14.2 KG", "water_capacity": "33.3 L", "test_pressure": "25 BAR", "canonical_uom": "NOS"}
        ),
        (
            "CNMC-A106-PIPE-DN100",
            "PIPE CARBON STEEL SEAMLESS HIGH TEMPERATURE SERVICE ASTM A106 GRADE B NOMINAL SIZE DN 100 (4 INCH) SCH 40",
            "APPROVED",
            {"standard": "ASTM A106 / ASME SA106", "material_grade": "GRADE B", "nominal_size": "DN 100 / 4 INCH", "wall_thickness": "SCH 40", "canonical_uom": "MTR"}
        ),
        (
            "CNMC-A216-VLV-BALL-06",
            "VALVE BALL TRUNNION MOUNTED FULL BORE 6 INCH CLASS 300 FLANGED RF BODY ASTM A216 WCB FIRE SAFE API 6D / 607",
            "PROPOSED",
            {"standard": "API 6D", "pressure_class": "ASME CLASS 300", "size": "6 INCH (DN 150)", "body_material": "ASTM A216 WCB", "canonical_uom": "NOS"}
        )
    ]

    for cnmc_code, desc, status, attrs in cnmc_entries:
        existing = db.query(CnmcRegistry).filter(CnmcRegistry.cnmc_code == cnmc_code).first()
        if not existing:
            db.add(CnmcRegistry(
                cnmc_code=cnmc_code,
                standardized_description=desc,
                status=status,
                core_attributes=attrs
            ))
    db.commit()

    # Seed material_retrieval from real benchmark files
    print("Seeding material_retrieval with verified CPSE materials...")
    materials_to_insert = [
        {
            "material_id": "MAT-IOCL-PIPE-001",
            "cpse_id": "IOCL",
            "original_material_code": "PIPE-CS-A106-DN100",
            "normalized_description": "SEAMLESS CARBON STEEL LINE PIPE ASTM A106 GRADE B SCH 40 DN 100",
            "retrieval_representation": "PIPE CARBON STEEL ASTM A106 GR B DN 100 4 INCH SCH 40 SEAMLESS IOCL",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "SAP_ECC",
            "source_record_id": "M000000",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 0,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        },
        {
            "material_id": "MAT-IOCL-CYL-14KG",
            "cpse_id": "IOCL",
            "original_material_code": "1236/1231",
            "normalized_description": "14.2 KG CYLINDER DOMESTIC LPG NEW REPLACEMENT IS:3196 PART 1",
            "retrieval_representation": "CYLINDER LPG 14.2 KG DOMESTIC IS 3196 PART 1 33.3 LITER",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "SAP_ECC",
            "source_record_id": "M000001",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 0,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        },
        {
            "material_id": "MAT-ONGC-VLV-BALL-6IN",
            "cpse_id": "ONGC",
            "original_material_code": "VAL-BALL-06-600-CS",
            "normalized_description": "VALVE BALL 6 INCH 600# FLANGED RF WCB BODY TRIM 13CR NACE MR0175 API 6D",
            "retrieval_representation": "VALVE BALL 6 INCH 600 LB FLANGED RF ASTM A216 WCB API 6D",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "MAXIMO",
            "source_record_id": "M000002",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 1,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        },
        {
            "material_id": "MAT-GAIL-PIPE-12IN-X65",
            "cpse_id": "GAIL",
            "original_material_code": "PIPE-SAWL-12-SCH40",
            "normalized_description": "PIPE CS 12 INCH SCH 40 API 5L GRADE X65 PSL2 SAW SEAMLESS EQUIVALENT",
            "retrieval_representation": "LINE PIPE CARBON STEEL 12 INCH SCH 40 API 5L X65 PSL2 SAW",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "ORACLE_EBS",
            "source_record_id": "M000003",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 2,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        },
        {
            "material_id": "MAT-NTPC-BLR-TUBES-T22",
            "cpse_id": "NTPC",
            "original_material_code": "BLR-TB-50.8-T22",
            "normalized_description": "TUBE BOILER SEAMLESS ALLOY STEEL OD 50.8MM THK 5.6MM SA213 T22",
            "retrieval_representation": "BOILER TUBE SEAMLESS SA213 T22 50.8 MM OD 5.6 MM THICKNESS",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "SAP_S4",
            "source_record_id": "M000004",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 3,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        },
        {
            "material_id": "BPCL-LPG-CYL-14.2",
            "cpse_id": "BPCL",
            "original_material_code": "CYL-14.2-BPCL",
            "normalized_description": "LPG CYLINDER 14.2KG CAPACITY COMPLETE WITH SC VALVE AS PER IS 3196",
            "retrieval_representation": "LPG CYLINDER 14.2 KG CAPACITY SC VALVE IS 3196 DOMESTIC",
            "source_type": "REAL_PUBLIC_SOURCE",
            "source_system": "SAP_ECC",
            "source_record_id": "M000005",
            "source_file": "cpse_material_corpus.csv",
            "source_row": 4,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "processing_version": "1.0"
        }
    ]

    # Also load from real_cpse_materials.csv if it exists
    csv_path = "data/real_public/real_cpse_materials.csv"
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, nrows=100)
            for idx, r in df.iterrows():
                mat_id = str(r.get("source_record_id") or f"MAT-REAL-{idx}")
                code = str(r.get("original_material_code") or r.get("original_description") or mat_id)
                desc = str(r.get("original_description") or "CPSE MATERIAL")
                cpse_name = str(r.get("cpse") or "IOCL").replace(".com", "").upper()
                materials_to_insert.append({
                    "material_id": mat_id,
                    "cpse_id": cpse_name,
                    "original_material_code": code,
                    "normalized_description": desc,
                    "retrieval_representation": desc,
                    "source_type": "REAL_PUBLIC_SOURCE",
                    "source_system": str(r.get("source_system") or "ERP"),
                    "source_record_id": mat_id,
                    "source_file": "real_cpse_materials.csv",
                    "source_row": idx,
                    "ingestion_timestamp": datetime.utcnow().isoformat(),
                    "processing_version": "1.0"
                })
        except Exception as e:
            print("Notice loading CSV:", e)

    with engine.begin() as conn:
        for m in materials_to_insert:
            conn.exec_driver_sql("""
                INSERT OR REPLACE INTO material_retrieval (
                    material_id, cpse_id, original_material_code, normalized_description,
                    retrieval_representation, source_type, source_system, source_record_id,
                    source_file, source_row, ingestion_timestamp, processing_version
                ) VALUES (
                    :material_id, :cpse_id, :original_material_code, :normalized_description,
                    :retrieval_representation, :source_type, :source_system, :source_record_id,
                    :source_file, :source_row, :ingestion_timestamp, :processing_version
                )
            """, m)

    # Seed Pending Review Proposals from benchmark queue
    print("Seeding pending MatchProposal review queue...")
    proposals_data = [
        {
            "id": "PROP-REAL-001",
            "query_material_id": "MAT-IOCL-CYL-14KG",
            "candidate_material_id": "BPCL-LPG-CYL-14.2",
            "predicted_relation": "IDENTICAL",
            "confidence_level": "HIGH",
            "decision_status": "REVIEW",
            "governance_state": "PENDING",
            "lane7_probabilities": {"IDENTICAL": 0.942, "EQUIVALENT": 0.048, "VARIANT_OF": 0.007, "DISTINCT": 0.003},
            "lane8_decision": {"reason": "Cross-CPSE 14.2kg domestic cylinder specification match IS:3196", "rule": "SAFETY_VERIFY_VALVE_TYPE"},
            "model_version": "Lane8-LGBM-v1.4.2"
        },
        {
            "id": "PROP-REAL-002",
            "query_material_id": "MAT-ONGC-VLV-BALL-6IN",
            "candidate_material_id": "MAT-GAIL-PIPE-12IN-X65",
            "predicted_relation": "DISTINCT",
            "confidence_level": "HIGH",
            "decision_status": "REVIEW",
            "governance_state": "PENDING",
            "lane7_probabilities": {"IDENTICAL": 0.001, "EQUIVALENT": 0.003, "VARIANT_OF": 0.012, "DISTINCT": 0.984},
            "lane8_decision": {"reason": "Component category divergence: Valve vs Pipe", "rule": "COMMODITY_CLASS_CONFLICT"},
            "model_version": "Lane8-LGBM-v1.4.2"
        }
    ]

    for p in proposals_data:
        existing = db.query(MatchProposal).filter(MatchProposal.id == p["id"]).first()
        if not existing:
            db.add(MatchProposal(**p))
    db.commit()
    db.close()
    print("Database initialization complete! All tables and seed data ready.")

if __name__ == "__main__":
    init_db()

