import React, { useState, useEffect } from 'react';

// This is the main component for the preview panel
const FlowPreview = ({ nodes, edges }) => {
    const [startNode, setStartNode] = useState(null);

    // Find the starting point of the flow whenever the nodes change
    useEffect(() => {
        const templateNode = nodes.find(n => n.type === 'templateNode');
        setStartNode(templateNode);
    }, [nodes]);

    // Recursive function to render a node and its connected children
    const renderFlowNode = (nodeId) => {
        const node = nodes.find(n => n.id === nodeId);
        if (!node) return null;

        const outgoingEdges = edges.filter(e => e.source === nodeId);
        
        // Map each type of node to its visual preview component
        const nodePreview = () => {
            switch (node.type) {
                case 'templateNode':
                    return <TemplatePreview data={node.data} />;
                case 'textNode':
                    return <TextMessagePreview data={node.data} />;
                case 'buttonsNode':
                    return <ButtonsMessagePreview data={node.data} />;
                case 'imageNode':
                    return <ImageMessagePreview data={node.data} />;
                case 'interactiveImageNode':
                    return <InteractiveImagePreview data={node.data} />;
                case 'interactiveListNode':
                    return <ListMessagePreview data={node.data} />;
                case 'mediaNode':
                    return <MediaMessagePreview data={node.data} />;
                default:
                    return <div className="preview-bubble-unknown">Unknown Node</div>;
            }
        };

        return (
            <div key={node.id} className="preview-step">
                {nodePreview()}
                <div className="preview-options">
                    {/* Render the buttons/options that lead to the next step */}
                    {outgoingEdges.map(edge => {
                        const nextNode = nodes.find(n => n.id === edge.target);
                        const handleText = edge.sourceHandle === 'onRead' ? `(On Read)` : edge.sourceHandle;
                        return (
                            <div key={edge.id} className="preview-option-path">
                                <div className="path-line"></div>
                                <div className="path-label">
                                    <span className={edge.sourceHandle === 'onRead' ? 'on-read-label' : ''}>
                                        {handleText}
                                    </span> → {nextNode?.type || '...'}
                                </div>
                                {renderFlowNode(edge.target)}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <aside className="flow-preview">
            <div className="phone-mockup">
                <div className="phone-header">
                    <span className="phone-contact">Flow Preview</span>
                </div>
                <div className="phone-screen">
                    {startNode ? renderFlowNode(startNode.id) : <div className="no-flow-message">Add a Template node to begin.</div>}
                </div>
            </div>
        </aside>
    );
};


// --- Individual Preview Components for each Node Type ---

// --- THIS COMPONENT IS UPGRADED ---
const TemplatePreview = ({ data }) => {
    const selectedTemplate = data.templates?.find(t => t.name === data.selectedTemplateName);

    if (!selectedTemplate) {
        return (
            <div className="preview-bubble-outbound">
                <p className="preview-text"><em>Select a template to see its preview.</em></p>
            </div>
        );
    }

    const components = selectedTemplate.components || [];
    const headerComp = components.find(c => c.type === 'HEADER');
    const bodyComp = components.find(c => c.type === 'BODY');
    const footerComp = components.find(c => c.type === 'FOOTER');

    // Process the body text, replacing variables with user-entered values
    let bodyText = bodyComp?.text || '';
    if (bodyText) {
        const variables = bodyText.match(/\{\{([0-9])\}\}/g) || [];
        variables.forEach(variable => {
            const varNum = variable.replace(/\{|\}/g, '');
            const userValue = data[`bodyVar${varNum}`];
            // Replace with user value, or a placeholder like [var1] if empty
            const replacement = userValue ? `<strong>${userValue}</strong>` : `[variable ${varNum}]`;
            bodyText = bodyText.replace(variable, replacement);
        });
    }

    const renderHeader = () => {
        if (!headerComp) return null;
        
        if (['IMAGE', 'VIDEO', 'DOCUMENT'].includes(headerComp.format)) {
            const imageUrl = data.localPreviewUrl || 'https://placehold.co/600x300/e3f2fd/2196F3?text=Media+Header';
            return <img src={imageUrl} alt="Header Preview" className="preview-header-image" />;
        }
        
        if (headerComp.format === 'TEXT') {
            return <p className="preview-header-text"><strong>{headerComp.text}</strong></p>;
        }
        
        return null;
    };

    return (
        <div className="preview-bubble-outbound">
            {renderHeader()}
            {/* Use dangerouslySetInnerHTML to render the bolded variables */}
            <p className="preview-text" style={{ whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: bodyText }} />
            {footerComp && <p className="preview-footer-text">{footerComp.text}</p>}
        </div>
    );
};


const TextMessagePreview = ({ data }) => (
    <div className="preview-bubble-outbound">
        <p className="preview-text">{data.text || '...'}</p>
    </div>
);

const ButtonsMessagePreview = ({ data }) => (
    <div className="preview-bubble-outbound">
        <p className="preview-text">{data.text || '...'}</p>
        <div className="preview-buttons-footer">
            {data.buttons?.map((btn, i) => <div key={i} className="preview-button-pill">{btn.text}</div>)}
        </div>
    </div>
);

const ImageMessagePreview = ({ data }) => (
    <div className="preview-bubble-outbound preview-bubble-media">
        <img src={data.localPreviewUrl || 'https://placehold.co/600x400/fff3e0/ff9800?text=Image'} alt="Image Preview" />
        <p className="preview-caption">{data.caption}</p>
    </div>
);

const InteractiveImagePreview = ({ data }) => (
     <div className="preview-bubble-outbound">
        <img src={data.localPreviewUrl || 'https://placehold.co/600x300/e3f2fd/2196F3?text=Image+Header'} alt="Header Preview" className="preview-header-image" />
        <p className="preview-text">{data.bodyText || '...'}</p>
        <div className="preview-buttons-footer">
            {data.buttons?.map((btn, i) => <div key={i} className="preview-button-pill">{btn.text}</div>)}
        </div>
    </div>
);

// --- THIS COMPONENT IS UPGRADED TO BE INTERACTIVE ---
const ListMessagePreview = ({ data }) => {
    const [isListOpen, setIsListOpen] = useState(false);

    return (
        <>
            <div className="preview-bubble-outbound">
                {data.header && <p className="preview-header-text">{data.header}</p>}
                <p className="preview-text">{data.body || '...'}</p>
                {data.footer && <p className="preview-footer-text">{data.footer}</p>}
                <div className="preview-buttons-footer list-button" onClick={() => setIsListOpen(true)}>
                    <span className="list-icon">☰</span> {data.buttonText || 'Select'}
                </div>
            </div>

            {isListOpen && (
                <div className="preview-list-popup">
                    <div className="preview-list-header">
                        <span>{data.header || 'List'}</span>
                        <button onClick={() => setIsListOpen(false)} className="close-list-btn">×</button>
                    </div>
                    <div className="preview-list-content">
                        {(data.sections || []).map((section, sIndex) => (
                            <div key={sIndex}>
                                <div className="preview-list-section-title">{section.title}</div>
                                {(section.rows || []).map((row, rIndex) => (
                                    <div key={rIndex} className="preview-list-item">
                                        <div className="preview-list-item-text">
                                            <div className="preview-list-item-title">{row.title}</div>
                                            {row.description && <div className="preview-list-item-description">{row.description}</div>}
                                        </div>
                                        <div className="preview-list-item-radio"></div>
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );
};

const MediaMessagePreview = ({ data }) => {
    const text = `[${data.mediaType || 'file'}] ${data.filename || data.caption || ''}`;
    return (
        <div className="preview-bubble-outbound preview-bubble-doc">
            <span className="doc-icon">📄</span>
            <p className="preview-text">{text}</p>
        </div>
    );
};


export default FlowPreview;