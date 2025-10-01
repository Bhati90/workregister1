import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './AIFlowGenerator.css';

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

const EnhancedAIFlowGenerator = () => {
  const navigate = useNavigate();
  
  // Main states
  const [step, setStep] = useState(1); // 1: Requirements, 2: Template Creation, 3: Flow Generated
  const [requirements, setRequirements] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  // Analysis results
  const [analysis, setAnalysis] = useState(null);
  const [missingTemplates, setMissingTemplates] = useState([]);
  const [flowPlan, setFlowPlan] = useState(null);
  
  // Template creation
  const [currentTemplateIndex, setCurrentTemplateIndex] = useState(0);
  const [templateData, setTemplateData] = useState(null);
  const [mediaFile, setMediaFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTemplates, setCreatedTemplates] = useState([]);
  const [templateStatuses, setTemplateStatuses] = useState({});
  
  // Final flow
  const [generatedFlow, setGeneratedFlow] = useState(null);
  const [error, setError] = useState('');

  // Step 1: Analyze Requirements
  const handleAnalyze = async () => {
    if (!requirements.trim()) {
      setError('Please describe your requirements');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    
    try {
      const response = await axios.post(`${API_URL}/api/flows/generate-smart/`, {
        user_info: requirements
      });

      if (response.data.status === 'templates_needed') {
        // Templates missing - go to creation step
        setAnalysis(response.data.analysis);
        setMissingTemplates(response.data.missing_templates);
        setFlowPlan(response.data.flow_plan);
        setStep(2);
        
        // Initialize first template
        if (response.data.missing_templates.length > 0) {
          prepareTemplateCreation(response.data.missing_templates[0]);
        }
      } else if (response.data.status === 'success') {
        // All templates exist - flow generated immediately
        setGeneratedFlow(response.data.flow);
        setStep(3);
      } else {
        setError(response.data.message || 'Failed to analyze requirements');
      }
    } catch (error) {
      setError(error.response?.data?.message || 'Analysis failed');
      console.error('Analysis error:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Prepare template creation UI
  const prepareTemplateCreation = (templateReq) => {
    const { suggested_name, template_requirements } = templateReq;
    
    setTemplateData({
      name: suggested_name,
      language: 'en',
      category: template_requirements.category,
      components: buildComponents(template_requirements)
    });
  };

  const buildComponents = (requirements) => {
    const components = [];
    
    // Header (if media needed)
    if (requirements.needs_media) {
      components.push({
        type: 'HEADER',
        format: 'IMAGE'
      });
    }
    
    // Body
    components.push({
      type: 'BODY',
      text: requirements.body_text,
      example: {
        body_text: [requirements.variables?.map(v => v.example) || []]
      }
    });
    
    // Buttons
    if (requirements.needs_buttons) {
      components.push({
        type: 'BUTTONS',
        buttons: requirements.button_options.map(text => ({
          type: 'QUICK_REPLY',
          text
        }))
      });
    }
    
    return components;
  };

  // Submit current template to Meta
  const handleSubmitTemplate = async () => {
    const currentTemplate = missingTemplates[currentTemplateIndex];
    
    if (currentTemplate.template_requirements.needs_media && !mediaFile) {
      alert('Please upload media file');
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
        const templateName = response.data.template_name;
        
        // Track created template
        setCreatedTemplates(prev => [...prev, templateName]);
        setTemplateStatuses(prev => ({
          ...prev,
          [templateName]: 'PENDING'
        }));
        
        // Start polling for this template
        startPollingTemplate(templateName);
        
        // Move to next template or wait for approval
        if (currentTemplateIndex < missingTemplates.length - 1) {
          setCurrentTemplateIndex(prev => prev + 1);
          prepareTemplateCreation(missingTemplates[currentTemplateIndex + 1]);
          setMediaFile(null);
        } else {
          // All templates submitted - wait for approvals
          alert('All templates submitted! Waiting for Meta approval...');
        }
      } else {
        alert('Submission failed: ' + response.data.message);
      }
    } catch (error) {
      alert('Error submitting template: ' + (error.response?.data?.message || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Poll template status
  const startPollingTemplate = (templateName) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/template-flow/status/${templateName}/`);
        
        if (response.data.status === 'success') {
          const status = response.data.template_status;
          
          setTemplateStatuses(prev => ({
            ...prev,
            [templateName]: status
          }));
          
          if (status === 'APPROVED' || status === 'REJECTED') {
            clearInterval(interval);
            
            // Check if all templates are resolved
            checkAllTemplatesReady();
          }
        }
      } catch (error) {
        console.error('Error checking template status:', error);
      }
    }, 10000); // Check every 10 seconds
  };

  // Check if all templates are approved
  const checkAllTemplatesReady = async () => {
    const allApproved = createdTemplates.every(
      name => templateStatuses[name] === 'APPROVED'
    );
    
    const anyRejected = createdTemplates.some(
      name => templateStatuses[name] === 'REJECTED'
    );
    
    if (anyRejected) {
      alert('Some templates were rejected. Please review and resubmit.');
      return;
    }
    
    if (allApproved && createdTemplates.length === missingTemplates.length) {
      // All approved - automatically resume flow creation
      alert('All templates approved! Creating flow now...');
      await resumeFlowCreation();
    }
  };

  // Resume flow creation after templates approved
  const resumeFlowCreation = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/flows/resume-with-templates/`, {
        original_requirements: requirements,
        flow_plan: flowPlan,
        created_templates: createdTemplates
      });

      if (response.data.status === 'success') {
        setGeneratedFlow(response.data.flow);
        setStep(3);
      } else if (response.data.status === 'waiting') {
        // Some templates still pending
        alert('Waiting for remaining templates to be approved');
      } else {
        setError('Failed to create flow: ' + response.data.message);
      }
    } catch (error) {
      setError('Error creating flow: ' + (error.response?.data?.message || error.message));
    }
  };

  // Update template field
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

  // Render functions
  const renderStepContent = () => {
    switch (step) {
      case 1:
        return renderRequirementsStep();
      case 2:
        return renderTemplateCreationStep();
      case 3:
        return renderFlowGeneratedStep();
      default:
        return null;
    }
  };

  const renderRequirementsStep = () => (
    <div className="step-content">
      <h2>Describe Your Flow Requirements</h2>
      <p>Our AI will analyze if existing templates work, or pause to create new ones if needed.</p>
      
      <textarea
        value={requirements}
        onChange={(e) => setRequirements(e.target.value)}
        placeholder="Example: I need a farmer onboarding flow. Welcome them, ask what crop they grow, request their farm location, ask how many laborers needed, and send them available worker profiles."
        rows={8}
      />

      <div className="example-prompts">
        <p><strong>Example for Farmer-Labor Platform:</strong></p>
        <div className="prompt-item" onClick={() => setRequirements("Create farmer registration flow: welcome message, ask crop type, request farm location, ask land size, collect contact number, confirm registration.")}>
          Farmer Registration Flow
        </div>
        <div className="prompt-item" onClick={() => setRequirements("Labor booking flow: show available workers with skills, let farmer select workers, ask work date and duration, collect location, send booking confirmation.")}>
          Labor Booking Flow
        </div>
        <div className="prompt-item" onClick={() => setRequirements("Service inquiry flow: present farming services (seeds, equipment, consultation), collect requirements, ask budget, request callback time.")}>
          Service Inquiry Flow
        </div>
      </div>

      <button onClick={handleAnalyze} disabled={isAnalyzing} className="primary-button">
        {isAnalyzing ? 'Analyzing...' : 'Analyze & Generate'}
      </button>

      {error && <div className="error-box">{error}</div>}
    </div>
  );

  const renderTemplateCreationStep = () => {
    const currentTemplate = missingTemplates[currentTemplateIndex];
    const progress = `${currentTemplateIndex + 1} of ${missingTemplates.length}`;
    const allSubmitted = createdTemplates.length === missingTemplates.length;
    const allApproved = createdTemplates.every(name => templateStatuses[name] === 'APPROVED');
    
    return (
      <div className="step-content">
        <h2>Template Creation Required</h2>
        
        <div className="template-progress">
          <p>Creating template {progress}</p>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{width: `${((currentTemplateIndex + 1) / missingTemplates.length) * 100}%`}}
            />
          </div>
        </div>

        {allSubmitted && !allApproved && (
          <div className="info-box" style={{background: '#fff3e0', padding: '16px', borderRadius: '8px', marginBottom: '20px'}}>
            <p style={{margin: 0, color: '#e65100'}}>
              <strong>⏳ Waiting for Meta Approval</strong><br/>
              All templates have been submitted. Checking status every 10 seconds...<br/>
              This typically takes 15 minutes to 2 hours.
            </p>
          </div>
        )}

        {allApproved && (
          <div className="success-box" style={{background: '#e8f5e9', padding: '16px', borderRadius: '8px', marginBottom: '20px'}}>
            <p style={{margin: 0, color: '#2e7d32'}}>
              <strong>✓ All Templates Approved!</strong><br/>
              Ready to create your flow.
            </p>
          </div>
        )}

        <div className="analysis-info">
          <h3>Why this template is needed:</h3>
          <p>{currentTemplate.reason}</p>
          
          <h4>Flow Plan:</h4>
          <ol className="flow-steps">
            {flowPlan.steps.map((s, i) => (
              <li key={i} className={s.status === 'missing' ? 'missing' : 'ready'}>
                <strong>Step {s.step}:</strong> {s.action}
                <span className={`status-badge ${s.status}`}>{s.status}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="template-editor">
          <h3>Template: {currentTemplate.purpose}</h3>
          
          <div className="field-group">
            <label>Template Name:</label>
            <input
              type="text"
              value={templateData?.name || ''}
              onChange={(e) => updateTemplateField('name', e.target.value)}
            />
          </div>

          <div className="field-group">
            <label>Category:</label>
            <select
              value={templateData?.category || 'UTILITY'}
              onChange={(e) => updateTemplateField('category', e.target.value)}
            >
              <option value="UTILITY">Utility</option>
              <option value="MARKETING">Marketing</option>
            </select>
          </div>

          {templateData?.components?.map((comp, index) => (
            <div key={index} className="component-editor">
              <h4>{comp.type}</h4>
              
              {comp.type === 'BODY' && (
                <textarea
                  value={comp.text}
                  onChange={(e) => updateComponent(index, 'text', e.target.value)}
                  rows={4}
                />
              )}
              
              {comp.type === 'HEADER' && comp.format === 'IMAGE' && (
                <div className="field-group">
                  <label>Upload Image:</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setMediaFile(e.target.files[0])}
                  />
                  {mediaFile && <small>Selected: {mediaFile.name}</small>}
                </div>
              )}
              
              {comp.type === 'BUTTONS' && (
                <div className="buttons-preview">
                  <p>Buttons:</p>
                  {comp.buttons.map((btn, i) => (
                    <div key={i} className="button-pill">{btn.text}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="button-group">
          <button onClick={() => setStep(1)} className="secondary-button">
            Back
          </button>
          <button 
            onClick={handleSubmitTemplate} 
            disabled={isSubmitting}
            className="primary-button"
          >
            {isSubmitting ? 'Submitting...' : 'Submit to Meta'}
          </button>
        </div>

        {/* Show status of all templates */}
        {createdTemplates.length > 0 && (
          <div className="templates-status">
            <h4>Template Status:</h4>
            {createdTemplates.map(name => (
              <div key={name} className="status-row">
                <span>{name}</span>
                <span className={`status-badge ${templateStatuses[name]?.toLowerCase()}`}>
                  {templateStatuses[name] || 'SUBMITTING'}
                </span>
              </div>
            ))}
            
            {/* Manual flow creation button */}
            {createdTemplates.every(name => templateStatuses[name] === 'APPROVED') && (
              <button 
                onClick={resumeFlowCreation}
                className="primary-button"
                style={{marginTop: '20px'}}
              >
                ✓ All Approved - Create Flow Now
              </button>
            )}
            
            {createdTemplates.some(name => templateStatuses[name] === 'REJECTED') && (
              <div className="error-box" style={{marginTop: '20px'}}>
                Some templates were rejected. Please review in Meta Business Manager and resubmit.
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderFlowGeneratedStep = () => (
    <div className="step-content">
      <h2>Flow Generated Successfully!</h2>
      
      <div className="flow-info">
        <div className="info-row">
          <strong>Flow Name:</strong>
          <span>{generatedFlow?.name}</span>
        </div>
        <div className="info-row">
          <strong>Template:</strong>
          <span>{generatedFlow?.template_name}</span>
        </div>
        <div className="info-row">
          <strong>Flow ID:</strong>
          <span>#{generatedFlow?.id}</span>
        </div>
      </div>

      {generatedFlow?.explanation && (
        <div className="explanation">
          <h3>Design Explanation:</h3>
          <p>{generatedFlow.explanation}</p>
        </div>
      )}

      {generatedFlow?.created_attributes?.length > 0 && (
        <div className="attributes-box">
          <h3>Auto-Created Attributes:</h3>
          <ul>
            {generatedFlow.created_attributes.map((attr, i) => (
              <li key={i}>{attr}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flow-stats">
        <div className="stat-item">
          <span className="stat-number">{generatedFlow?.flow_data?.nodes?.length || 0}</span>
          <span className="stat-label">Nodes</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{generatedFlow?.flow_data?.edges?.length || 0}</span>
          <span className="stat-label">Connections</span>
        </div>
      </div>

      <div className="button-group">
        <button 
          onClick={() => navigate(`/edit-flow/${generatedFlow.id}`)}
          className="primary-button"
        >
          View & Edit Flow
        </button>
        <button 
          onClick={() => {
            setStep(1);
            setRequirements('');
            setGeneratedFlow(null);
            setCreatedTemplates([]);
            setTemplateStatuses({});
          }}
          className="secondary-button"
        >
          Create Another Flow
        </button>
      </div>
    </div>
  );

  return (
    <div className="enhanced-flow-generator">
      <div className="header">
        <h1>AI Flow Generator</h1>
        <p>Intelligent template detection - Creates missing templates automatically</p>
      </div>

      <div className="progress-indicator">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>1. Requirements</div>
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>2. Templates</div>
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>3. Flow Ready</div>
      </div>

      <div className="content-container">
        {renderStepContent()}
      </div>
    </div>
  );
};

export default EnhancedAIFlowGenerator;