import joblib
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import models

# --- 1. Load the ML Models at Startup ---
BASE_DIR = Path(__file__).resolve().parent.parent
ML_MODEL_DIR = BASE_DIR / "ml_models"

try:
    kmeans_model = joblib.load(ML_MODEL_DIR / "kmeans_model.joblib")
    scaler = joblib.load(ML_MODEL_DIR / "scaler.joblib")
    print("ML models loaded successfully.")
except FileNotFoundError:
    print("ML models not found! Please run the notebook to create them.")
    kmeans_model = None
    scaler = None

# --- 2. The Core Analysis Function ---
def run_segmentation_analysis(db: Session, dataset_id: int):
    """
    This is the main function that performs the K-Means clustering.
    - Fetches raw customer data for a given dataset.
    - Uses the pre-trained model to predict clusters.
    - Saves the cluster labels back to the database.
    """
    if not kmeans_model or not scaler:
        raise RuntimeError("ML models are not available. Cannot run analysis.")

    # Step A: Fetch the raw data from the database
    customer_query = db.query(models.CustomerData).filter(models.CustomerData.dataset_id == dataset_id)
    df = pd.read_sql(customer_query.statement, customer_query.session.bind)
    
    if df.empty:
        raise ValueError("No customer data found for this dataset to analyze.")

    # --- THE FIX IS HERE ---
    # The model expects the original column names from the CSV file.
    # We rename the columns from our database format ('annual_income')
    # back to the format the model was trained on ('Annual Income (k$)').
    df_for_model = df.rename(columns={
        'annual_income': 'Annual Income (k$)',
        'spending_score': 'Spending Score (1-100)'
    })

    # Now, we use the original feature names that the model expects.
    features = ['Annual Income (k$)', 'Spending Score (1-100)']
    X = df_for_model[features]
    # --- END OF FIX ---

    X_scaled = scaler.transform(X)

    # Step C: Use the loaded model to predict the clusters
    cluster_labels = kmeans_model.predict(X_scaled)
    df['cluster_label'] = cluster_labels # Add the new labels back to our original DataFrame

    # Step D: Save the results back to the database
    for index, row in df.iterrows():
        db.query(models.CustomerData).filter(models.CustomerData.id == row['id'])\
          .update({"cluster_label": int(row['cluster_label'])})
    
    db.commit()

    print(f"Analysis complete. Cluster labels saved for dataset_id: {dataset_id}")
    
    # Return the DataFrame with results, which is useful for the API response.
    return df

def predict_single_customer(income: float, score: float) -> int:
    """
    Takes a single customer's income and score, scales them, 
    and returns the predicted cluster ID.
    """
    if not kmeans_model or not scaler:
        raise RuntimeError("ML models are not available. Cannot run prediction.")

    # 1. Create a DataFrame for a single input
    data_for_prediction = pd.DataFrame([{
        # Use the exact column names the model was trained on
        'Annual Income (k$)': income, 
        'Spending Score (1-100)': score
    }])
    
    # 2. Scale the data using the *pre-loaded* scaler
    X_scaled = scaler.transform(data_for_prediction)
    
    # 3. Predict the cluster
    cluster_label = kmeans_model.predict(X_scaled)[0]
    
    return cluster_label