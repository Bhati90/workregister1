import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

// Helper to map component types to an emoji for better visuals
const componentIcons = {
  'heading': '📰',
  'text': '📝',
  'text-input': '⌨️',
  'textarea': '📄',
  'dropdown': '📋',
  'radio-group': '🔘',
  'checkbox-group': '✅',
  'date-picker': '📅',
};

const FormFlowNode = ({ id, data }) => {
  // The handleSelectChange function remains the same
  const handleSelectChange = (event) => {
    const selectedFlowId = event.target.value;
    const selectedFlow = data.forms.find(form => form.id == selectedFlowId);

    if (selectedFlow) {
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
      // Clear all data
      Object.keys(data).forEach(key => {
        if (!['onUpdate', 'onDelete', 'forms'].includes(key)) {
          data.onUpdate(key, '');
        }
      });
      data.onUpdate('flowStructure', null);
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
            <option key={form.id} value={form.id}>
              {form.name}
            </option>
          ))}
        </select>
        
        {data.selectedFormId && (
          <>
            <div className="flow-details">
                <div className="detail-item"><strong>Flow Name:</strong> <span>{data.selectedFormName}</span></div>
                <div className="detail-item"><strong>Flow Status:</strong> <span>{data.flowStatus}</span></div>
                <div className="detail-item"><strong>Template:</strong> <span>{data.templateName}</span></div>
                <div className="detail-item"><strong>Category:</strong> <span>{data.templateCategory}</span></div>
                <div className="detail-item"><strong>Created:</strong> <span>{data.createdAt}</span></div>
            </div>

            <div className="flow-structure-preview">
                <h5>Flow Structure Preview:</h5>
                {data.flowStructure?.screens_data?.map((screen, index) => (
                <div key={screen.id || index} className="screen-preview">
                    <strong>Screen: {screen.title}</strong>
                    <div className="component-list">
                    {screen.components?.map((component, compIndex) => (
                        <div key={compIndex} className="component-item">
                            {componentIcons[component.type] || '▫️'} {component.label}
                        </div>
                    ))}
                    </div>
                </div>
                ))}
            </div>
          </>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} id = "onSuccess" />
    </div>
  );
};

export default memo(FormFlowNode);