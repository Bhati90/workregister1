import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const FormFlowNode = ({ id, data }) => {

  const handleSelectChange = (event) => {
    const selectedFlowId = event.target.value;
    const selectedFlow = data.forms.find(form => form.flow_id == selectedFlowId);

    if (selectedFlow) {
      // --- UPDATE THIS SECTION TO STORE ALL THE NEW DATA ---
      data.onUpdate('selectedFormId', selectedFlowId);
      data.onUpdate('selectedFormName', selectedFlow.name);
      data.onUpdate('flowStructure', selectedFlow.structure || null);
      data.onUpdate('templateCategory', selectedFlow.template_category);
      data.onUpdate('templateBody', selectedFlow.template_body);
      data.onUpdate('templateButtonText', selectedFlow.template_button_text);
      data.onUpdate('flowStatus', selectedFlow.flow_status);
      data.onUpdate('templateName', selectedFlow.template_name);
      data.onUpdate('templateStatus', selectedFlow.template_status);
      data.onUpdate('createdAt', selectedFlow.created_at);
    } else {
      // Clear all data if nothing is selected
      data.onUpdate('selectedFormId', '');
      data.onUpdate('selectedFormName', '');
      data.onUpdate('flowStructure', null);
      data.onUpdate('templateCategory', '');
      data.onUpdate('templateBody', '');
      data.onUpdate('templateButtonText', '');
      data.onUpdate('flowStatus', '');
      data.onUpdate('templateName', '');
      data.onUpdate('templateStatus', '');
      data.onUpdate('createdAt', '');
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
        
        {/* This section now displays everything */}
        {data.selectedFormId && (
          <div className="flow-content-preview">
            
            {/* --- NEW: Display all the database fields --- */}
            <div className="flow-details">
                <p><strong>Flow Name:</strong> {data.selectedFormName}</p>
                <p><strong>Flow Status:</strong> {data.flowStatus}</p>
                <p><strong>Template Name:</strong> {data.templateName}</p>
                <p><strong>Template Status:</strong> {data.templateStatus}</p>
                <p><strong>Category:</strong> {data.templateCategory}</p>
                <p><strong>Created At:</strong> {data.createdAt}</p>
            </div>
            
            <hr />

            <h5>Flow Structure Preview:</h5>
            {data.flowStructure?.screens_data?.map((screen, index) => (
              <div key={screen.id || index} className="screen-preview">
                <strong>Screen: {screen.title}</strong>
                <ul>
                  {screen.components?.map((component, compIndex) => (
                    <li key={compIndex}>
                      {component.type}: "{component.label}"
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