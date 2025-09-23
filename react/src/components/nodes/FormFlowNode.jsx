import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

// Define the absolute base URL for your API at the top of the file
const API_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

const FormFlowNode = ({ id, data }) => {
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  const handleSelectChange = async (event) => {
    const selectedFlowId = event.target.value;
    data.onUpdate('flowStructure', null);
    
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
        // --- FIX IS HERE ---
        // Use the full, absolute API_URL
        const response = await fetch(`${API_URL}/api/get-flow-details/${selectedFlowId}/`);
        // --- END OF FIX ---
        
        // This line was causing the error because the response was HTML
        const result = await response.json(); 

        if (result.status === 'success' && result.data.flow_json) {
          data.onUpdate('flowStructure', result.data.flow_json);
        } else {
          console.error("Failed to fetch flow details:", result);
        }
      } catch (error) {
        // The error you saw was caught here
        console.error("Error fetching flow details:", error);
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
        
        {/* Show a loading message */}
        {isLoadingDetails && <div className="loading-text">Loading details...</div>}

        {/* Display the full structure once it's loaded */}
        {data.flowStructure && !isLoadingDetails && (
          <div className="flow-structure-preview">
            <h5>Flow Structure Preview:</h5>
            {data.flowStructure.screens.map((screen, index) => (
              <div key={screen.id || index} className="screen-preview">
                <strong>Screen: {screen.title}</strong>
                <ul>
                  {screen.layout.children
                    .filter(c => c.type !== 'Footer') // Don't show the footer
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