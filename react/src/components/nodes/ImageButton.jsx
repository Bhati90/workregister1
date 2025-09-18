import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';
import axios from 'axios';

const API_BASE_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

export default memo(({ data, isConnectable }) => {
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const buttons = data.buttons || [];

    const onUpdate = (field, value) => data.onUpdate(field, value);

    const handleImageUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        setUploadError(null);
        const formData = new FormData();
        formData.append('media', file); // Use 'media' as the key

        try {
            // NOTE: Using a generalized media upload endpoint now
            const response = await axios.post(`${API_BASE_URL}/api/upload-media-to-meta/`, formData);
            if (response.data.status === 'success') {
                onUpdate('metaMediaId', response.data.media_id);
                onUpdate('imageUrl', file.name);
            } else {
                setUploadError(response.data.message || 'Upload failed.');
            }
        } catch (error) {
            setUploadError(error.response?.data?.message || 'Upload failed.');
        } finally {
            setUploading(false);
        }
    };

    const onButtonTextChange = (e, index) => {
        const newButtons = [...buttons];
        newButtons[index] = { ...newButtons[index], text: e.target.value };
        onUpdate('buttons', newButtons);
    };

    const addButton = () => {
        if (buttons.length < 3) {
            onUpdate('buttons', [...buttons, { text: `Button ${buttons.length + 1}` }]);
        }
    };

    const removeButton = (index) => {
        onUpdate('buttons', buttons.filter((_, i) => i !== index));
    };

    return (
        <div className="custom-node image-buttons-node">
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
            <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
            <div className="node-header"><strong>Image with Buttons</strong></div>
            <div className="node-content">
                <label>Header Image:</label>
                <input type="file" accept="image/jpeg,image/png" onChange={handleImageUpload} disabled={uploading} />
                {uploading && <p>Uploading...</p>}
                {uploadError && <p style={{ color: 'red' }}>Error: {uploadError}</p>}
                {data.metaMediaId && <p style={{ color: 'green', fontSize: '0.8em' }}>Uploaded: {data.imageUrl}</p>}
                
                <label>Body Text:</label>
                <textarea value={data.bodyText || ''} onChange={(e) => onUpdate('bodyText', e.target.value)} rows={3} placeholder="Enter message text..." />

                <hr className="divider" />
                <label>Buttons (Max 3):</label>
                {buttons.map((btn, index) => (
                    <div key={index} className="button-input-wrapper">
                        <input type="text" value={btn.text} onChange={(e) => onButtonTextChange(e, index)} />
                        <button onClick={() => removeButton(index)} className="remove-btn">×</button>
                    </div>
                ))}
                {buttons.length < 3 && <button onClick={addButton} className="add-btn">+ Add Button</button>}
            </div>
            <div className="node-footer">
                {buttons.map((btn, index) => (
                    <div key={index} className="output-handle-wrapper">
                        <span>{btn.text}</span>
                        <Handle type="source" position={Position.Right} id={btn.text} isConnectable={isConnectable} />
                    </div>
                ))}
            </div>
        </div>
    );
});