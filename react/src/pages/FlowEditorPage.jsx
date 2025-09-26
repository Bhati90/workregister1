// FlowEditorPage.jsx - Combined create/edit page
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import FlowBuilder from '../components/FlowBuilder';

const API_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

const FlowEditorPage = () => {
  const { flowId } = useParams(); // Get flow ID from URL
  const navigate = useNavigate();
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isEditing = flowId && flowId !== 'new';

  useEffect(() => {
    if (isEditing) {
      fetchFlowData();
    } else {
      // For new flows, just set empty data
      setFlowData({
        id: null,
        name: 'My New Flow',
        flow_data: { nodes: [], edges: [] },
        is_active: true
      });
      setLoading(false);
    }
  }, [flowId, isEditing]);

  const fetchFlowData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/flows/${flowId}/`);
      
      if (response.data.status === 'success') {
        setFlowData(response.data.flow);
      } else {
        setError(response.data.message || 'Failed to load flow');
      }
    } catch (error) {
      console.error('Error fetching flow:', error);
      if (error.response?.status === 404) {
        setError('Flow not found');
      } else {
        setError('Failed to load flow data');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-container" style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div className="loading-spinner">
          Loading {isEditing ? 'flow' : 'editor'}...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container" style={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')} className="btn btn-primary">
          Back to Flow List
        </button>
      </div>
    );
  }

  return (
    <div className="flow-editor-page">
      <FlowBuilder 
        initialData={flowData} 
        isEditing={isEditing}
      />
    </div>
  );
};

export default FlowEditorPage;