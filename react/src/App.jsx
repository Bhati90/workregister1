// src/App.js
import React from 'react';
import { ReactFlowProvider } from 'reactflow';
import FlowBuilder from './components/FlowBuilder.jsx';
import 'reactflow/dist/style.css';
import './App.css';

function App() {
  return (
    <div className="App">
      <ReactFlowProvider>
        <FlowBuilder />
      </ReactFlowProvider>
    </div>
  );
}

export default App;