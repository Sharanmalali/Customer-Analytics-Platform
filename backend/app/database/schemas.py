from pydantic import BaseModel, ConfigDict, Field # <--- ADD Field to imports
from typing import List, Optional, Any, Dict
from datetime import datetime

# ====================================================================
# NEW SCHEMAS FOR USER AUTHENTICATION
# ====================================================================

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    # --- THE FIX IS HERE ---
    # We add validation to the password field.
    # It must now be at least 8 characters and no more than 72.
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ====================================================================
# YOUR EXISTING SCHEMAS (Unchanged)
# ====================================================================

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    registration_date: datetime
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class DatasetBase(BaseModel):
    file_name: str
    data_period_description: Optional[str] = None

class DatasetCreate(DatasetBase):
    pass

class CustomerDataBase(BaseModel):
    original_customer_id: int
    gender: str
    age: int
    annual_income: int
    spending_score: int
    cluster_label: Optional[int] = None

class CustomerData(CustomerDataBase):
    id: int
    dataset_id: int
    model_config = ConfigDict(from_attributes=True)

class Dataset(DatasetBase):
    id: int
    company_id: int
    upload_timestamp: datetime
    customer_data: List[CustomerData] = []
    model_config = ConfigDict(from_attributes=True)

class AnalysisRequest(BaseModel):
    analysis_type: str
    parameters: Optional[Dict[str, Any]] = None

class AnalysisJob(BaseModel):
    id: str
    dataset_id: int
    status: str
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# In schemas.py, add this below the other BaseModels

class LivePredictionRequest(BaseModel):
    annual_income: float
    spending_score: float


class DynamicAnalysisRequest(BaseModel):
    """Schema for requesting clustering on arbitrary features from a dataset."""
    dataset_id: int
    features: List[str] # e.g., ["age", "spending_score"]
    n_clusters: int = 5 # Allow user to specify k, default to 5
    # Since we are creating clusters on the fly, we don't need a response_model for the data
    # We will just return a status message.