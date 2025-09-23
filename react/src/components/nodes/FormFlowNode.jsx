import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const FormFlowNode = ({ id, data }) => {
  // Add a loading state for the second API call
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  const handleSelectChange = async (event) => {
    const selectedFlowId = event.target.value;
    
    // First, clear any old data
    data.onUpdate('flowStructure', null);
    
    if (!selectedFlowId) {
      // If the user selected the placeholder, clear everything
      data.onUpdate('selectedFormId', '');
      data.onUpdate('selectedFormName', '');
      return;
    }

    const selectedFlow = data.forms.find(form => form.flow_id == selectedFlowId);
    if (selectedFlow) {
      // Update the name immediately
      data.onUpdate('selectedFormId', selectedFlowId);
      data.onUpdate('selectedFormName', selectedFlow.name);
      
      setIsLoadingDetails(true); // Set loading to true

      try {
        // --- NEW: Fetch the detailed structure from your new backend endpoint ---
        const response = await fetch(`/register/whatsapp/api/get-flow-details/${selectedFlowId}/`);
        const result = await response.json();

        if (result.status === 'success' && result.data.flow_json) {
          // Update the node with the full structure
          data.onUpdate('flowStructure', result.data.flow_json);
        } else {
          console.error("Failed to fetch flow details:", result);
        }

      } catch (error) {
        console.error("Error fetching flow details:", error);
      } finally {
        setIsLoadingDetails(false); // Set loading to false
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