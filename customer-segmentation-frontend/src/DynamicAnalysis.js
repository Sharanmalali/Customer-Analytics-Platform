import React, { useState } from 'react';
// We will integrate this new component into App.js later
// For now, assume this is the main entry point

// --- CONFIGURATION CONSTANTS ---
const API_BASE_URL = 'http://127.0.0.1:8000/api/';
// IMPORTANT: Replace this with a valid Company ID!
const COMPANY_ID = 3; // e.g., The company ID you used in your tests
// -----------------------------

const ALL_FEATURES = [
    'Gender',
    'Age',
    'Annual Income (k$)',
    'Spending Score (1-100)'
];

function DynamicAnalysis() {
    // --- State for File Upload and Feature Selection ---
    const [file, setFile] = useState(null);
    const [selectedFeatures, setSelectedFeatures] = useState([]);
    const [numClusters, setNumClusters] = useState(5); // Default K=5
    const [fileUploadStatus, setFileUploadStatus] = useState(null); // 'success', 'error', 'loading'

    // --- State for Dynamic Analysis Job ---
    const [analysisJobId, setAnalysisJobId] = useState(null);
    const [analysisStatus, setAnalysisStatus] = useState(null); // 'queued', 'running', 'completed', 'failed'
    const [analysisResults, setAnalysisResults] = useState(null);

    // --- State for Data ID after upload ---
    const [datasetId, setDatasetId] = useState(null);

    // -----------------------------------------------------------
    // 1. FILE UPLOAD HANDLER
    // -----------------------------------------------------------
    const handleFileUpload = async (e) => {
        e.preventDefault();
        if (!file) {
            alert("Please select a file first.");
            return;
        }

        setFileUploadStatus('loading');
        setDatasetId(null);
        const formData = new FormData();
        formData.append('file', file);
        // Note: description is optional, but helps
        formData.append('description', `Dynamic upload for company ${COMPANY_ID}`); 

        try {
            // This calls your existing, proven upload endpoint!
            const response = await fetch(`${API_BASE_URL}companies/${COMPANY_ID}/datasets/`, {
                method: 'POST',
                // FastAPI correctly handles multipart/form-data when using FormData
                body: formData, 
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
            }

            const data = await response.json();
            setDatasetId(data.id);
            setFileUploadStatus('success');
            alert(`File uploaded successfully! Dataset ID: ${data.id}`);

        } catch (error) {
            console.error("Upload Error:", error);
            setFileUploadStatus('error');
            alert(`File upload failed: ${error.message}`);
        }
    };

    // -----------------------------------------------------------
    // 2. FEATURE SELECTION HANDLER
    // -----------------------------------------------------------
    const handleFeatureChange = (feature) => {
        setSelectedFeatures(prev => 
            prev.includes(feature) 
            ? prev.filter(f => f !== feature) 
            : [...prev, feature]
        );
    };

    // -----------------------------------------------------------
    // 3. RUN ANALYSIS HANDLER (Calls the new Dynamic Endpoint)
    // -----------------------------------------------------------
    const handleRunAnalysis = async () => {
        if (!datasetId) {
            alert("Please upload a dataset first.");
            return;
        }
        if (selectedFeatures.length < 2) {
            alert("Please select at least two features for clustering.");
            return;
        }

        setAnalysisStatus('loading');
        setAnalysisJobId(null);
        setAnalysisResults(null);

        const payload = {
            dataset_id: datasetId,
            features: selectedFeatures,
            n_clusters: numClusters,
        };

        try {
            // This calls the new dynamic analysis endpoint!
            const response = await fetch(`${API_BASE_URL}datasets/run-dynamic-analysis/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                 const errorData = await response.json();
                 throw new Error(errorData.detail || `Analysis failed with status ${response.status}`);
            }

            const jobData = await response.json();
            setAnalysisJobId(jobData.id);
            setAnalysisStatus('queued');
            
            // Start polling for results
            pollJobStatus(jobData.id);

        } catch (error) {
            setAnalysisStatus('failed');
            alert(`Analysis initiation failed: ${error.message}`);
            console.error("Analysis Initiation Error:", error);
        }
    };

    // -----------------------------------------------------------
    // 4. POLLING LOGIC (Checks job status periodically)
    // -----------------------------------------------------------
    const pollJobStatus = (jobId) => {
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}analysis-jobs/${jobId}`);
                if (!response.ok) throw new Error("Failed to fetch job status.");

                const job = await response.json();
                setAnalysisStatus(job.status);

                if (job.status === 'completed') {
                    clearInterval(intervalId);
                    setAnalysisResults(job.results); // Job results contain the summary
                    alert(`Dynamic Analysis Job ${jobId} Completed!`);
                } else if (job.status === 'failed') {
                    clearInterval(intervalId);
                    setAnalysisResults(job.results);
                    alert(`Dynamic Analysis Job ${jobId} Failed! Check console for details.`);
                }
            } catch (error) {
                console.error("Polling Error:", error);
                clearInterval(intervalId);
                setAnalysisStatus('failed');
            }
        }, 5000); // Poll every 5 seconds
        return () => clearInterval(intervalId); // Cleanup function
    };

    // -----------------------------------------------------------
    // 5. RENDER LOGIC
    // -----------------------------------------------------------
    const renderForm = () => (
        <div className="analysis-section">
            <h2>1. Upload Data (Step 1 of 2)</h2>
            <p>Your CSV must contain the columns: CustomerID, Gender, Age, Annual Income (k$), Spending Score (1-100).</p>
            
            <form onSubmit={handleFileUpload} className="file-upload-form">
                <input 
                    type="file" 
                    accept=".csv" 
                    onChange={(e) => setFile(e.target.files[0])} 
                    required 
                />
                <button 
                    type="submit" 
                    disabled={fileUploadStatus === 'loading' || !file}
                >
                    {fileUploadStatus === 'loading' ? 'Uploading...' : 'Upload & Process Data'}
                </button>
            </form>
            {datasetId && (
                <p className="success-message">✅ Data uploaded! Dataset ID: **{datasetId}**</p>
            )}
            
            {datasetId && (
                <>
                    <hr />
                    <h2>2. Select Features & Run Analysis (Step 2 of 2)</h2>
                    
                    <div className="feature-selection">
                        <label>Features for Clustering (Select 2+):</label>
                        <div className="checkbox-group">
                            {ALL_FEATURES.map(feature => (
                                <label key={feature}>
                                    <input 
                                        type="checkbox" 
                                        checked={selectedFeatures.includes(feature)}
                                        onChange={() => handleFeatureChange(feature)}
                                        // Allow max 3 features for complexity reasons, or 2 for simple visual
                                    />
                                    {feature}
                                </label>
                            ))}
                        </div>
                    </div>
                    
                    <div className="input-group" style={{maxWidth: '200px', margin: '20px auto'}}>
                        <label htmlFor="k-value">Number of Clusters (k):</label>
                        <input
                            id="k-value"
                            type="number"
                            value={numClusters}
                            onChange={(e) => setNumClusters(Math.max(2, parseInt(e.target.value) || 2))}
                            required
                            min="2"
                            max="10"
                        />
                    </div>

                    <button 
                        onClick={handleRunAnalysis} 
                        disabled={selectedFeatures.length < 2 || analysisStatus === 'loading' || analysisStatus === 'running'}
                    >
                        {analysisStatus === 'running' ? 'Analysis Running...' : 'Start Dynamic Clustering'}
                    </button>
                </>
            )}
        </div>
    );

    const renderResults = () => {
        if (!analysisJobId) return null;

        return (
            <div className="results-container">
                <h2>Analysis Job Status: {analysisStatus.toUpperCase()}</h2>
                <p>Job ID: **{analysisJobId}**</p>
                
                {analysisStatus === 'running' && <p className="loading-message">Analysis is running in the background. Please wait...</p>}
                
                {analysisStatus === 'completed' && analysisResults && (
                    <>
                        <p className="success-message">Analysis completed successfully on: **{analysisResults.features_used.join(', ')}**</p>
                        {/* We will add Bar Chart/Visualization here in Phase 2 */}
                        <h3>Cluster Distribution:</h3>
                        <ul>
                            {Object.entries(analysisResults.cluster_distribution).map(([cluster, count]) => (
                                <li key={cluster}>Cluster {cluster}: {count} customers</li>
                            ))}
                        </ul>
                    </>
                )}
                
                {analysisStatus === 'failed' && <p className="error-message">Analysis Failed: {analysisResults.error || 'Check server logs.'}</p>}
            </div>
        );
    };

    return (
        <div className="container dynamic-analysis">
            <h1>Dynamic Customer Analysis Platform 📈</h1>
            <p>Upload data and choose the features for K-Means Clustering.</p>
            
            {renderForm()}
            
            <hr style={{margin: '30px 0'}} />
            
            {renderResults()}
            
            {/* The Visualization component will be placed here in Phase 2 */}
        </div>
    );
}

export default DynamicAnalysis;