import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
    const onUpdate = (field, value) => data.onUpdate(field, value);

    return (
        <div className="custom-node api-node">
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
            <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
            <div className="node-header"><strong>API Request (Webhook)</strong></div>
            <div className="node-content">
                <label>Webhook URL:</label>
                <input 
                    type="text" 
                    value={data.webhookUrl || ''} 
                    onChange={(e) => onUpdate('webhookUrl', e.target.value)}
                    placeholder="https://yourapi.com/webhook"
                />
            </div>
             <div className="node-footer">
                 <div className="output-handle-wrapper">
                    <span>Request Sent</span>
                    <Handle type="source" position={Position.Right} id="onSent" isConnectable={isConnectable} />
                </div>
                 <div className="output-handle-wrapper event-handle">
                    <span>Request Failed</span>
                    <Handle type="source" position={Position.Right} id="onFail" isConnectable={isConnectable} style={{ background: '#ff4d4d' }}/>
                </div>
            </div>
        </div>
    );
});