import React, { useState } from 'react';
import './App.css'; // We will define styles here

// 1. Define the Cluster Mapping based on your test results
// This maps the arbitrary model number (key) to a meaningful business segment (value)
const CLUSTER_MAPPING = {
  // Cluster IDs confirmed from your testing:
  '4': {
    name: "Cautious/Miserly",
    description: "Low Income, Low Spending. Focus on necessity-based promotions."
  },
  '0': {
    name: "Average/Target",
    description: "Moderate Income, Average Spending. The core base for loyalty programs."
  },
  '1': {
    name: "VIP/Enthusiast",
    description: "High Income, High Spending. Your most valuable customers for exclusive offers."
  },
  // We should also map the other two potential clusters (if k=5, we need 5 labels)
  '2': {
    name: "Low Income, High Spenders",
    description: "Risky but engaged. Often young and impulsive. Market impulsive/trendy items."
  },
  '3': {
    name: "High Income, Low Spenders",
    description: "High potential, but difficult to convert. Focus on value and trust-building offers."
  }
};

const API_ENDPOINT = 'http://127.0.0.1:8000/api/predict-live/';

function PredictionForm() {
  // State variables for form inputs
  const [annualIncome, setAnnualIncome] = useState('');
  const [spendingScore, setSpendingScore] = useState('');
  
  // State variables for the prediction result and its details
  const [prediction, setPrediction] = useState(null);
  const [clusterDetails, setClusterDetails] = useState(null);
  
  // State for UI feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // We will fill the handleSubmit function in Step 3
  const handleSubmit = async (event) => {
    event.preventDefault(); // Stop page reload
    setLoading(true);       // Show loading indicator
    setError(null);         // Clear previous errors
    setPrediction(null);
    setClusterDetails(null);

    // 1. Prepare the payload (FastAPI expects float and the exact keys)
    const payload = {
      annual_income: parseFloat(annualIncome),
      spending_score: parseFloat(spendingScore),
    };
    
    // Simple client-side validation check
    if (isNaN(payload.annual_income) || isNaN(payload.spending_score)) {
      setError("Please ensure both inputs are valid numbers.");
      setLoading(false);
      return;
    }

    try {
      // 2. Send the POST request to your FastAPI endpoint
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // IMPORTANT: Your CORS setup in main.py allows this connection!
        },
        body: JSON.stringify(payload),
      });

      // 3. Handle HTTP errors (e.g., 400, 500)
      if (!response.ok) {
        let errorData = await response.json();
        // Use the detail message provided by FastAPI if available
        throw new Error(errorData.detail || `Server error: Status ${response.status}`);
      }

      // 4. Process the successful JSON response
      const data = await response.json();
      
      // Expected: data = {"predicted_cluster": X}
      const clusterId = String(data.predicted_cluster);

      // 5. Update state for display
      setPrediction(clusterId);
      setClusterDetails(CLUSTER_MAPPING[clusterId] || {
        name: "Unknown Cluster",
        description: "This cluster ID was not mapped. Check the model output."
      });

    } catch (err) {
      console.error("Prediction failed:", err);
      setError(`Failed to connect to the prediction service. Details: ${err.message}`);
    } finally {
      setLoading(false); // Hide loading indicator
    }
  };

  // Helper function to render the result box
  const renderResult = () => {
    if (loading) {
      return <p className="loading-message">Predicting segment...</p>;
    }

    if (error) {
      return <p className="error-message">Error: {error}</p>;
    }

    if (clusterDetails) {
      return (
        <div className="result-card">
          <h2>Segment Prediction Complete!</h2>
          <p className="cluster-id">Customer Segment: **Cluster #{prediction}**</p>
          
          <div className="segment-details">
            <h3>{clusterDetails.name}</h3>
            <p>{clusterDetails.description}</p>
          </div>
          <p className="callout">
            This customer is an ideal candidate for our **{clusterDetails.name}** marketing strategy.
          </p>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div className="container">
      <h1>🛍️ Mall Customer Segment Predictor</h1>
      <p>Enter a customer's Annual Income and Spending Score to instantly classify them into a marketing segment.</p>
      
      <form onSubmit={handleSubmit} className="prediction-form">
        
        <div className="input-group">
          <label htmlFor="income">Annual Income (k$):</label>
          <input
            id="income"
            type="number"
            value={annualIncome}
            onChange={(e) => setAnnualIncome(e.target.value)}
            placeholder="e.g., 67.0"
            required
            step="0.1"
          />
        </div>

        <div className="input-group">
          <label htmlFor="score">Spending Score (1-100):</label>
          <input
            id="score"
            type="number"
            value={spendingScore}
            onChange={(e) => setSpendingScore(e.target.value)}
            placeholder="e.g., 56.0"
            required
            min="1"
            max="100"
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Predicting...' : 'Get Customer Segment'}
        </button>
      </form>

      {/* Prediction Result Display */}
      {renderResult()}
    </div>
  );
}

export default PredictionForm;

// In a real React project, you'd use index.js to render App or PredictionForm
// For this guide, assume this is your App.js, and you export it as default