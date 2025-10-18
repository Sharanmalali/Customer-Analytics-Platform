from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd
from typing import Optional, List
import uuid
from datetime import datetime

# --- Import database and schema components ---
from app.database import schemas, models
from app.database.database import get_db, SessionLocal 

# --- IMPORT YOUR ANALYSIS SERVICE ---
# This is the crucial link to your ML logic
from app.services import analysis_service
from app import auth

router = APIRouter()

# --- THE REAL BACKGROUND TASK ---
# This function replaces the old placeholder. It calls your actual analysis service.
def run_background_analysis(job_id: str, dataset_id: int):
    """
    This function runs in the background and performs the following steps:
    1. Creates its own database session.
    2. Updates the job status to "running".
    3. Calls the real ML analysis service to perform clustering.
    4. Calculates summary results from the analysis.
    5. Updates the job status to "completed" and saves the results.
    6. Handles any errors and updates the status to "failed".
    7. Ensures the database session is always closed.
    """
    db: Session = SessionLocal()
    try:
        print(f"[{job_id}] Background task started for dataset {dataset_id}...")
        job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
        if not job:
            print(f"[{job_id}] FATAL ERROR: Job not found in database.")
            return

        # 1. Update status to "running"
        job.status = "running"
        db.commit()

        # 2. --- CALL THE REAL ANALYSIS LOGIC ---
        # This is where we use the service you provided.
        results_df = analysis_service.run_segmentation_analysis(db=db, dataset_id=dataset_id)
        
        # 3. --- CALCULATE AND PREPARE RESULTS TO SAVE ---
        # We'll create a simple JSON summary from the results DataFrame.
        cluster_summary = results_df['cluster_label'].value_counts().to_dict()
        analysis_results = {
            "summary": f"Segmentation analysis complete for dataset {dataset_id}.",
            "total_records_processed": len(results_df),
            "cluster_distribution": {str(k): v for k, v in cluster_summary.items()} # Convert keys to string for JSON
        }
        
        # 4. Update job with final status and results
        job.status = "completed"
        job.results = analysis_results
        job.finished_at = datetime.utcnow()
        db.commit()
        print(f"[{job_id}] Analysis finished successfully and results have been saved.")

    except Exception as e:
        # 5. Handle any errors during the analysis
        print(f"[{job_id}] Analysis failed with an error: {e}")
        if 'job' in locals() and job:
            job.status = "failed"
            job.results = {"error": str(e)}
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        # 6. Always close the database session
        db.close()

# --------------------------------------------------------------------
# Endpoint 1: Register a New Company (No Changes)
# --------------------------------------------------------------------
@router.post("/companies/", response_model=schemas.Company)
def create_company(
    company: schemas.CompanyCreate, 
    db: Session = Depends(get_db),
    # This dependency correctly secures the endpoint
    current_user: models.User = Depends(auth.get_current_user)
):
    """Creates a new company and links it to the logged-in user."""
    db_company = db.query(models.Company).filter(models.Company.name == company.name).first()
    if db_company:
        raise HTTPException(status_code=400, detail=f"Company '{company.name}' already registered.")
    
    # This logic is correct
    new_company = models.Company(name=company.name, user_id=current_user.id)
    
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company
# --------------------------------------------------------------------
# Endpoint 2: Upload Customer Data CSV for a Company (No Changes)
# --------------------------------------------------------------------
@router.post("/companies/{company_id}/datasets/", response_model=schemas.Dataset)
def upload_dataset_for_company(
    company_id: int, file: UploadFile = File(...), description: Optional[str] = Form(None), db: Session = Depends(get_db)
):
    db_company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found.")
    new_dataset = models.Dataset(company_id=company_id, file_name=file.filename, data_period_description=description)
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    try:
        chunk_iter = pd.read_csv(file.file, chunksize=1000)
        for chunk in chunk_iter:
            chunk.rename(columns={'CustomerID':'original_customer_id','Gender':'gender','Age':'age','Annual Income (k$)':'annual_income','Spending Score (1-100)':'spending_score'}, inplace=True)
            chunk['dataset_id'] = new_dataset.id
            db.bulk_insert_mappings(models.CustomerData, chunk.to_dict(orient="records"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV file: {e}")
    return new_dataset

# --------------------------------------------------------------------
# Endpoint 3: Run a New Analysis (UPDATED)
# --------------------------------------------------------------------
@router.post("/companies/{company_id}/datasets/{dataset_id}/run-analysis/", response_model=schemas.AnalysisJob)
def run_analysis_on_dataset(
    company_id: int, dataset_id: int, request: schemas.AnalysisRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id, models.Dataset.company_id == company_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found for company {company_id}.")

    new_job = models.AnalysisJob(id=f"job-{uuid.uuid4()}", dataset_id=dataset_id, status="queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    background_tasks.add_task(run_background_analysis, job_id=new_job.id, dataset_id=dataset_id)
    return new_job

# --------------------------------------------------------------------
# Endpoint 4: Get Job Status and Results (FINAL)
# --------------------------------------------------------------------
@router.get("/analysis-jobs/{job_id}", response_model=schemas.AnalysisJob)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job
