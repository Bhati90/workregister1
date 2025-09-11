// src/pages/FlowBuilderPage.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ReactFlowProvider } from 'reactflow';
import FlowBuilder from '../components/FlowBuilder';

const API_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

const FlowBuilderPage = () => {
  const { flowId } = useParams();
  const navigate = useNavigate();
  const [initialFlowData, setInitialFlowData] = useState(null);
  const [loading, setLoading] = useState(true);

  const isNewFlow = flowId === 'new';

  useEffect(() => {
    if (!isNewFlow) {
      // It's an existing flow, let's fetch its data
      axios.get(`${API_URL}/api/flows/${flowId}/`)
        .then(response => {
          setInitialFlowData(response.data);
          setLoading(false);
        })
        .catch(error => {
          console.error("Error fetching flow data:", error);
          alert("Could not load the flow. It might have been deleted.");
          navigate('/'); // Redirect to the list page on error
        });
    } else {
      setLoading(false); // It's a new flow, no data to load
    }
  }, [flowId, isNewFlow, navigate]);

  if (loading) {
    return <div>Loading Flow Builder...</div>;
  }

  return (
    <ReactFlowProvider>
      {/* Pass the initial data to the FlowBuilder component */}
      <FlowBuilder initialData={initialFlowData} />
    </ReactFlowProvider>
  );
};

export default FlowBuilderPage;