from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import datetime
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

# Note: We explicitly DO NOT model `material_retrieval` here to avoid accidental migrations
# modifying the Lane 5 vector store. We use String (TEXT) for material_id foreign keys, 
# because material_retrieval.material_id is a TEXT column.

class CpseTenant(Base):
    __tablename__ = "cpse_tenant"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="cpse")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    cpse_id = Column(String, ForeignKey("cpse_tenant.id"), nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    auth_provider = Column(String, default="local") # "local" or "google"
    avatar_url = Column(String, nullable=True)
    role = Column(
        SQLEnum('CPSE_USER', 'TECHNICAL_REVIEWER', 'CPSE_ADMIN', 'NATIONAL_ADMIN', 'AUDITOR', name="user_role_enum"),
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cpse = relationship("CpseTenant", back_populates="users")
    identities = relationship("ExternalIdentity", back_populates="user", cascade="all, delete-orphan")

class ExternalIdentity(Base):
    __tablename__ = "external_identity"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_external_identity_provider_id"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    provider = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="identities")

class MatchProposal(Base):
    __tablename__ = "match_proposal"

    id = Column(String, primary_key=True, default=generate_uuid)
    
    # These reference the existing material_retrieval.material_id which is TEXT
    query_material_id = Column(String, nullable=False, index=True)
    candidate_material_id = Column(String, nullable=False, index=True)

    predicted_relation = Column(
        SQLEnum('IDENTICAL', 'EQUIVALENT', 'VARIANT_OF', 'DISTINCT', 'UNDETERMINED', name="relation_enum"),
        nullable=False
    )
    confidence_level = Column(String, nullable=False) # e.g. HIGH, MEDIUM, LOW, REVIEW
    decision_status = Column(
        SQLEnum('PROPOSED', 'REVIEW', name="decision_status_enum"),
        nullable=False
    )
    
    governance_state = Column(
        SQLEnum('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED', name="governance_state_enum"),
        default='PENDING',
        nullable=False
    )

    lane7_probabilities = Column(JSON, nullable=True)
    lane8_decision = Column(JSON, nullable=True)
    model_version = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    mappings = relationship("CpseCnmcMapping", back_populates="match_proposal")

class CnmcRegistry(Base):
    __tablename__ = "cnmc_registry"

    id = Column(String, primary_key=True, default=generate_uuid)
    cnmc_code = Column(String, unique=True, index=True, nullable=False) # e.g., CNMC-100234
    standardized_description = Column(Text, nullable=False)
    core_attributes = Column(JSON, nullable=True)
    status = Column(
        SQLEnum('PROPOSED', 'APPROVED', name="cnmc_status_enum"),
        default='PROPOSED',
        nullable=False
    )
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    mappings = relationship("CpseCnmcMapping", back_populates="cnmc")

class CpseCnmcMapping(Base):
    __tablename__ = "cpse_cnmc_mapping"

    id = Column(String, primary_key=True, default=generate_uuid)
    cpse_material_id = Column(String, nullable=False, index=True) # References material_retrieval
    cnmc_id = Column(String, ForeignKey("cnmc_registry.id"), nullable=False)
    
    relationship_type = Column(
        SQLEnum('IDENTICAL', 'EQUIVALENT', name="cnmc_mapping_relation_enum"),
        nullable=False
    )
    match_proposal_id = Column(String, ForeignKey("match_proposal.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cnmc = relationship("CnmcRegistry", back_populates="mappings")
    match_proposal = relationship("MatchProposal", back_populates="mappings")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    entity_name = Column(String, nullable=False, index=True) # MATCH_PROPOSAL, CPSE_CNMC_MAPPING
    entity_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, nullable=True) # Nullable, system/AI
    action = Column(String, nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
