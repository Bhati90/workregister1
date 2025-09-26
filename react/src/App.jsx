import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FlowListPage from './pages/FlowListPage';
import FlowBuilderPage from './pages/FlowBuilderPage';
import AnalyticsPage from './pages/AnalyticsPage'; // <-- Import the new page
import 'reactflow/dist/style.css';
import './App.css';
import AttributesPage from './pages/AttributePage';
import FlowEditorPage from './pages/FlowEditorPage';

function App() {
  return (
    <Router>
      <div className="App">
        {/* You could add a navigation header here if you like */}
        <Routes>
          <Route path="/" element={<FlowListPage />} />
          <Route path = "/attributes" element = {<AttributesPage/>}/>
          {/* <Route path="/flow/:flowId" element={<FlowBuilderPage />} />
           */}
           <Route path="/flow/:flowId" element={<FlowEditorPage />} />
           <Route path="/flow/new" element={<FlowEditorPage />} />
          
          {/* <Route path="/analytics" element={<AnalyticsPage />} /> <-- Add the route */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;
