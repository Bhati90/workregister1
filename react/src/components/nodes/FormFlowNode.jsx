import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

// Ensure this URL points to your deployed Django backend
const API_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

const FormFlowNode = ({ id, data }) => {
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  const handleSelectChange = async (event) => {
    const selectedFlowId = event.target.value;
    
    // Reset state on every change
    data.onUpdate('flowStructure', null);
    setError(null);
    
    if (!selectedFlowId) {
      data.onUpdate('selectedFormId', '');
      data.onUpdate('selectedFormName', '');
      return;
    }

    const selectedFlow = data.forms.find(form => form.flow_id == selectedFlowId);
    if (selectedFlow) {
      data.onUpdate('selectedFormId', selectedFlowId);
      data.onUpdate('selectedFormName', selectedFlow.name);
      setIsLoadingDetails(true);

      try {
        const response = await fetch(`${API_URL}/api/get-flow-details/${selectedFlowId}/`);
        if (!response.ok) {
            // Handle HTTP errors like 404 or 500
            throw new Error(`API request failed with status ${response.status}`);
        }
        
        const result = await response.json();

        if (result.status === 'success' && result.data.flow_json) {
          data.onUpdate('flowStructure', result.data.flow_json);
        } else {
          // Handle logical errors from our own API
          throw new Error(result.message || 'Failed to fetch flow details.');
        }

      } catch (err) {
        console.error("Error fetching flow details:", err);
        setError(err.message);
      } finally {
        setIsLoadingDetails(false);
      }
    }
  };

  return (
    <div className="react-flow-node flow-form-node">
      <Handle type="target" position={Position.Top} />
      <div className="node-header"><strong>Flow Form Trigger</strong></div>

      <div className="node-content">
        <label htmlFor={`flow-select-${id}`}>Select a Flow:</label>
        <select 
          id={`flow-select-${id}`} 
          className="nodrag"
          value={data.selectedFormId} 
          onChange={handleSelectChange}
        >
          <option value="">-- Choose a Flow --</option>
          {data.forms && data.forms.map((form) => (
            <option key={form.flow_id} value={form.flow_id}>
              {form.name}
            </option>
          ))}
        </select>
        
        {isLoadingDetails && <div className="loading-text">Loading details...</div>}
        {error && <div className="error-text">Error: {error}</div>}

        {/* This improved rendering logic safely displays the full structure */}
        {data.flowStructure && !isLoadingDetails && (
          <div className="flow-structure-preview">
            <h5>Flow Structure Preview:</h5>
            {data.flowStructure.screens?.map((screen, index) => (
              <div key={screen.id || index} className="screen-preview">
                <strong>Screen: {screen.title}</strong>
                <ul>
                  {screen.layout?.children
                    ?.filter(c => c.type !== 'Footer') // Don't show the footer
                    .map((component, compIndex) => (
                    <li key={compIndex}>
                      {component.type}: "{component.label || component.text}"
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default memo(FormFlowNode);