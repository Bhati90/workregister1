import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Panel,
  MarkerType, 
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

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';
const edgeOptions = {
  animated: true,
  style: { stroke: '#b1b1b7', strokeWidth: 2 },
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: '#b1b1b7',
  },
};
let id = 0;
const getId = () => `dndnode_${id++}`;

const FlowBuilder = ({ initialData, isEditing }) => {
    const navigate = useNavigate();
    const [nodes, setNodes, onNodesChange] = useNodesState(initialData?.flow_data?.nodes || []);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialData?.flow_data?.edges || []);
    const [reactFlowInstance, setReactFlowInstance] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [flowName, setFlowName] = useState(initialData?.name || 'My New Flow');
    const [isSidebarVisible, setIsSidebarVisible] = useState(true);
    const [flowForms, setFlowForms] = useState([]);
    
    // Update node data to latest - set the highest id counter to avoid conflicts
    useEffect(() => {
        if (initialData?.flow_data?.nodes) {
            const maxId = initialData.flow_data.nodes.reduce((max, node) => {
                const nodeIdNum = parseInt(node.id.replace('dndnode_', ''));
                return nodeIdNum > max ? nodeIdNum : max;
            }, 0);
            id = maxId + 1;
        }
    }, [initialData]);

    useEffect(() => {
        if (initialData) {
            setFlowName(initialData.name || 'My New Flow');
            // Set nodes and edges if they exist
            if (initialData.flow_data?.nodes) {
                setNodes(initialData.flow_data.nodes);
            }
            if (initialData.flow_data?.edges) {
                setEdges(initialData.flow_data.edges);
            }
        }
    }, [initialData, setNodes, setEdges]);
    
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

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                const templatesResponse = await axios.get(`${API_URL}/api/templates/`);
                setTemplates(templatesResponse.data);
                
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

    // Update nodes with latest data when templates or forms are loaded
    useEffect(() => {
        if (templates.length > 0 || flowForms.length > 0) {
            setNodes((prevNodes) => 
                prevNodes.map((node) => {
                    const updatedData = { ...node.data };
                    
                    // Update callbacks for all nodes
                    updatedData.onUpdate = (field, value) => updateNodeData(node.id, field, value);
                    updatedData.onDelete = deleteNode;
                    
                    // Update specific node data
                    if (node.type === 'templateNode' && templates.length > 0) {
                        updatedData.templates = templates;
                    }
                    if (node.type === 'flowFormNode' && flowForms.length > 0) {
                        updatedData.forms = flowForms;
                    }
                    
                    return { ...node, data: updatedData };
                })
            );
        }
    }, [templates, flowForms, deleteNode]);
  
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
                            buttonText: '',
                            templateCategory: '',
                            templateBody: '',
                            templateButtonText: '',
                            flowStatus: '',
                            templateName: '',
                            templateStatus: '',
                            createdAt: '',
                            flowStructure: null
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

        const apiUrl = isEditing 
            ? `${API_URL}/api/flows/${initialData.id}/update/`
            : `${API_URL}/api/flows/save/`;
        
        const httpMethod = isEditing ? 'put' : 'post';

        axios[httpMethod](apiUrl, payload)
            .then(response => {
                if (response.data.status === 'success') {
                    alert(isEditing ? 'Flow updated successfully!' : response.data.message);
                    navigate('/');
                } else {
                    alert(`Error: ${response.data.message}`);
                }
            })
            .catch(error => {
                console.error(`Error ${isEditing ? 'updating' : 'saving'} flow:`, error);
                alert(`Failed to ${isEditing ? 'update' : 'save'} flow.`);
            });
    }, [reactFlowInstance, flowName, navigate, initialData, isEditing]);

    if (isLoading) {
        return (
            <div className="loading-container" style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh'
            }}>
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
                         defaultEdgeOptions={edgeOptions} 
                        onEdgesDelete={(edgesToDelete) => {  // Add this handler
    edgesToDelete.forEach(edge => onEdgeDelete(edge.id));
  }}
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
                                <button onClick={onSave}>
                                    {isEditing ? 'Update Flow' : 'Save Flow'}
                                </button>
                                <button onClick={() => navigate('/')}>
                                    Back to List
                                </button>
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