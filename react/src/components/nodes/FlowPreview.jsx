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
                case 'askQuestionNode':
                    return <AskQuestionPreview data={node.data} />;                
                case 'askLocationNode':
                    return <AskLocationPreview data={node.data} />;
                case 'askForImageNode':
                    return <AskForImagePreview data={node.data} />;
                case 'askApiNode':
                    return <ApiRequestPreview data={node.data} />;
                case 'flowFormNode':
                    return <FormFlowPreview data={node.data} />;
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
const ApiRequestPreview = ({ data }) => (
  <div className="preview-bubble-system">
    <span className="system-icon">⚙️</span>
    <div className="system-text">
      <strong>API Request</strong>
      <span>{data.method || 'GET'}: {data.apiUrl || 'No URL specified'}</span>
      <small>(Data is fetched and saved to attributes)</small>
    </div>
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
const AskQuestionPreview = ({ data }) => (
    <>
        {/* The question sent by the bot */}
        <div className="preview-bubble-outbound">
            <p className="preview-text">{data.questionText || '...'}</p>
        </div>
        {/* A placeholder for the user's expected reply */}
        <div className="preview-bubble-inbound">
             <p className="preview-text-user-reply">
                <em>User replies with text...</em><br/>
                <small>(Saves to attribute)</small>
            </p>
        </div>
    </>
);

const AskLocationPreview = ({ data }) => (
    <>
        {/* The request sent by the bot */}
        <div className="preview-bubble-outbound">
            <p className="preview-text">{data.questionText || 'Please share your location.'}</p>
            <div className="preview-buttons-footer location-request">
                <span className="location-icon">📍</span> Send Location
            </div>
        </div>
        {/* A placeholder for the user's expected reply */}
        <div className="preview-bubble-inbound-location">
             <img src="https://placehold.co/200x100/e9edef/667781?text=Map+Location" alt="Map Preview" />
             <p className="preview-text-user-reply">
                <em>User shares their location...</em><br/>
                <small>(Saves to attributes)</small>
            </p>
        </div>
    </>
);
const AskForImagePreview = ({ data }) => (
    <>
        {/* The request sent by the bot */}
        <div className="preview-bubble-outbound">
            <p className="preview-text">{data.questionText || 'Please send an image.'}</p>
        </div>
        {/* A placeholder for the user's expected reply */}
        <div className="preview-bubble-inbound-image">
             <div className="image-placeholder">🖼️</div>
             <p className="preview-text-user-reply">
                <em>User sends an image...</em><br/>
                <small>(Saves URL to attribute)</small>
            </p>
        </div>
    </>
);

// --- ADD THIS NEW COMPONENT TO THE BOTTOM OF YOUR FlowPreview.js FILE ---

const FormFlowPreview = ({ data }) => {
  // If no flow has been selected in the node yet, show a placeholder.
  if (!data.selectedFormId) {
    return (
      <div className="preview-bubble-outbound">
        <p className="preview-text"><em>A Flow trigger message will appear here once a flow is selected.</em></p>
      </div>
    );
  }

  // Once a flow is selected, show its body and button text.
  return (
    <div className="preview-bubble-outbound">
      <p className="preview-text" style={{ whiteSpace: 'pre-wrap' }}>
        {data.templateBody || '...'}
      </p>
      {/* This div mimics the appearance of a WhatsApp Flow button */}
      <div className="preview-buttons-footer flow-button">
        <span className="flow-icon">➔</span> {data.templateButtonText || 'Open Form'}
      </div>
    </div>
  );
};

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