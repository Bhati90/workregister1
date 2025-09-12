// src/components/FlowBuilder.jsx
// import { useRuseCallback, useEffect } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Panel,
} from 'reactflow';
import axios from 'axios';
import Sidebar from './Sidebar';
import TemplateNode from './nodes/TemplateNode';
import TextNode from './nodes/TextNode';
import ButtonsNode from './nodes/ButtonsNode';
import ImageNode from './nodes/ImageNode';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Import useNavigate


const nodeTypes = { templateNode: TemplateNode, textNode: TextNode,buttonsNode: ButtonsNode,
  imageNode: ImageNode, };
const API_URL = 'http://127.0.0.1:8000/register/whatsapp'; // Change to your Django server URL

let id = 0;
const getId = () => `dndnode_${id++}`;

const FlowBuilder = ({ initialData }) => {
  const navigate = useNavigate();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialData?.flow_data?.nodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialData?.flow_data?.edges || []); // <-- CORRECTED
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [templates, setTemplates] = useState([]);
  // const [flowName, setFlowName] = useState('My New Flow');
  const [isLoading, setIsLoading] = useState(true);


  const [flowName, setFlowName] = useState(initialData?.name || 'My New Flow');
  
  const updateNodeData = (nodeId, field, value) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          node.data = { ...node.data, [field]: value };
        }
        return node;
      })
    );
  };

  const deleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
  }, [setNodes, setEdges]);

  useEffect(() => {
    axios.get(`${API_URL}/api/templates/`)
      .then(response => {
        setTemplates(response.data);
      })
      .catch(error => {
        console.error("Could not fetch WhatsApp templates:", error);
        alert("Could not fetch WhatsApp templates from the server.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (typeof type === 'undefined' || !type) return;

     
      const position = reactFlowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const newNodeId = getId();
      let newNode;

      if (type === 'templateNode') {
        newNode = {
          id: newNodeId, type, position,
          data: {
            id: newNodeId, templates: templates,
            onUpdate: (field, value) => updateNodeData(newNodeId, field, value),
            onDelete: deleteNode,
          },
        };
      } else if (type === 'textNode') {
        newNode = {
          id: newNodeId, type, position,
          data: {
            id: newNodeId, text: '',
            onUpdate: (field, value) => updateNodeData(newNodeId, field, value),
            onDelete: deleteNode,
          },
        };
      }
      else if (type === 'buttonsNode') {
        newNode = {
          id: newNodeId, type, position,
          data: {
            id: newNodeId, text: '', buttons: [],
            onUpdate: (field, value) => updateNodeData(newNodeId, field, value),
            onDelete: deleteNode,
          },
        };
      } else if (type === 'imageNode') {
        newNode = {
          id: newNodeId, type, position,
          data: {
            id: newNodeId,  metaMediaId: '', // Initialize Meta Media ID
            imageUrl: '', // Will store filename for display
            caption: '',
            onUpdate: (field, value) => updateNodeData(newNodeId, field, value),
            onDelete: deleteNode,
          },
        };
      }

      if (newNode) {
        setNodes((nds) => nds.concat(newNode));
      }
    },
    [reactFlowInstance, nodes, templates, deleteNode]
  );
  
  const onSave = useCallback(() => {
    if (!reactFlowInstance) return;
    const flow = reactFlowInstance.toObject();

    const templateNode = flow.nodes.find(n => n.type === 'templateNode');

    const triggerTemplateName = templateNode?.data.selectedTemplateName || null;

    if (!templateNode || !templateNode.data.selectedTemplateName) {
      alert("Error: A template must be selected to save the flow.");
      return;
    }

    
    if (!flowName.trim()) {
      alert("Please enter a name for the flow.");
      return;
    }
    const payload = {
      name: flowName,
      template_name: triggerTemplateName,
      flow: flow,
    };


    axios.post(`${API_URL}/api/flows/save/`, payload)
      .then(response => {
        alert(response.data.message);
        navigate('/'); // <-- Navigate back to the list page
      })
      .catch(error => {
        console.error("Error saving flow:", error);
        alert("Failed to save flow.");
      });
  }, [reactFlowInstance, flowName, navigate]);

  return (
    <div className="dndflow">
      { !isLoading ? (
        <Sidebar />
      ) : (
        <div className="sidebar loading-pane">
          <p>Loading Templates...</p>
        </div>
      )}
      <div className="reactflow-wrapper">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
        >
          <Panel position="top-left">
            <div className="flow-controls">
              <input type="text" value={flowName} onChange={(e) => setFlowName(e.target.value)} />
              <button onClick={onSave}>Save Flow</button>
            </div>
          </Panel>
          <Controls />
          <Background />
        </ReactFlow>
      </div>

      <div className="back-to-list">
         <button onClick={() => navigate('/')}>← Back to Flows</button>
       </div>
    </div>
  );
};

export default FlowBuilder;