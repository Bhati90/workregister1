import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Panel,
} from 'reactflow';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import FlowPreview from './nodes/FlowPreview';

// Import all node types
import TemplateNode from './nodes/TemplateNode';
import TextNode from './nodes/TextNode';
import ButtonsNode from './nodes/ButtonsNode';
import ImageNode from './nodes/ImageNode';
import InteractiveImageNode from './nodes/ImageButton';
import InteractiveListNode from './nodes/ListNode';
import MediaNode from './nodes/MediaNode';


// REGISTER ALL NODE TYPES
const nodeTypes = { 
  templateNode: TemplateNode, 
  textNode: TextNode,
  buttonsNode: ButtonsNode,
  imageNode: ImageNode,
  interactiveImageNode: InteractiveImageNode,
  interactiveListNode: InteractiveListNode,
  mediaNode: MediaNode,
};

const API_URL = 'https://workregister1-g7pf.onrender.com/register/whatsapp';

let id = 0;
const getId = () => `dndnode_${id++}`;

const FlowBuilder = ({ initialData }) => {
    const navigate = useNavigate();
    const [nodes, setNodes, onNodesChange] = useNodesState(initialData?.flow_data?.nodes || []);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialData?.flow_data?.edges || []);
    const [reactFlowInstance, setReactFlowInstance] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [flowName, setFlowName] = useState(initialData?.name || 'My New Flow');
    const [isSidebarVisible, setIsSidebarVisible] = useState(true); // State for sidebar visibility

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
          .then(response => setTemplates(response.data))
          .catch(error => console.error("Could not fetch WhatsApp templates:", error))
          .finally(() => setIsLoading(false));
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
          
          const commonData = {
            id: newNodeId,
            onUpdate: (field, value) => updateNodeData(newNodeId, field, value),
            onDelete: deleteNode,
          };
          
          let newNode;
          switch (type) {
            case 'templateNode':
              newNode = { id: newNodeId, type, position, data: { ...commonData, templates: templates } };
              break;
            case 'textNode':
              newNode = { id: newNodeId, type, position, data: { ...commonData, text: '' } };
              break;
            case 'buttonsNode':
              newNode = { id: newNodeId, type, position, data: { ...commonData, text: '', buttons: [] } };
              break;
            case 'imageNode':
              newNode = { id: newNodeId, type, position, data: { ...commonData,  metaMediaId: '', imageUrl: '', caption: '' } };
              break;
            case 'interactiveImageNode':
                newNode = { id: newNodeId, type, position, data: { ...commonData, metaMediaId: '', imageUrl: '', bodyText: '', buttons: [] }};
                break;
            case 'interactiveListNode':
                newNode = { id: newNodeId, type, position, data: { ...commonData, header: '', body: '', footer: '', buttonText: '', sections: [] }};
                break;
            case 'mediaNode':
                newNode = { id: newNodeId, type, position, data: { ...commonData, mediaType: 'document', metaMediaId: '', mediaUrl: '', caption: '', filename: '' }};
                break;
            default:
                return;
          }
          
          setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance, templates, deleteNode]
      );
      
      const onSave = useCallback(() => {
        if (!reactFlowInstance) return;
        const flow = reactFlowInstance.toObject();
        const templateNode = flow.nodes.find(n => n.type === 'templateNode');
        const triggerTemplateName = templateNode?.data.selectedTemplateName || null;
    
        if (!templateNode || !triggerTemplateName) {
          alert("Error: A 'WhatsApp Template' node must exist and have a template selected to save the flow.");
          return;
        }
        if (!flowName.trim()) {
          alert("Please enter a name for the flow.");
          return;
        }
        const payload = { name: flowName, template_name: triggerTemplateName, flow: flow };
    
        axios.post(`${API_URL}/api/flows/save/`, payload)
          .then(response => {
            alert(response.data.message);
            navigate('/');
          })
          .catch(error => {
            console.error("Error saving flow:", error);
            alert("Failed to save flow.");
          });
      }, [reactFlowInstance, flowName, navigate]);

    return (
        <div className="flow-builder-layout">
            <div className={`dndflow ${!isSidebarVisible ? 'sidebar-collapsed' : ''}`}>
                {isSidebarVisible && 
                    <Sidebar onHide={() => setIsSidebarVisible(false)} />
                }
                <div className="reactflow-wrapper">
                {!isSidebarVisible && (
                    <button className="show-sidebar-btn" onClick={() => setIsSidebarVisible(true)}>
                        ☰
                    </button>
                )}
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
            </div>
            <FlowPreview nodes={nodes} edges={edges} />
        </div>
    );
};

export default FlowBuilder;
