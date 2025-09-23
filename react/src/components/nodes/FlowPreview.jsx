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
                    return <FlowFormPreview data={node.data} />;
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


const FlowFormPreview = ({ data }) => {
  const [showFlowModal, setShowFlowModal] = useState(false);
  const [currentScreenIndex, setCurrentScreenIndex] = useState(0);
  const [formData, setFormData] = useState({});

  const selectedForm = data.forms?.find(f => f.id === data.selectedFormId);

  if (!selectedForm) {
    return (
      <div className="preview-bubble-outbound">
        <p className="preview-text"><em>Select a form to see its preview.</em></p>
      </div>
    );
  }

  const templateBody = data.templateBody || selectedForm.template_body || '';
  const buttonText = data.buttonText || selectedForm.template_button_text || 'Open Form';
  const screens = selectedForm.screens_data || [];
  const currentScreen = screens[currentScreenIndex];

  const handleInputChange = (componentId, value) => {
    setFormData(prev => ({
      ...prev,
      [componentId]: value
    }));
  };

  const nextScreen = () => {
    if (currentScreenIndex < screens.length - 1) {
      setCurrentScreenIndex(prev => prev + 1);
    }
  };

  const prevScreen = () => {
    if (currentScreenIndex > 0) {
      setCurrentScreenIndex(prev => prev - 1);
    }
  };

  const closeFlow = () => {
    setShowFlowModal(false);
    setCurrentScreenIndex(0);
    setFormData({});
  };

  const renderFormComponent = (component) => {
    const componentId = component.id;
    const currentValue = formData[componentId] || '';

    switch (component.type) {
      case 'text-input':
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <input
              type="text"
              className="flow-form-input"
              placeholder={component.properties?.placeholder || ''}
              value={currentValue}
              onChange={(e) => handleInputChange(componentId, e.target.value)}
            />
          </div>
        );

      case 'textarea':
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <textarea
              className="flow-form-textarea"
              placeholder={component.properties?.placeholder || ''}
              rows={component.properties?.rows || 3}
              value={currentValue}
              onChange={(e) => handleInputChange(componentId, e.target.value)}
            />
          </div>
        );

      case 'dropdown':
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <select
              className="flow-form-select"
              value={currentValue}
              onChange={(e) => handleInputChange(componentId, e.target.value)}
            >
              <option value="">Select an option</option>
              {(component.properties?.options || []).map((option, index) => (
                <option key={index} value={option}>{option}</option>
              ))}
            </select>
          </div>
        );

      case 'date-picker':
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <input
              type="date"
              className="flow-form-input"
              value={currentValue}
              onChange={(e) => handleInputChange(componentId, e.target.value)}
            />
          </div>
        );

      case 'radio-group':
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <div className="flow-form-radio-group">
              {(component.properties?.options || []).map((option, index) => (
                <label key={index} className="flow-form-radio-label">
                  <input
                    type="radio"
                    name={componentId}
                    value={option}
                    checked={currentValue === option}
                    onChange={(e) => handleInputChange(componentId, e.target.value)}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 'checkbox-group':
        const selectedValues = Array.isArray(currentValue) ? currentValue : [];
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <div className="flow-form-checkbox-group">
              {(component.properties?.options || []).map((option, index) => (
                <label key={index} className="flow-form-checkbox-label">
                  <input
                    type="checkbox"
                    value={option}
                    checked={selectedValues.includes(option)}
                    onChange={(e) => {
                      const newValues = e.target.checked
                        ? [...selectedValues, option]
                        : selectedValues.filter(v => v !== option);
                      handleInputChange(componentId, newValues);
                    }}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 'heading':
        return (
          <div key={componentId} className="flow-form-heading">
            <h3>{component.label}</h3>
          </div>
        );

      case 'text':
        return (
          <div key={componentId} className="flow-form-text">
            <p>{component.properties?.content || component.label}</p>
          </div>
        );

      default:
        return (
          <div key={componentId} className="flow-form-field">
            <label className="flow-form-label">{component.label}</label>
            <div className="flow-form-unknown">Unsupported component type: {component.type}</div>
          </div>
        );
    }
  };

  return (
    <>
      {/* Initial template message */}
      <div className="preview-bubble-outbound">
        <p className="preview-text">{templateBody}</p>
        <div className="preview-buttons-footer">
          <div 
            className="preview-button-pill flow-button"
            onClick={() => setShowFlowModal(true)}
          >
            {buttonText}
          </div>
        </div>
      </div>

      {/* Flow Modal */}
      {showFlowModal && (
        <div className="flow-modal-overlay">
          <div className="flow-modal">
            {/* Header */}
            <div className="flow-modal-header">
              <h3>{currentScreen?.title || `Screen ${currentScreenIndex + 1}`}</h3>
              <button 
                className="flow-modal-close"
                onClick={closeFlow}
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="flow-modal-content">
              {currentScreen ? (
                <div className="flow-screen">
                  {currentScreen.components.map(renderFormComponent)}
                </div>
              ) : (
                <div className="flow-no-screens">
                  <p>No screens configured for this form.</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flow-modal-footer">
              <div className="flow-navigation">
                {currentScreenIndex > 0 && (
                  <button 
                    className="flow-nav-btn flow-prev-btn"
                    onClick={prevScreen}
                  >
                    Previous
                  </button>
                )}
                
                <span className="flow-screen-indicator">
                  {currentScreenIndex + 1} of {screens.length}
                </span>

                {currentScreenIndex < screens.length - 1 ? (
                  <button 
                    className="flow-nav-btn flow-next-btn"
                    onClick={nextScreen}
                  >
                    Next
                  </button>
                ) : (
                  <button 
                    className="flow-nav-btn flow-submit-btn"
                    onClick={() => {
                      closeFlow();
                      // In real implementation, this would submit the form
                    }}
                  >
                    Submit
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* User completion indicator */}
      {showFlowModal === false && formData && Object.keys(formData).length > 0 && (
        <div className="preview-bubble-inbound">
          <p className="preview-text-user-reply">
            <em>User completes form...</em><br/>
            <small>(Form data saved to attributes)</small>
          </p>
        </div>
      )}
    </>
  );
};

// CSS Styles for the Flow Form Preview
const FlowFormStyles = `
  .flow-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    cursor: pointer;
    transition: transform 0.2s;
  }

  .flow-button:hover {
    transform: scale(1.05);
  }

  .flow-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .flow-modal {
    background: white;
    border-radius: 12px;
    width: 90%;
    max-width: 400px;
    max-height: 90vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }

  .flow-modal-header {
    background: #25D366;
    color: white;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .flow-modal-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .flow-modal-close {
    background: none;
    border: none;
    color: white;
    font-size: 24px;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background 0.2s;
  }

  .flow-modal-close:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .flow-modal-content {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
  }

  .flow-screen {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .flow-form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .flow-form-label {
    font-weight: 600;
    color: #333;
    font-size: 14px;
  }

  .flow-form-input,
  .flow-form-textarea,
  .flow-form-select {
    padding: 12px;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.2s;
  }

  .flow-form-input:focus,
  .flow-form-textarea:focus,
  .flow-form-select:focus {
    outline: none;
    border-color: #25D366;
  }

  .flow-form-textarea {
    resize: vertical;
    min-height: 80px;
  }

  .flow-form-radio-group,
  .flow-form-checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .flow-form-radio-label,
  .flow-form-checkbox-label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 8px;
    border-radius: 6px;
    transition: background 0.2s;
  }

  .flow-form-radio-label:hover,
  .flow-form-checkbox-label:hover {
    background: #f8f9fa;
  }

  .flow-form-heading h3 {
    margin: 0;
    color: #333;
    font-size: 18px;
    border-bottom: 2px solid #25D366;
    padding-bottom: 8px;
  }

  .flow-form-text p {
    margin: 0;
    color: #666;
    line-height: 1.5;
  }

  .flow-form-unknown {
    background: #f8f9fa;
    border: 1px dashed #dee2e6;
    padding: 12px;
    border-radius: 6px;
    color: #6c757d;
    text-align: center;
    font-style: italic;
  }

  .flow-modal-footer {
    border-top: 1px solid #e1e5e9;
    padding: 16px 20px;
    background: #f8f9fa;
  }

  .flow-navigation {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .flow-nav-btn {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .flow-prev-btn {
    background: #6c757d;
    color: white;
  }

  .flow-prev-btn:hover {
    background: #5a6268;
  }

  .flow-next-btn {
    background: #007bff;
    color: white;
  }

  .flow-next-btn:hover {
    background: #0056b3;
  }

  .flow-submit-btn {
    background: #28a745;
    color: white;
  }

  .flow-submit-btn:hover {
    background: #218838;
  }

  .flow-screen-indicator {
    font-size: 14px;
    color: #6c757d;
    font-weight: 500;
  }

  .flow-no-screens {
    text-align: center;
    padding: 40px 20px;
    color: #6c757d;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = FlowFormStyles;
  document.head.appendChild(styleElement);
}

export default FlowFormPreview;