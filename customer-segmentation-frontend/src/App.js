// In src/App.js

import React from 'react';
import './App.css'; // Keep the styling import
import DynamicAnalysis from './DynamicAnalysis'; // Import the new component

function App() {
  // We can easily switch back to the old component if needed
  // return <PredictionForm />; 
  return <DynamicAnalysis />; 
}

export default App;