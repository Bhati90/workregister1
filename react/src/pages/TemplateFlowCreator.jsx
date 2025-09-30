import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './TemplateFlowCreator.css';

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

const TemplateFlowCreator = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Requirements, 2: Preview, 3: Submission, 4: Polling
  const [requirements, setRequirements] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [templateData, setTemplateData] = useState(null);
  const [mediaFile, setMediaFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedTemplate, setSubmittedTemplate] = useState(null);
  const [templateStatus, setTemplateStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);

  // Step 1: Analyze Requirements
  const handleAnalyze = async () => {
    if (!requirements.trim()) {
      alert('Please describe your requirements');
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await axios.post(`${API_URL}/api/template-flow/analyze/`, {
        requirements
      });

      if (response.data.status === 'success') {
        setAnalysis(response.data.analysis);
        
        if (response.data.analysis.recommendation === 'use_existing') {
          // Show existing template recommendation
          alert(`Existing template recommended: ${response.data.analysis.existing_template}`);
        } else {
          // Prepare new template data
          setTemplateData(response.data.analysis.new_template);
          setStep(2);
        }
      }
    } catch (error) {
      alert('Error analyzing requirements: ' + (error.response?.data?.message || error.message));
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Step 2: Edit Template (allow modifications)
  const updateTemplateField = (field, value) => {
    setTemplateData(prev => ({ ...prev, [field]: value }));
  };

  const updateComponent = (index, field, value) => {
    setTemplateData(prev => {
      const newComponents = [...prev.components];
      newComponents[index] = { ...newComponents[index], [field]: value };
      return { ...prev, components: newComponents };
    });
  };

  // Step 3: Submit to Meta
  const handleSubmitToMeta = async () => {
    if (analysis.needs_media && !mediaFile) {
      alert('Please upload media file required for this template');
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('template_data', JSON.stringify(templateData));
      if (mediaFile) {
        formData.append('media_file', mediaFile);
      }

      const response = await axios.post(`${API_URL}/api/template-flow/submit/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.status === 'success') {
        setSubmittedTemplate({
          name: response.data.template_name,
          id: response.data.template_id
        });
        setStep(4);
        startPolling(response.data.template_name);
      } else {
        alert('Submission failed: ' + response.data.message);
      }
    } catch (error) {
      alert('Error submitting template: ' + (error.response?.data?.message || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Step 4: Poll for approval status
  const startPolling = (templateName) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/template-flow/status/${templateName}/`);
        
        if (response.data.status === 'success') {
          const status = response.data.template_status;
          setTemplateStatus(status);
          
          if (status === 'APPROVED') {
            clearInterval(interval);
            // Automatically create flow
            await createFlowAfterApproval(templateName);
          } else if (status === 'REJECTED') {
            clearInterval(interval);
            alert('Template was rejected by Meta. Please review and resubmit.');
          }
        }
      } catch (error) {
        console.error('Error checking status:', error);
      }
    }, 10000); // Check every 10 seconds

    setPollingInterval(interval);
  };

  const createFlowAfterApproval = async (templateName) => {
    try {
      const response = await axios.post(`${API_URL}/api/template-flow/create-flow/`, {
        template_name: templateName,
        original_requirements: requirements,
        suggested_flow: analysis.suggested_flow
      });

      if (response.data.status === 'success') {
        alert('Flow created successfully! Redirecting to flow editor...');
        navigate(`/edit-flow/${response.data.flow.id}`);
      }
    } catch (error) {
      console.error('Error creating flow:', error);
      alert('Template approved but flow creation failed. Please create flow manually.');
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="step-content">
            <h2>Describe Your Requirements</h2>
            <p>Tell us what you want to achieve with your WhatsApp flow. Our AI will analyze if an existing template works or create a new one.</p>
            
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="Example: I need a restaurant booking system where customers can view menu, select items, provide delivery address, and make payment. Send confirmation with estimated delivery time."
              rows={8}
            />

            <div className="example-prompts">
              <p><strong>Example Requirements:</strong></p>
              <div className="prompt-list">
                <div onClick={() => setRequirements("Create a customer support flow for an e-commerce store. Handle order status inquiries, returns, refunds, and product questions.")}>
                  E-commerce Customer Support
                </div>
                <div onClick={() => setRequirements("Build an appointment booking system for a dental clinic. Collect patient name, phone, preferred date/time, and reason for visit.")}>
                  Appointment Booking
                </div>
                <div onClick={() => setRequirements("Design a lead generation flow for real estate. Ask for budget, location preference, property type, and contact details.")}>
                  Real Estate Lead Gen
                </div>
              </div>
            </div>

            <button 
              onClick={handleAnalyze} 
              disabled={isAnalyzing}
              className="primary-button"
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Requirements'}
            </button>
          </div>
        );

      case 2:
        return (
          <div className="step-content">
            <h2>Review & Edit Template</h2>
            
            {analysis && (
              <div className="analysis-box">
                <h3>AI Analysis</h3>
                <p><strong>Recommendation:</strong> Create new template</p>
                <p><strong>Reasoning:</strong> {analysis.reasoning}</p>
              </div>
            )}

            <div className="template-editor">
              <div className="field-group">
                <label>Template Name:</label>
                <input
                  type="text"
                  value={templateData?.name || ''}
                  onChange={(e) => updateTemplateField('name', e.target.value)}
                  placeholder="my_template_name"
                />
                <small>Lowercase, underscores only</small>
              </div>

              <div className="field-group">
                <label>Language:</label>
                <select
                  value={templateData?.language || 'en'}
                  onChange={(e) => updateTemplateField('language', e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="es">Spanish</option>
                  <option value="pt_BR">Portuguese (Brazil)</option>
                </select>
              </div>

              <div className="field-group">
                <label>Category:</label>
                <select
                  value={templateData?.category || 'UTILITY'}
                  onChange={(e) => updateTemplateField('category', e.target.value)}
                >
                  <option value="UTILITY">Utility</option>
                  <option value="MARKETING">Marketing</option>
                  <option value="AUTHENTICATION">Authentication</option>
                </select>
              </div>

              {templateData?.components?.map((component, index) => (
                <div key={index} className="component-editor">
                  <h4>{component.type}</h4>
                  
                  {component.type === 'BODY' && (
                    <textarea
                      value={component.text}
                      onChange={(e) => updateComponent(index, 'text', e.target.value)}
                      rows={4}
                      placeholder="Body text with {{1}} variables"
                    />
                  )}

                  {component.type === 'HEADER' && component.format === 'TEXT' && (
                    <input
                      type="text"
                      value={component.text}
                      onChange={(e) => updateComponent(index, 'text', e.target.value)}
                      placeholder="Header text"
                    />
                  )}

                  {component.type === 'FOOTER' && (
                    <input
                      type="text"
                      value={component.text}
                      onChange={(e) => updateComponent(index, 'text', e.target.value)}
                      placeholder="Footer text (max 60 chars)"
                    />
                  )}
                </div>
              ))}

              {analysis?.needs_media && (
                <div className="field-group">
                  <label>Upload Media ({analysis.media_type}):</label>
                  <input
                    type="file"
                    accept={
                      analysis.media_type === 'image' ? 'image/*' :
                      analysis.media_type === 'video' ? 'video/*' :
                      '*/*'
                    }
                    onChange={(e) => setMediaFile(e.target.files[0])}
                  />
                  {mediaFile && <small>Selected: {mediaFile.name}</small>}
                </div>
              )}

              {analysis?.variables_needed && analysis.variables_needed.length > 0 && (
                <div className="variables-box">
                  <h4>Variables in Template:</h4>
                  <ul>
                    {analysis.variables_needed.map((v, i) => (
                      <li key={i}>
                        <strong>{'{{' + (i + 1) + '}}'}</strong> = {v.name} 
                        <small>({v.description}, e.g., "{v.example}")</small>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="button-group">
              <button onClick={() => setStep(1)} className="secondary-button">
                Back
              </button>
              <button onClick={() => setStep(3)} className="primary-button">
                Preview & Submit
              </button>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="step-content">
            <h2>Final Preview</h2>
            
            <div className="preview-box">
              <h3>Template: {templateData?.name}</h3>
              <div className="preview-message">
                {templateData?.components?.map((comp, index) => (
                  <div key={index} className={`preview-${comp.type.toLowerCase()}`}>
                    {comp.type === 'HEADER' && comp.format === 'TEXT' && (
                      <div className="preview-header">{comp.text}</div>
                    )}
                    {comp.type === 'HEADER' && comp.format !== 'TEXT' && (
                      <div className="preview-media">
                        [{comp.format} - {mediaFile ? mediaFile.name : 'No file uploaded'}]
                      </div>
                    )}
                    {comp.type === 'BODY' && (
                      <div className="preview-body">
                        {comp.text.replace(/\{\{(\d+)\}\}/g, (match, num) => {
                          const varIndex = parseInt(num) - 1;
                          return analysis?.variables_needed?.[varIndex]?.example || match;
                        })}
                      </div>
                    )}
                    {comp.type === 'FOOTER' && (
                      <div className="preview-footer">{comp.text}</div>
                    )}
                    {comp.type === 'BUTTONS' && (
                      <div className="preview-buttons">
                        {comp.buttons.map((btn, i) => (
                          <button key={i} className="preview-button">{btn.text}</button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="warning-box">
              <p><strong>Important:</strong> Once submitted, this template will be sent to Meta for review. 
              This typically takes a few hours to a few days. You'll be notified when approved.</p>
            </div>

            <div className="button-group">
              <button onClick={() => setStep(2)} className="secondary-button">
                Edit Template
              </button>
              <button 
                onClick={handleSubmitToMeta} 
                disabled={isSubmitting}
                className="primary-button submit-button"
              >
                {isSubmitting ? 'Submitting...' : 'Submit to Meta for Approval'}
              </button>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="step-content">
            <h2>Template Submitted</h2>
            
            <div className="status-box">
              <h3>Template: {submittedTemplate?.name}</h3>
              <p><strong>ID:</strong> {submittedTemplate?.id}</p>
              <p><strong>Status:</strong> <span className={`status-${templateStatus?.toLowerCase()}`}>
                {templateStatus || 'PENDING'}
              </span></p>
              
              {templateStatus === 'PENDING' && (
                <div className="polling-indicator">
                  <div className="spinner-small"></div>
                  <p>Waiting for Meta approval... This may take a few hours.</p>
                  <small>We're checking every 10 seconds. You can close this page and come back later.</small>
                </div>
              )}

              {templateStatus === 'APPROVED' && (
                <div className="success-message">
                  <h4>Template Approved!</h4>
                  <p>Your template has been approved by Meta. Creating your flow now...</p>
                </div>
              )}

              {templateStatus === 'REJECTED' && (
                <div className="error-message">
                  <h4>Template Rejected</h4>
                  <p>Meta rejected this template. Please review Meta's guidelines and try again.</p>
                  <button onClick={() => setStep(2)} className="primary-button">
                    Edit & Resubmit
                  </button>
                </div>
              )}
            </div>

            {analysis?.suggested_flow && (
              <div className="suggested-flow-box">
                <h3>Planned Flow (After Approval)</h3>
                <p>{analysis.suggested_flow.description}</p>
                <ol>
                  {analysis.suggested_flow.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
              </div>
            )}

            <button onClick={() => navigate('/')} className="secondary-button">
              Back to Dashboard
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="template-flow-creator">
      <div className="header">
        <h1>AI Template & Flow Creator</h1>
        <p>Let AI analyze your needs, create templates, and build flows automatically</p>
      </div>

      <div className="progress-bar">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>1. Requirements</div>
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>2. Edit Template</div>
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>3. Preview</div>
        <div className={`progress-step ${step >= 4 ? 'active' : ''}`}>4. Approval</div>
      </div>

      <div className="content-area">
        {renderStepContent()}
      </div>
    </div>
  );
};

export default TemplateFlowCreator;