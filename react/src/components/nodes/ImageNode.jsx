// src/components/nodes/ImageNode.jsx
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
  return (
    <div className="custom-node image-node">
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
      <div className="node-header">
        <strong>Image & Caption</strong>
      </div>
      <div className="node-content">
        <label>Image URL:</label>
        <input
          type="text"
          placeholder="https://... image link"
          value={data.imageUrl || ''}
          onChange={(e) => data.onUpdate('imageUrl', e.target.value)}
        />
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