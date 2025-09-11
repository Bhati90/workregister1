// src/components/nodes/ButtonsNode.jsx
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
  const buttons = data.buttons || [];

  const onTextChange = (e) => {
    data.onUpdate('text', e.target.value);
  };

  const onButtonTextChange = (e, index) => {
    const newButtons = [...buttons];
    newButtons[index] = { ...newButtons[index], text: e.target.value };
    data.onUpdate('buttons', newButtons);
  };

  const addButton = () => {
    if (buttons.length < 3) {
      const newButtons = [...buttons, { text: `Button ${buttons.length + 1}` }];
      data.onUpdate('buttons', newButtons);
    }
  };

  const removeButton = (index) => {
    const newButtons = buttons.filter((_, i) => i !== index);
    data.onUpdate('buttons', newButtons);
  };

  return (
    <div className="custom-node buttons-node">
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
      <div className="node-header">
        <strong>Text with Buttons</strong>
      </div>
      <div className="node-content">
        <label>Message Text:</label>
        <textarea
          value={data.text || ''}
          onChange={onTextChange}
          rows={3}
          placeholder="Enter message..."
        />
        <hr className="divider" />
        <label>Buttons (Max 3):</label>
        {buttons.map((btn, index) => (
          <div key={index} className="button-input-wrapper">
            <input
              type="text"
              value={btn.text}
              onChange={(e) => onButtonTextChange(e, index)}
              placeholder="Button text"
            />
            <button onClick={() => removeButton(index)} className="remove-btn">×</button>
          </div>
        ))}
        {buttons.length < 3 && (
          <button onClick={addButton} className="add-btn">+ Add Button</button>
        )}
      </div>
      <div className="node-footer">
        {buttons.map((btn, index) => (
          <div key={index} className="output-handle-wrapper">
            <span>{btn.text}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={btn.text}
              isConnectable={isConnectable}
            />
          </div>
        ))}
      </div>
    </div>
  );
});