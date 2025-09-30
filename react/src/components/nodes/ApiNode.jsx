import React, { memo, useEffect, useState, useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import axios from 'axios';

// Helper icon component
const ApiIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6"></polyline>
        <polyline points="8 6 2 12 8 18"></polyline>
    </svg>
);


const API_BASE_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

// The main node component, now acting as a summary view
export default memo(({ data, isConnectable }) => {
    const [showConfigModal, setShowConfigModal] = useState(false);

    const openModal = () => setShowConfigModal(true);
    const closeModal = () => setShowConfigModal(false);

    return (
        <>
            <div className="custom-node api-node-summary" onClick={openModal}>
                <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
                <button onClick={(e) => { e.stopPropagation(); data.onDelete(data.id); }} className="delete-button summary-delete-btn">×</button>
                
                <div className="node-header">
                    <div className="node-header-icon"><ApiIcon /></div>
                    <strong>API Request</strong>
                </div>
                <div className="node-content">
                    <p>{data.apiUrl || 'Webhook URL not set'}</p>
                </div>

                <Handle type="source" position={Position.Right} id="onSuccess" isConnectable={isConnectable} style={{ top: '35%' }} />
                <Handle type="source" position={Position.Right} id="onError" isConnectable={isConnectable} style={{ top: '65%' }} />
            </div>

            {showConfigModal && (
                <ApiConfigModal 
                    data={data}
                    onClose={closeModal}
                />
            )}
        </>
    );
});

// The detailed configuration modal component
const ApiConfigModal = ({ data, onClose }) => {
    const [attributes, setAttributes] = useState([]);
    const [activeTab, setActiveTab] = useState('body');
    const [testResult, setTestResult] = useState(null);
    const [testLoading, setTestLoading] = useState(false);

    useEffect(() => {
        axios.get(`${API_BASE_URL}/api/attributes/`)
            .then(response => setAttributes(response.data))
            .catch(error => console.error("Could not fetch attributes:", error));
    }, []);
    
    // Memoize callbacks to prevent re-renders
    const onUpdate = useCallback((field, value) => data.onUpdate(field, value), [data]);

    const addResponseMapping = useCallback(() => {
        const currentMappings = data.responseMappings || [];
        onUpdate('responseMappings', [...currentMappings, { jsonPath: '', attributeId: '' }]);
    }, [data.responseMappings, onUpdate]);

    const updateResponseMapping = useCallback((index, field, value) => {
        const currentMappings = [...(data.responseMappings || [])];
        currentMappings[index][field] = value;
        onUpdate('responseMappings', currentMappings);
    }, [data.responseMappings, onUpdate]);

    const removeResponseMapping = useCallback((index) => {
        const currentMappings = [...(data.responseMappings || [])];
        currentMappings.splice(index, 1);
        onUpdate('responseMappings', currentMappings);
    }, [data.responseMappings, onUpdate]);

    const testApiRequest = async () => {
        setTestLoading(true);
        setTestResult(null);
        try {
            const requestConfig = {
                method: data.method || 'GET',
                url: data.apiUrl,
                headers: data.headers ? JSON.parse(data.headers) : {},
                data: (data.method !== 'GET' && data.requestBody) ? JSON.parse(data.requestBody) : undefined,
            };
            const response = await axios(requestConfig);
            setTestResult({ success: true, status: response.status, data: response.data });
        } catch (error) {
            setTestResult({ success: false, status: error.response?.status, data: error.response?.data, error: error.message });
        } finally {
            setTestLoading(false);
        }
    };

    return (
        <div className="api-config-modal-overlay">
            <div className="api-config-modal">
                <div className="modal-header">
                    <h3>Request</h3>
                    <button onClick={onClose} className="close-btn">×</button>
                </div>

                <div className="modal-body">
                    <div className="request-setup">
                        <select value={data.method || 'GET'} onChange={(e) => onUpdate('method', e.target.value)} className="method-select">
                            <option>GET</option>
                            <option>POST</option>
                            <option>PUT</option>
                            <option>PATCH</option>
                            <option>DELETE</option>
                        </select>
                        <input type="text" value={data.apiUrl || ''} onChange={(e) => onUpdate('apiUrl', e.target.value)} placeholder="Enter URL or paste" className="url-input" />
                    </div>

                    <div className="request-tabs">
                        <button className={activeTab === 'params' ? 'active' : ''} onClick={() => setActiveTab('params')}>Params</button>
                        <button className={activeTab === 'headers' ? 'active' : ''} onClick={() => setActiveTab('headers')}>Headers</button>
                        <button className={activeTab === 'body' ? 'active' : ''} onClick={() => setActiveTab('body')}>Body</button>
                    </div>

                    <div className="tab-content">
                        {activeTab === 'headers' && (
                             <textarea value={data.headers || ''} onChange={(e) => onUpdate('headers', e.target.value)} rows={5} placeholder={'{\n  "Authorization": "Bearer YOUR_TOKEN"\n}'} className="json-editor" />
                        )}
                        {activeTab === 'body' && (
                            <textarea value={data.requestBody || ''} onChange={(e) => onUpdate('requestBody', e.target.value)} rows={5} placeholder={'{\n  "key": "value",\n  "name": "{{contact.name}}"\n}'} className="json-editor" />
                        )}
                         {activeTab === 'params' && (
                             <div className="params-placeholder">Parameter configuration coming soon.</div>
                        )}
                    </div>
                    
                    <div className="response-section">
                        <h4>Response</h4>
                        <label>Capture response in Attribute</label>
                        {(data.responseMappings || []).map((mapping, index) => (
                            <div key={index} className="mapping-row">
                                <input type="text" placeholder="JSON path (e.g. data.user.id)" value={mapping.jsonPath} onChange={(e) => updateResponseMapping(index, 'jsonPath', e.target.value)} />
                                <select value={mapping.attributeId} onChange={(e) => updateResponseMapping(index, 'attributeId', e.target.value)}>
                                    <option value="">Select attribute</option>
                                    {attributes.map(attr => <option key={attr.id} value={attr.id}>{attr.name}</option>)}
                                </select>
                                <button onClick={() => removeResponseMapping(index)} className="remove-btn">-</button>
                            </div>
                        ))}
                         <button onClick={addResponseMapping} className="add-mapping-btn">+ Add</button>
                    </div>

                    {testResult && (
                        <div className="response-section test-response">
                            <h4>Test Response</h4>
                            <pre className={testResult.success ? 'success' : 'error'}>
                                <strong>Status: {testResult.status}</strong><br/>
                                {JSON.stringify(testResult.data, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button onClick={testApiRequest} className="test-btn" disabled={testLoading}>{testLoading ? 'Testing...' : 'Test'}</button>
                    <button onClick={onClose} className="save-btn">Save</button>
                </div>
            </div>
        </div>
    );
};
