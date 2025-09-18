import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';
import axios from 'axios';

const API_BASE_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

const fileAcceptMap = {
    document: '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx',
    video: 'video/mp4,video/3gpp',
    audio: 'audio/aac,audio/mp4,audio/mpeg,audio/amr,audio/ogg',
};

export default memo(({ data, isConnectable }) => {
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const mediaType = data.mediaType || 'document';

    const onUpdate = (field, value) => data.onUpdate(field, value);

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
                onUpdate('metaMediaId', response.data.media_id);
                onUpdate('mediaUrl', file.name); // Store filename for display
                 if (mediaType === 'document') {
                    onUpdate('filename', file.name); // Set filename for documents
                }
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
        <div className="custom-node media-node">
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
            <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
            <div className="node-header"><strong>Media Message</strong></div>
            <div className="node-content">
                <label>Media Type:</label>
                <select value={mediaType} onChange={(e) => onUpdate('mediaType', e.target.value)}>
                    <option value="document">Document</option>
                    <option value="video">Video</option>
                    <option value="audio">Audio</option>
                </select>

                <label>Upload File:</label>
                <input type="file" accept={fileAcceptMap[mediaType]} onChange={handleMediaUpload} disabled={uploading} />
                {uploading && <p>Uploading...</p>}
                {uploadError && <p style={{ color: 'red' }}>Error: {uploadError}</p>}
                {data.metaMediaId && <p style={{ color: 'green', fontSize: '0.8em' }}>Uploaded: {data.mediaUrl}</p>}
                
                {mediaType !== 'audio' && (
                     <label>Caption:</label>
                )}
                {mediaType !== 'audio' && (
                    <textarea value={data.caption || ''} onChange={(e) => onUpdate('caption', e.target.value)} rows={2} placeholder="Optional caption..." />
                )}

                {mediaType === 'document' && (
                     <label>Filename:</label>
                )}
                {mediaType === 'document' && (
                    <input type="text" value={data.filename || ''} onChange={(e) => onUpdate('filename', e.target.value)} placeholder="Filename for recipient" />
                )}
            </div>
        </div>
    );
});