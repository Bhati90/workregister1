// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FlowListPage from './pages/FlowListPage';
import FlowBuilderPage from './pages/FlowBuilderPage';
import 'reactflow/dist/style.css';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<FlowListPage />} />
          {/* This one route handles both creating a new flow and editing an existing one */}
          <Route path="/flow/:flowId" element={<FlowBuilderPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;