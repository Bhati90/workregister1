// src/App.js
import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  Handle,
  Position,
  Panel,
  useReactFlow,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './FlowBuilder.css';

// // --- 1. DUMMY TEMPLATE DATA (This would come from your API) ---
// const TEMPLATES = [
//   { id: 'template_01', name: 'Welcome Offer', buttons: ['Yes', 'No'] },
//   { id: 'template_02', name: 'Appointment Confirmation', buttons: ['Confirm', 'Reschedule', 'Cancel'] },
//   { id: 'template_03', name: 'Feedback Request', buttons: ['Give Feedback'] },
// ];
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
// --- 2. CUSTOM NODE COMPONENTS ---

// Node for starting the flow
const FlowStartNode = ({ data }) => (
  <div className="flow-node flow-start-node">
    <div className="flow-node-header"><span className="icon">➡️</span> Flow Start</div>
    <div className="flow-node-body">
      <p>Select a template to begin building your flow.</p>
      <button onClick={data.onChooseTemplate} className="flow-button nodrag">Choose Template</button>
    </div>
  </div>
);

// Node that represents the chosen template and its button outputs
const TemplateNode = ({ data }) => (
  <div className="flow-node template-node">
    <Handle type="target" position={Position.Left} />
    <div className="flow-node-header">
      <span className="icon">📄</span> Template: {data.name}
    </div>
    <div className="flow-node-body">
      <p>Connect a new node to each button output.</p>
      <div className="template-node-outputs">
        {data.buttons.map((buttonName, index) => (
          <div key={buttonName} className="template-output-item">
            <span>{buttonName}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={buttonName} // CRUCIAL: The handle ID is the button name
              style={{ top: `${(index + 1) * (100 / (data.buttons.length + 1))}%` }}
            />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Node for sending a message (text, image, button)
const MessageNode = ({ data, id }) => {
  const onDataChange = (field, value) => {
    data.onDataChange(id, { ...data, [field]: value });
  };
  return (
    <div className="flow-node message-node">
      <Handle type="target" position={Position.Left} />
      <div className="flow-node-header"><span className="icon">💬</span> Message Action</div>
      <div className="flow-node-body">
        <label>Text</label>
        <textarea rows={3} value={data.text || ''} onChange={(e) => onDataChange('text', e.target.value)} className="nodrag" />
        <label>Image URL</label>
        <input type="text" value={data.imageUrl || ''} onChange={(e) => onDataChange('imageUrl', e.target.value)} className="nodrag" />
        <label>Button Text</label>
        <input type="text" value={data.buttonText || ''} onChange={(e) => onDataChange('buttonText', e.target.value)} className="nodrag" />
        <label>Button URL</label>
        <input type="text" value={data.buttonUrl || ''} onChange={(e) => onDataChange('buttonUrl', e.target.value)} className="nodrag" />
      </div>
    </div>
  );
};

// --- 3. MAIN FLOW BUILDER COMPONENT ---

const nodeTypes = {
  flowStart: FlowStartNode,
  template: TemplateNode,
  message: MessageNode,
};

let id = 1;
const getId = () => `node_${id++}`;

const FlowBuilder = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showModal, setShowModal] = useState(false);
  const [templates, setTemplates] = useState([]); // State to hold templates from API
 const reactFlowInstance = useReactFlow();
  const [activeTemplate, setActiveTemplate] = useState(null);

    const onSave = useCallback(async () => { // Make the function async
        if (!activeTemplate) {
          alert("Please select a template before saving.");
          return;
        }
        
        const flow = reactFlowInstance.toObject();
        const cleanFlow = {
          ...flow,
          nodes: flow.nodes.map(node => {
            const { onDataChange, onChooseTemplate, ...restData } = node.data;
            return { ...node, data: restData };
          }),
        };

        const payload = {
          template_name: activeTemplate,
          flow: cleanFlow,
        };

        try {
            const csrftoken = getCookie('csrftoken');
            const response = await fetch('http://127.0.0.1:8000/register/api/save-flow/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (response.ok) {
                alert(result.message);
                console.log('Saved Flow to Backend:', payload);
            } else {
                throw new Error(result.message || 'Failed to save flow.');
            }
        } catch (error) {
            console.error('Error saving flow:', error);
            alert(`Error: ${error.message}`);
        }
    }, [reactFlowInstance, activeTemplate]);
  // NEW: Fetch templates from Django when the component loads
  useEffect(() => {
    async function fetchTemplates() {
      try {
        const response = await fetch('http://127.0.0.1:8000/register/api/get-whatsapp-templates/'); // Your new Django API endpoint
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        setTemplates(data);
      } catch (error) {
        console.error("Failed to fetch templates:", error);
        alert("Could not load templates from the server.");
      }
    }
    fetchTemplates();
  }, []);

  const onConnect = useCallback((params) =>
    setEdges((eds) => addEdge({ ...params, type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed } }, eds)), [setEdges]);

  const updateNodeData = useCallback((nodeId, newData) => {
    setNodes((nds) => nds.map((node) => node.id === nodeId ? { ...node, data: { ...node.data, ...newData } } : node));
  }, [setNodes]);

  const addNode = useCallback((type, data, position) => {
    const newNode = {
      id: getId(),
      type,
      position,
      data: { ...data, onDataChange: updateNodeData },
    };
    setNodes((nds) => nds.concat(newNode));
  }, [setNodes, updateNodeData]);

  const handleTemplateSelect = (template) => {
    setActiveTemplate(template.name);
    const startNode = nodes[0];
    const position = { x: startNode.position.x + 400, y: startNode.position.y };
    addNode('template', template, position);

    // Automatically connect the start node to the new template node
    setEdges((eds) => eds.concat({
      id: `e-${startNode.id}-template`,
      source: startNode.id,
      target: `node_${id - 1}`, // The ID of the node we just added
      type: 'smoothstep',
    }));

    setShowModal(false);
  };

  useEffect(() => {
    // Add the initial start node if it doesn't exist
    if (nodes.length === 0) {
      setNodes([{
        id: 'node_0',
        type: 'flowStart',
        position: { x: 50, y: 150 },
        data: { onChooseTemplate: () => setShowModal(true) },
      }]);
    }
  }, [nodes.length, setNodes]);

  return (
    <div className="flow-builder-container">
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Choose a Template</h3>
              {templates.map(t => <button key={t.id} onClick={() => handleTemplateSelect(t)} className="flow-button">{t.name}</button>)}
            <button onClick={() => setShowModal(false)} style={{ background: '#6c757d', marginTop: '10px' }} className="flow-button">Cancel</button>
         </div>
        </div>
      )}
      <aside className="sidebar">
        <h3>Actions</h3>
        <div className="sidebar-item" onClick={() => addNode('message', {}, { x: 700, y: 100 })}>
          💬 Message Action
        </div>
      </aside>
      <div className="reactflow-wrapper">
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} nodeTypes={nodeTypes} fitView>
          <Controls />
          <Background />
          <Panel position="top-right">
            <button onClick={onSave}>Save Flow</button>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
};

// Wrap the main component in the provider
export default function App() {
  return (
    <ReactFlowProvider>
      <FlowBuilder />
    </ReactFlowProvider>
  );
}