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
import AskQuestionNode from './nodes/AskQuestionNode';
import AskLocationNode from './nodes/AskLocationNode';
import AskImageNode from './nodes/AskImageNode';
import ApiNode from './nodes/ApiNode';
import FormFlowNode from './nodes/FormFlowNode';

// REGISTER ALL NODE TYPES
const nodeTypes = { 
  templateNode: TemplateNode, 
  textNode: TextNode,
  buttonsNode: ButtonsNode,
  askLocationNode: AskLocationNode,
  imageNode: ImageNode,
  interactiveImageNode: InteractiveImageNode,
  interactiveListNode: InteractiveListNode,
  mediaNode: MediaNode,
  askQuestionNode: AskQuestionNode,
  askForImageNode: AskImageNode,
  flowFormNode: FormFlowNode,
  askApiNode: ApiNode
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
    const [isSidebarVisible, setIsSidebarVisible] = useState(true);
    const [flowForms, setFlowForms] = useState([]);

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

    const onEdgeDelete = useCallback((edgeIdToDelete) => {
        setEdges((currentEdges) => currentEdges.filter((edge) => edge.id !== edgeIdToDelete));
    }, [setEdges]);

    const deleteNode = useCallback((nodeId) => {
        setNodes((nds) => nds.filter((node) => node.id !== nodeId));
        setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    }, [setNodes, setEdges]);

    // Fetch templates and flow forms
    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                
                // Fetch templates
                const templatesResponse = await axios.get(`${API_URL}/api/templates/`);
                setTemplates(templatesResponse.data);
                
                // Fetch flow forms
                const formsResponse = await axios.get(`${API_URL}/api/whatsapp-forms/`);
                if (formsResponse.data.status === 'success') {
                    setFlowForms(formsResponse.data.forms);
                }
            } catch (error) {
                console.error("Error fetching data:", error);
            } finally {
                setIsLoading(false);
            }
        };
        
        fetchData();
    }, []);

    // Update existing flow form nodes when forms data is loaded
    useEffect(() => {
        if (flowForms.length > 0) {
            setNodes(nds => nds.map(node => {
                if (node.type === 'flowFormNode') {
                    return {
                        ...node,
                        data: {
                            ...node.data,
                            forms: flowForms
                        }
                    };
                }
                return node;
            }));
        }
    }, [flowForms, setNodes]);

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
                case 'askApiNode':
                    newNode = { 
                        id: newNodeId, 
                        type, 
                        position, 
                        data: { 
                            ...commonData, 
                            method: 'GET',
                            apiUrl: '',
                            headers: '{\n  "Content-Type": "application/json"\n}',
                            requestBody: '',
                            responseMappings: [],
                            statusCodeAttributeId: ''
                        }
                    };
                    break; 
                case 'askLocationNode':
                    newNode = { id: newNodeId, type, position, data: { ...commonData, questionText: '', longitudeAttributeId: null, latitudeAttributeId: null }};
                    break;
                case 'askForImageNode':
                    newNode = { id: newNodeId, type, position, data: { ...commonData, questionText: '', saveAttributeId: null }};
                    break;
                case 'askQuestionNode':
                    newNode = { id: newNodeId, type, position, data: { ...commonData, questionText: '', saveAttributeId: null }};
                    break;
                case 'flowFormNode':
                    newNode = { 
                        id: newNodeId, 
                        type, 
                        position, 
                        data: { 
                            ...commonData, 
                            forms: flowForms,
                            selectedFormId: '',
                            selectedFormName: '',
                            templateBody: '',
                            buttonText: ''
                        }
                    };
                    break;
                default:
                    return;
            }
            
            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance, templates, flowForms, deleteNode]
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

        // Clean the flow data - remove functions and large objects from node data
        const cleanedNodes = flow.nodes.map(node => ({
            id: node.id,
            type: node.type,
            position: node.position,
            data: {
                ...Object.fromEntries(
                    Object.entries(node.data || {}).filter(([key, value]) => 
                        !['onUpdate', 'onDelete', 'forms', 'templates'].includes(key) &&
                        typeof value !== 'function'
                    )
                )
            }
        }));

        const payload = { 
            name: flowName, 
            template_name: triggerTemplateName, 
            flow: {
                nodes: cleanedNodes,
                edges: flow.edges
            }
        };

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

    if (isLoading) {
        return (
            <div className="loading-container">
                <div className="loading-spinner">Loading...</div>
            </div>
        );
    }

    return (
        <div className="flow-builder-layout">
            <div className={`dndflow ${!isSidebarVisible ? 'sidebar-collapsed' : ''}`}>
                {isSidebarVisible && 
                    <Sidebar 
                        onHide={() => setIsSidebarVisible(false)} 
                        flowForms={flowForms}
                    />
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
                                <input 
                                    type="text" 
                                    value={flowName} 
                                    onChange={(e) => setFlowName(e.target.value)}
                                    placeholder="Enter flow name..."
                                />
                                <button onClick={onSave}>Save Flow</button>
                            </div>
                        </Panel>
                        <Controls />
                        <Background />
                    </ReactFlow>
                </div>
            </div>
            <FlowPreview nodes={nodes} edges={edges} onEdgeDelete={onEdgeDelete} />
        </div>
    );
};

export default FlowBuilder;