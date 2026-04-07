"""
Database Models for Loan Sizer SaaS Platform
Multi-tenant architecture with client isolation
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== CLIENT/TENANT MODELS ====================

class Client(Base):
    """A tenant/client organization"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)  # URL-safe identifier
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    status = Column(String(20), default="active")  # active, suspended, trial
    
    # Subscription
    plan = Column(String(50), default="basic")  # basic, professional, enterprise
    monthly_fee = Column(Float, default=500.0)
    trial_ends_at = Column(DateTime)
    
    # Customization
    logo_url = Column(String(500))
    primary_color = Column(String(7), default="#059669")
    email_template_header = Column(Text)
    email_template_footer = Column(Text)
    
    # Email Processing Settings
    email_provider = Column(String(50), default="sendgrid")  # sendgrid, mailgun, ses
    custom_domain = Column(String(255))  # e.g., abclending.com
    sendgrid_api_key = Column(String(255))
    mailgun_api_key = Column(String(255))
    mailgun_domain = Column(String(255))
    
    # Forwarding address
    forwarding_email = Column(String(255))  # e.g., abclending@process.loansizer.com
    
    # Settings
    settings = Column(JSON, default=dict)  # Custom settings per client
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="client", cascade="all, delete-orphan")
    templates = relationship("ExcelTemplate", back_populates="client", cascade="all, delete-orphan")
    applications = relationship("LoanApplication", back_populates="client", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="client", cascade="all, delete-orphan")
    email_logs = relationship("EmailProcessingLog", back_populates="client", cascade="all, delete-orphan")


class User(Base):
    """User account within a client organization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    role = Column(String(50), default="loan_officer")  # admin, loan_officer, viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    
    # Preferences
    notification_email = Column(Boolean, default=True)
    default_rate = Column(Float, default=8.50)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="users")
    applications_processed = relationship("LoanApplication", back_populates="processed_by")
    
    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)
    
    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


# ==================== TEMPLATE MODELS ====================

class ExcelTemplate(Base):
    """Client's uploaded Excel sizer template"""
    __tablename__ = "excel_templates"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # File storage
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64))  # SHA-256 for integrity
    
    # Cell mappings (extracted from file analysis)
    cell_mappings = Column(JSON, default=dict)
    program_sheets = Column(JSON, default=list)
    
    # Validation rules
    validation_rules = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="templates")
    applications = relationship("LoanApplication", back_populates="template")


# ==================== APPLICATION MODELS ====================

class LoanApplication(Base):
    """Loan application record"""
    __tablename__ = "loan_applications"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("excel_templates.id"))
    processed_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Source
    source_type = Column(String(50), default="email")  # email, pdf, manual
    source_email = Column(Text)  # Original email content
    source_pdf_path = Column(String(500))  # Path to uploaded PDF
    
    # Extracted Data
    applicant_email = Column(String(255))
    applicant_name = Column(String(255))
    applicant_phone = Column(String(50))
    
    # Property
    property_address = Column(String(500))
    property_city = Column(String(100))
    property_state = Column(String(10))
    property_zip = Column(String(20))
    property_type = Column(String(50))
    units = Column(Integer)
    
    # Financial
    estimated_value = Column(Float)
    purchase_price = Column(Float)
    loan_amount = Column(Float)
    note_type = Column(String(50))
    interest_rate = Column(Float)
    points_to_lender = Column(Float, default=0)
    
    # Credit
    credit_score_1 = Column(Integer)
    credit_score_2 = Column(Integer)
    credit_score_3 = Column(Integer)
    credit_score_middle = Column(Integer)
    
    # Calculated
    ltv_ratio = Column(Float)
    dscr = Column(Float)
    
    # Processing
    extraction_confidence = Column(Float)
    extraction_method = Column(String(50))  # ai, regex, manual
    missing_fields = Column(JSON, default=list)
    
    # Results
    programs_results = Column(JSON, default=list)
    overall_decision = Column(String(50))  # APPROVE, REJECT, REVIEW
    decision_reason = Column(Text)
    
    # Generated files
    output_excel_path = Column(String(500))
    generated_email_subject = Column(String(500))
    generated_email_body = Column(Text)
    
    # Status
    status = Column(String(50), default="processing")  # processing, review, approved, rejected, sent
    officer_notes = Column(Text)
    sent_at = Column(DateTime)
    
    # Metrics
    processing_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="applications")
    template = relationship("ExcelTemplate", back_populates="applications")
    processed_by = relationship("User", back_populates="applications_processed")
    audit_logs = relationship("AuditLog", back_populates="application", cascade="all, delete-orphan")


# ==================== API & INTEGRATION MODELS ====================

class ApiKey(Base):
    """API keys for client integrations"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    name = Column(String(255))
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(20))  # First 8 chars for identification
    
    scopes = Column(JSON, default=list)  # ['read', 'write', 'admin']
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="api_keys")


class AuditLog(Base):
    """Audit trail for compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    action = Column(String(100), nullable=False)  # created, updated, approved, rejected, sent
    description = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    application = relationship("LoanApplication", back_populates="audit_logs")


class EmailIntegration(Base):
    """Email integration settings (Gmail, Outlook, etc.)"""
    __tablename__ = "email_integrations"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    provider = Column(String(50))  # gmail, outlook, smtp
    email_address = Column(String(255))
    
    # OAuth tokens (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    # IMAP/SMTP settings
    imap_server = Column(String(255))
    imap_port = Column(Integer)
    smtp_server = Column(String(255))
    smtp_port = Column(Integer)
    
    # Monitoring
    monitor_inbox = Column(Boolean, default=False)
    auto_process = Column(Boolean, default=False)  # Auto-process incoming emails
    filter_subject = Column(String(255))  # Only process emails with this in subject
    
    is_active = Column(Boolean, default=True)
    last_check_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailProcessingLog(Base):
    """Log of processed forwarded emails"""
    __tablename__ = "email_processing_logs"
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    application_id = Column(Integer, ForeignKey("loan_applications.id"))
    
    # Email details
    forwarder_email = Column(String(255), nullable=False)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(500))
    original_sender = Column(String(255))  # The applicant's email
    
    # Processing results
    status = Column(String(50), default="processing")  # processing, completed, failed, rejected
    decision = Column(String(50))  # APPROVE, DECLINE, CONDITIONAL
    processing_time_ms = Column(Integer)
    error_message = Column(Text)
    
    # Email delivery
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    email_error = Column(Text)
    
    # Raw data storage (for debugging)
    raw_email_body = Column(Text)
    extracted_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="email_logs")
    user = relationship("User")


# ==================== DATABASE SETUP ====================

def init_db(database_url: str = "sqlite:///./loansizer.db"):
    """Initialize database tables"""
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine

def get_session_factory(engine):
    """Get session factory for database operations"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
