import React, { memo, useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
  const [selectedForm, setSelectedForm] = useState(null);

  useEffect(() => {
    if (data.selectedFormId && data.forms) {
      const formData = data.forms.find(f => f.id === data.selectedFormId);
      setSelectedForm(formData);
    } else {
      setSelectedForm(null);
    }
  }, [data.selectedFormId, data.forms]);

  const handleFormChange = (e) => {
    const formId = e.target.value;
    data.onUpdate('selectedFormId', formId);
    
    // Also update the form name for easier reference
    const form = data.forms?.find(f => f.id === formId);
    if (form) {
      data.onUpdate('selectedFormName', form.name);
    }
  };

  const handlePropertyChange = (property, value) => {
    data.onUpdate(property, value);
  };

  return (
    <div className="custom-node flow-form-node">
      {/* Input connection point */}
      <Handle 
        type="target" 
        position={Position.Left} 
        isConnectable={isConnectable} 
      />

      <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
      
      <div className="node-header">
        <strong>WhatsApp Flow Form</strong>
      </div>
      
      <div className="node-content">
        <div className="form-group">
          <label>Select Form:</label>
          <select 
            onChange={handleFormChange} 
            value={data.selectedFormId || ''}
          >
            <option value="" disabled>-- Choose a Form --</option>
            {data.forms?.map(form => (
              <option key={form.id} value={form.id}>
                {form.name}
              </option>
            ))}
          </select>
        </div>

        {selectedForm && (
          <>
            <div className="form-group">
              <label>Template Body:</label>
              <textarea
                rows="3"
                value={data.templateBody || selectedForm.template_body || ''}
                onChange={(e) => handlePropertyChange('templateBody', e.target.value)}
                placeholder="Template message body"
              />
            </div>

            <div className="form-group">
              <label>Button Text:</label>
              <input
                type="text"
                value={data.buttonText || selectedForm.template_button_text || ''}
                onChange={(e) => handlePropertyChange('buttonText', e.target.value)}
                placeholder="Flow button text"
              />
            </div>

            <div className="form-info">
              <div className="info-item">
                <strong>Screens:</strong> {selectedForm.screens_data?.length || 0}
              </div>
              <div className="info-item">
                <strong>Category:</strong> {selectedForm.template_category}
              </div>
            </div>
          </>
        )}
      </div>
      
      <div className="node-footer">
        {selectedForm ? (
          <>
            {/* Success handle - when form is completed */}
            <div className="output-handle-wrapper success-handle">
              <span>On Complete</span>
              <Handle
                type="source"
                position={Position.Right}
                id="onComplete"
                isConnectable={isConnectable}
                style={{ background: '#28a745' }}
              />
            </div>

            {/* Error handle - when form fails or is cancelled */}
            <div className="output-handle-wrapper error-handle">
              <span>On Error</span>
              <Handle
                type="source"
                position={Position.Right}
                id="onError"
                isConnectable={isConnectable}
                style={{ background: '#dc3545' }}
              />
            </div>

            {/* Timeout handle - when form expires */}
            <div className="output-handle-wrapper timeout-handle">
              <span>On Timeout</span>
              <Handle
                type="source"
                position={Position.Right}
                id="onTimeout"
                isConnectable={isConnectable}
                style={{ background: '#ffc107' }}
              />
            </div>
          </>
        ) : (
          <div className="no-form-message">
            Select a form to see connection options.
          </div>
        )}
      </div>
    </div>
  );
});