import React, { useState, useEffect } from 'react';
import './App.css'; 

// --- 1. CHART.JS IMPORTS ---
import { Scatter } from 'react-chartjs-2';
import { 
  Chart as ChartJS, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Tooltip, 
  Legend 
} from 'chart.js';

// Register the necessary components for Chart.js
ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Legend);
// -----------------------------

const CLUSTER_MAPPING = {
  '4': { name: "Cautious/Miserly", description: "Low Income, Low Spending.", color: 'rgba(255, 99, 132, 0.7)' }, // Red
  '0': { name: "Average/Target", description: "Moderate Income, Average Spending.", color: 'rgba(54, 162, 235, 0.7)' }, // Blue
  '1': { name: "VIP/Enthusiast", description: "High Income, High Spending.", color: 'rgba(75, 192, 192, 0.7)' }, // Teal
  '2': { name: "Low Income, High Spenders", description: "Risky but engaged.", color: 'rgba(255, 206, 86, 0.7)' }, // Yellow
  '3': { name: "High Income, Low Spenders", description: "High potential, difficult to convert.", color: 'rgba(153, 102, 255, 0.7)' } // Purple
};

// --- CONFIGURATION CONSTANTS ---
const API_BASE_URL = 'http://127.0.0.1:8000/api/';
const PREDICT_LIVE_ENDPOINT = API_BASE_URL + 'predict-live/';
// !!! IMPORTANT: REPLACE THIS WITH YOUR VALID dataset_id from the backend test !!!
const CLUSTER_DATA_ENDPOINT = API_BASE_URL + 'datasets/3/clustered-data/'; 
// For example: const CLUSTER_DATA_ENDPOINT = API_BASE_URL + 'datasets/12/clustered-data/'; 
// -----------------------------

function PredictionForm() {
  // Form State
  const [annualIncome, setAnnualIncome] = useState('');
  const [spendingScore, setSpendingScore] = useState('');
  
  // Prediction State
  const [prediction, setPrediction] = useState(null);
  const [clusterDetails, setClusterDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- NEW VISUALIZATION STATE ---
  const [clusteredData, setClusteredData] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState(null);
  // -----------------------------

  // --- NEW: FETCH CLUSTERED HISTORY DATA ON LOAD ---
  useEffect(() => {
    // NOTE: Replace 'YOUR_DATASET_ID' in CLUSTER_DATA_ENDPOINT before running!
    const fetchClusteredData = async () => {
      try {
        const response = await fetch(CLUSTER_DATA_ENDPOINT);
        if (!response.ok) {
          throw new Error(`Failed to fetch history data. Status: ${response.status}`);
        }
        const data = await response.json();
        setClusteredData(data);
        setDataLoading(false);
      } catch (err) {
        console.error("Historical Data Fetch Failed:", err);
        setDataError("Could not load historical clustered data for visualization.");
        setDataLoading(false);
      }
    };

    fetchClusteredData();
  }, []); // Empty dependency array means this runs only once on component mount
  // ----------------------------------------------------

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setPrediction(null);
    setClusterDetails(null);

    const payload = {
      annual_income: parseFloat(annualIncome),
      spending_score: parseFloat(spendingScore),
    };
    
    if (isNaN(payload.annual_income) || isNaN(payload.spending_score)) {
      setError("Please ensure both inputs are valid numbers.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(PREDICT_LIVE_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errorData = await response.json();
        throw new Error(errorData.detail || `Server error: Status ${response.status}`);
      }

      const data = await response.json();
      const clusterId = String(data.predicted_cluster);

      setPrediction(clusterId);
      setClusterDetails(CLUSTER_MAPPING[clusterId] || {
        name: "Unknown Cluster",
        description: "This cluster ID was not mapped."
      });

    } catch (err) {
      console.error("Prediction failed:", err);
      setError(`Failed to connect to the prediction service. Details: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };


  // --- NEW: FUNCTION TO PREPARE DATA FOR CHART.JS ---
  const getChartData = () => {
    const datasets = [];
    const clusters = {}; // Group data by cluster_label

    // 1. Group all historical data
    clusteredData.forEach(customer => {
      const key = String(customer.cluster_label);
      if (!clusters[key]) {
        clusters[key] = [];
      }
      clusters[key].push({
        x: customer.annual_income,
        y: customer.spending_score,
      });
    });

    // 2. Create a dataset for each cluster (for coloring and legend)
    Object.keys(clusters).forEach(clusterId => {
      const clusterInfo = CLUSTER_MAPPING[clusterId] || { name: `Cluster ${clusterId}`, color: '#ccc' };
      datasets.push({
        label: clusterInfo.name,
        data: clusters[clusterId],
        backgroundColor: clusterInfo.color,
        pointRadius: 4,
        hoverRadius: 6,
      });
    });

    // 3. Add the NEW PREDICTION POINT if it exists
    if (prediction && annualIncome && spendingScore) {
      datasets.push({
        label: 'New Prediction',
        data: [{ 
          x: parseFloat(annualIncome), 
          y: parseFloat(spendingScore) 
        }],
        backgroundColor: 'rgba(255, 0, 0, 1)', // Bright Red
        borderColor: 'black',
        borderWidth: 2,
        pointRadius: 10, // Make it large and distinct
        pointStyle: 'star', // Use a star shape
        hoverRadius: 12,
      });
    }

    return { datasets };
  };

  // --- CHART CONFIG OPTIONS ---
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { position: 'bottom' },
      title: { display: true, text: 'Customer Segmentation Map (Income vs. Spending)' },
      tooltip: { 
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
                label += ': ';
            }
            if (context.parsed.x !== null) {
                label += `Income: $${context.parsed.x}k`;
            }
            if (context.parsed.y !== null) {
                label += `, Score: ${context.parsed.y}`;
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: { title: { display: true, text: 'Annual Income (k$)' } },
      y: { title: { display: true, text: 'Spending Score (1-100)' } },
    }
  };


  // Helper function to render the result box and chart
  const renderResult = () => {
    if (loading) {
      return <p className="loading-message">Predicting segment...</p>;
    }

    if (error) {
      return <p className="error-message">Prediction Error: {error}</p>;
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

  const renderVisualization = () => {
    if (dataLoading) {
      return <p className="data-loading">Loading historical map data...</p>;
    }
    if (dataError) {
      return <p className="error-message">Error loading map: {dataError}</p>;
    }
    if (clusteredData.length === 0) {
        return <p className="error-message">No historical data available for visualization.</p>;
    }

    return (
      <div className="chart-container">
        {/* The Scatter chart component */}
        <Scatter data={getChartData()} options={chartOptions} />
      </div>
    );
  };
  
  return (
    <div className="container">
      <h1>🛍️ Mall Customer Segment Predictor</h1>
      <p>Enter a customer's details to instantly classify them into a marketing segment.</p>
      
      {/* RENDER THE CHART ABOVE THE FORM */}
      {renderVisualization()}

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