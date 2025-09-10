// src/components/nodes/TextNode.jsx
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
  const onTextChange = (e) => {
    data.onUpdate('text', e.target.value);
  };

  return (
    <div className="custom-node text-node">
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
      <div className="node-header">
        <strong>Text Message</strong>
      </div>
      <div className="node-content">
        <textarea
          defaultValue={data.text}
          onChange={onTextChange}
          rows={3}
          placeholder="Enter message..."
        />
      </div>
    </div>
  );
});