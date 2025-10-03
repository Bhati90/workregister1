import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FlowListPage from './pages/FlowListPage';
import FlowBuilderPage from './pages/FlowBuilderPage';
import AnalyticsPage from './pages/AnalyticsPage'; // <-- Import the new page
import 'reactflow/dist/style.css';
import './App.css';
import AttributesPage from './pages/AttributePage';
import FlowEditorPage from './pages/FlowEditorPage';
import AIFlowGenerator from './components/FlowGenerator';
import TemplateFlowCreator from './pages/TemplateFlowCreator';
import FlexibleFlowGenerator from './components/AiFlowGenerator';
// import EnhancedAIFlowGenerator from './components/AiFlowGenerator';

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
           <Route path="/ai-tem-generator" element={<FlexibleFlowGenerator/>} />
          <Route path="/ai-flow-generator" element={<AIFlowGenerator />} />
           
           {/* <Route path="/template-flow-creator" element={<TemplateFlowCreator />} /> */}
          <Route path="/analytics" element={<AnalyticsPage />} /> 
        </Routes>
      </div>
    </Router>
  );
}

export default App;
