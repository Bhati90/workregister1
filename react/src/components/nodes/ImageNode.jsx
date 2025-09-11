// src/components/nodes/ImageNode.jsx
import React, { memo, useState } from 'react'; // Import useState
import { Handle, Position } from 'reactflow';
import axios from 'axios'; // Import axios for uploads

const API_BASE_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp'; // Make sure this matches your Django backend URL

export default memo(({ data, isConnectable }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null); // Clear previous errors

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/upload-image-to-meta/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.status === 'success' && response.data.media_id) {
        data.onUpdate('metaMediaId', response.data.media_id); // Save the Meta Media ID
        data.onUpdate('imageUrl', file.name); // Store file name for display, not URL
      } else {
        setUploadError(response.data.message || 'Failed to get Meta Media ID.');
      }
    } catch (error) {
      console.error("Error uploading image to Meta:", error);
      setUploadError(error.response?.data?.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="custom-node image-node">
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
      <div className="node-header">
        <strong>Image & Caption</strong>
      </div>
      <div className="node-content">
        <label>Upload Image:</label>
        <input
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          disabled={uploading}
        />
        {uploading && <p>Uploading...</p>}
        {uploadError && <p style={{ color: 'red' }}>Error: {uploadError}</p>}
        {data.metaMediaId && (
          <p style={{ color: 'green', fontSize: '0.8em' }}>
            Image uploaded: {data.imageUrl || data.metaMediaId} (ID: {data.metaMediaId})
          </p>
        )}

        <label>Caption:</label>
        <textarea
          value={data.caption || ''}
          onChange={(e) => data.onUpdate('caption', e.target.value)}
          rows={3}
          placeholder="Enter image caption..."
        />
      </div>
    </div>
  );
});