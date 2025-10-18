from sqlalchemy import (
    JSON, Column, Integer, String, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import datetime

# The Base class is the foundation from which all our table models will inherit.
Base = declarative_base()

# --------------------------------------------------------------------
# 1. NEW: Users Table Model
# --------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # This creates a relationship so we can easily access all companies
    # owned by a user. e.g., my_user.companies
    companies = relationship("Company", back_populates="owner", cascade="all, delete-orphan")

# --------------------------------------------------------------------
# 2. MODIFIED: Companies Table Model
# --------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    registration_date = Column(DateTime(timezone=True), server_default=func.now())

    # --- THIS IS THE NEW LINK ---
    # Each company must be owned by one user.
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="companies")
    # --- END OF NEW LINK ---

    datasets = relationship("Dataset", back_populates="company", cascade="all, delete-orphan")

# --------------------------------------------------------------------
# 3. Datasets Table Model (No Changes)
# --------------------------------------------------------------------
class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    data_period_description = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company = relationship("Company", back_populates="datasets")
    customer_data = relationship("CustomerData", back_populates="dataset", cascade="all, delete-orphan")

# --------------------------------------------------------------------
# 4. Customer Data Table Model (No Changes)
# --------------------------------------------------------------------
class CustomerData(Base):
    __tablename__ = "customer_data"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    original_customer_id = Column(Integer)
    gender = Column(String)
    age = Column(Integer)
    annual_income = Column(Integer)
    spending_score = Column(Integer)
    cluster_label = Column(Integer, nullable=True)
    dataset = relationship("Dataset", back_populates="customer_data")

# --------------------------------------------------------------------
# 5. Analysis Jobs Table Model (No Changes)
# --------------------------------------------------------------------
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id = Column(String, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    status = Column(String, index=True, default="queued")
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    dataset = relationship("Dataset")