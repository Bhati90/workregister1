import React, { memo, useEffect, useState } from 'react';
import { Handle, Position } from 'reactflow';
import axios from 'axios';

const API_BASE_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

export default memo(({ data, isConnectable }) => {
    const [attributes, setAttributes] = useState([]);

    // Fetch the list of available attributes when the node is mounted
    useEffect(() => {
        axios.get(`${API_BASE_URL}/api/attributes/`)
            .then(response => setAttributes(response.data))
            .catch(error => console.error("Could not fetch attributes:", error));
    }, []);

    const onUpdate = (field, value) => data.onUpdate(field, value);

    return (
        <div className="custom-node question-node">
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
            <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
            <div className="node-header"><strong>Ask a Question</strong></div>
            <div className="node-content">
                <label>Question Message:</label>
                <textarea 
                    value={data.questionText || ''} 
                    onChange={(e) => onUpdate('questionText', e.target.value)} 
                    rows={3} 
                    placeholder="E.g., What is your email address?" 
                />
                
                <label>Save Answer to Attribute:</label>
                <select 
                    value={data.saveAttributeId || ''} 
                    onChange={(e) => onUpdate('saveAttributeId', e.target.value)}
                >
                    <option value="" disabled>-- Select Attribute --</option>
                    {attributes.map(attr => (
                        <option key={attr.id} value={attr.id}>{attr.name}</option>
                    ))}
                </select>
            </div>
            <div className="node-footer">
                 <div className="output-handle-wrapper">
                    <span>Answer Received</span>
                    <Handle type="source" position={Position.Right} id="onAnswer" isConnectable={isConnectable} />
                </div>
            </div>
        </div>
    );
});

