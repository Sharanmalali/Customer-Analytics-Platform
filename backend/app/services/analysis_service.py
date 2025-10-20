from typing import List
import joblib
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from sklearn.preprocessing import StandardScaler, OneHotEncoder 
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
import numpy as np # Needed for array handling
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


# In app/services/analysis_service.py, add this new function

def run_dynamic_segmentation_analysis(db: Session, dataset_id: int, features: List[str], n_clusters: int):
    """
    Performs K-Means clustering on the fly using user-specified features,
    handling numerical scaling and categorical encoding.
    """
    
    # 1. Fetch data for all required columns
    # We fetch the primary key 'id' to save results, plus all requested features.
    cols_to_fetch = ['id'] + [
        f.replace('Annual Income (k$)', 'annual_income').replace('Spending Score (1-100)', 'spending_score') 
        for f in features
    ]
    
    customer_query = db.query(models.CustomerData).filter(models.CustomerData.dataset_id == dataset_id)
    df = pd.read_sql(customer_query.statement, customer_query.session.bind)
    
    if df.empty:
        raise ValueError(f"No customer data found for dataset {dataset_id}.")

    # 2. Rename columns back to original format for clarity if needed, 
    # but the simplest approach is to use the database names (which are simpler)
    # The database names are: 'gender', 'age', 'annual_income', 'spending_score'
    
    # Check if all requested features are available in the dataset
    db_cols = ['gender', 'age', 'annual_income', 'spending_score']
    
    # Ensure all features requested by the user are available in the database format:
    # We must map the user-friendly names (e.g. 'Age') to the database column names (e.g. 'age')
    feature_map = {
        'Gender': 'gender',
        'Age': 'age',
        'Annual Income (k$)': 'annual_income',
        'Spending Score (1-100)': 'spending_score'
    }
    
    # Use the DB column names for the analysis
    analysis_features = [feature_map[f] for f in features if f in feature_map]
    
    # Select only the necessary columns (ID and the features)
    X = df[['id'] + analysis_features].copy()
    
    # 3. Handle Numerical vs. Categorical features
    numerical_features = X[analysis_features].select_dtypes(include=np.number).columns.tolist()
    categorical_features = X[analysis_features].select_dtypes(include=['object']).columns.tolist()

    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            # Scale all numerical features (important for K-Means)
            ('num', StandardScaler(), numerical_features),
            # One-hot encode all categorical features (like Gender)
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ],
        remainder='passthrough' # Keep other columns, though not strictly needed here
    )

    # 4. Fit and Transform the data
    X_processed = preprocessor.fit_transform(X[analysis_features])

    # 5. Run K-Means on the processed data
    kmeans_model_dynamic = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    cluster_labels = kmeans_model_dynamic.fit_predict(X_processed)
    
    # 6. Save the results back to the database
    # The labels are in the same order as the rows in X (and df)
    
    # Update cluster labels in the original DataFrame
    df['cluster_label'] = cluster_labels 
    
    # Update database records in bulk
    for index, row in df.iterrows():
        db.query(models.CustomerData).filter(models.CustomerData.id == row['id'])\
          .update({"cluster_label": int(row['cluster_label'])})
    
    db.commit()

    print(f"Dynamic analysis complete on features: {features}. Cluster labels saved.")
    
    # Return the analysis features and the model for potential visualization metadata
    return {
        "df": df,
        "features": features,
        "n_clusters": n_clusters,
        "cluster_centers": kmeans_model_dynamic.cluster_centers_
    }