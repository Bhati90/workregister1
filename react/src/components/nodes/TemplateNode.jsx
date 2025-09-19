import React, { memo, useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
const API_BASE_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp'; // Make sure this matches your Django backend URL
import axios from 'axios';
// Helper function to find variables like {{1}}, {{2}} in the text
const findVariables = (text) => {
  if (!text) return [];
  const regex = /\{\{([0-9])\}\}/g;
  const matches = text.match(regex) || [];
  return [...new Set(matches.map(v => v.replace(/\{|\}/g, '')))];
};

export default memo(({ data, isConnectable }) => {
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [headerComponent, setHeaderComponent] = useState(null);
  const [bodyVariables, setBodyVariables] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  useEffect(() => {
    if (!data.templates) {
      return;
    }

    if (data.selectedTemplateName) {
      const templateData = data.templates.find(t => t.name === data.selectedTemplateName);
      if (templateData) {
        setSelectedTemplate(templateData);
        const components = templateData.components || [];
        const header = components.find(c => c.type === 'HEADER' && ['IMAGE', 'VIDEO', 'DOCUMENT'].includes(c.format));
        setHeaderComponent(header);
        const body = components.find(c => c.type === 'BODY');
        setBodyVariables(findVariables(body?.text));
      }
    } else {
        setSelectedTemplate(null);
        setHeaderComponent(null);
        setBodyVariables([]);
    }
  }, [data.selectedTemplateName, data.templates]);

  const handleTemplateChange = (e) => data.onUpdate('selectedTemplateName', e.target.value);
  const handleVariableChange = (e) => data.onUpdate(e.target.name, e.target.value);
  
  // --- NEW: UPLOAD HANDLER FOR MEDIA HEADERS ---
  const handleMediaUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    const formData = new FormData();
    formData.append('media', file);

    try {
        const response = await axios.post(`${API_BASE_URL}/api/upload-media-to-meta/`, formData);
        if (response.data.status === 'success') {
            // Save the Meta Media ID needed for sending
            data.onUpdate('metaMediaId', response.data.media_id);
            // Save a temporary local URL for the preview panel
            data.onUpdate('localPreviewUrl', URL.createObjectURL(file));
        } else {
            setUploadError(response.data.message || 'Upload failed.');
        }
    } catch (error) {
        setUploadError(error.response?.data?.message || 'Upload failed.');
    } finally {
        setUploading(false);
    }
  };
  return (
    <div className="custom-node template-node">
        {/* Input connection point for the node */}
        <Handle 
            type="target" 
            position={Position.Left} 
            isConnectable={isConnectable} 
        />

        <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
        
        <div className="node-header">
            <strong>WhatsApp Template</strong>
        </div>
        
        <div className="node-content">
            <label>Select Template:</label>
            <select onChange={handleTemplateChange} value={data.selectedTemplateName || ''}>
                <option value="" disabled>-- Choose a Template --</option>
                {data.templates?.map(template => (
                <option key={template.name} value={template.name}>
                    {template.name}
                </option>
                ))}
            </select>

            {/* --- REVISED: CONDITIONAL UI FOR MEDIA UPLOAD --- */}
            {headerComponent && (
                <div className="variable-input">
                    <label>Header {headerComponent.format}:</label>
                    <input type="file" onChange={handleMediaUpload} disabled={uploading} />
                    {uploading && <p>Uploading...</p>}
                    {uploadError && <p style={{ color: 'red' }}>Error: {uploadError}</p>}
                    {data.metaMediaId && <p style={{ color: 'green', fontSize: '0.8em' }}>Media ready (ID: {data.metaMediaId})</p>}
                </div>
            )}
            {bodyVariables.map(variableNum => (
                <div key={variableNum} className="variable-input">
                    <label>{`Body Variable {{${variableNum}}}`}:</label>
                    <input type="text" name={`bodyVar${variableNum}`} placeholder={`Value for variable ${variableNum}`} value={data[`bodyVar${variableNum}`] || ''} onChange={handleVariableChange} />
                </div>
            ))}
        </div>
        
        <div className="node-footer">
            {selectedTemplate && selectedTemplate.buttons && selectedTemplate.buttons.length > 0 ? (
                selectedTemplate.buttons.map((button, index) => (
                    <div key={index} className="output-handle-wrapper">
                        <span>{button.text}</span>
                        {/* Output connection point for each button */}
                        <Handle 
                            type="source" 
                            position={Position.Right} 
                            id={button.text} 
                            isConnectable={isConnectable} 
                        />
                    </div>
                ))
            ) : selectedTemplate ? (
                <div className="no-buttons-message">
                    This template has no Quick Reply buttons to connect.
                </div>
            ) : null}

            {/* --- NEW "On Read" TRIGGER HANDLE --- */}
            <div className="output-handle-wrapper event-handle">
                <span>On Read</span>
                <Handle
                    type="source"
                    position={Position.Right}
                    id="onRead" 
                    isConnectable={isConnectable}
                    style={{ background: '#28a745' }} // Green color to distinguish
                />
            </div>
        </div>
    </div>
  );
});
