import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './AIFlowGenerator.css';

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

const FlexibleFlowGenerator = () => {
  const navigate = useNavigate();
  
  // Main states
  const [step, setStep] = useState(1); // 1: Requirements, 2: Review All Templates, 3: Submit Options
  const [requirements, setRequirements] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState('hi'); // hi, en, mr
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  // Analysis results
  const [analysis, setAnalysis] = useState(null);
  const [allTemplates, setAllTemplates] = useState([]); // All templates to create
  const [flowPlan, setFlowPlan] = useState(null);
  
  // User choices
  const [selectedTemplates, setSelectedTemplates] = useState([]); // Which templates user wants to create
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedTemplates, setSubmittedTemplates] = useState([]);
  
  const [error, setError] = useState('');

  // Step 1: Analyze Requirements
  const handleAnalyze = async () => {
    if (!requirements.trim()) {
      setError('कृपया आवश्यकता वर्णन करा / Please describe requirements');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    
    try {
      const response = await axios.post(`${API_URL}/api/flows/analyze-with-language/`, {
        user_info: requirements,
        preferred_language: preferredLanguage
      });

      if (response.data.status === 'success') {
        setAnalysis(response.data.analysis);
        setAllTemplates(response.data.missing_templates || []);
        setFlowPlan(response.data.flow_plan);
        
        if (response.data.missing_templates && response.data.missing_templates.length > 0) {
          // Show all templates for review
          setStep(2);
          // Pre-select all templates
          setSelectedTemplates(response.data.missing_templates.map((_, i) => i));
        } else {
          // No templates needed, go directly to flow creation
          alert('सर्व templates उपलब्ध आहेत! / All templates available!');
          await createFlowDirectly();
        }
      }
    } catch (error) {
      setError(error.response?.data?.message || 'विश्लेषण अयशस्वी / Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Toggle template selection
  const toggleTemplate = (index) => {
    setSelectedTemplates(prev => {
      if (prev.includes(index)) {
        return prev.filter(i => i !== index);
      } else {
        return [...prev, index];
      }
    });
  };

  // Update template field
  const updateTemplate = (index, field, value) => {
    setAllTemplates(prev => {
      const updated = [...prev];
      if (field === 'language') {
        updated[index].template_requirements.language = value;
      } else if (field === 'category') {
        updated[index].template_requirements.category = value;
      } else if (field.includes('.')) {
        // Nested field like template_requirements.body_text
        const [parent, child] = field.split('.');
        updated[index][parent][child] = value;
      } else {
        updated[index][field] = value;
      }
      return updated;
    });
  };

  // Submit selected templates to Meta
  const handleSubmitToMeta = async () => {
    if (selectedTemplates.length === 0) {
      alert('कृपया किमान एक template निवडा / Please select at least one template');
      return;
    }

    setIsSubmitting(true);
    const submitted = [];
    
    for (const index of selectedTemplates) {
      const template = allTemplates[index];
      
      try {
        const templateData = {
          name: template.suggested_name,
          language: template.template_requirements.language || preferredLanguage,
          category: template.template_requirements.category,
          components: buildComponents(template.template_requirements)
        };

        const response = await axios.post(`${API_URL}/api/template-flow/submit/`, 
          { template_data: JSON.stringify(templateData) },
          { headers: { 'Content-Type': 'application/json' } }
        );

        if (response.data.status === 'success') {
          submitted.push({
            name: response.data.template_name,
            id: response.data.template_id,
            status: 'PENDING'
          });
        }
      } catch (error) {
        console.error(`Template ${index} submission failed:`, error);
      }
    }
    
    setSubmittedTemplates(submitted);
    setIsSubmitting(false);
    
    if (submitted.length > 0) {
      setStep(3);
      // Start polling
      submitted.forEach(t => startPolling(t.name));
    } else {
      alert('सर्व templates submit करण्यात अयशस्वी / All submissions failed');
    }
  };

  // Skip template creation and go to flow
  const skipTemplatesAndCreateFlow = async () => {
    if (window.confirm('Templates न बनवता flow तयार करायचा? / Create flow without new templates?')) {
      await createFlowDirectly();
    }
  };

  // Create flow without waiting for templates
  const createFlowDirectly = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/flows/generate-ai/`, {
        user_info: requirements
      });

      if (response.data.status === 'success') {
        alert('Flow तयार झाला! / Flow created!');
        navigate(`/flow/${response.data.flow.id}`);
      }
    } catch (error) {
      setError('Flow तयार करण्यात त्रुटी / Flow creation failed');
    }
  };

  const buildComponents = (requirements) => {
    const components = [];
    
    // Body
    components.push({
      type: 'BODY',
      text: requirements.body_text,
      example: requirements.variables && requirements.variables.length > 0 ? {
        body_text: [requirements.variables.map(v => v.example)]
      } : undefined
    });
    
    // Buttons
    if (requirements.needs_buttons && requirements.button_options) {
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

  const startPolling = (templateName) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/api/template-flow/status/${templateName}/`);
        
        if (response.data.status === 'success') {
          const status = response.data.template_status;
          
          setSubmittedTemplates(prev => 
            prev.map(t => t.name === templateName ? {...t, status} : t)
          );
          
          if (status === 'APPROVED' || status === 'REJECTED') {
            clearInterval(interval);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 10000);
  };

  const allApproved = submittedTemplates.length > 0 && 
    submittedTemplates.every(t => t.status === 'APPROVED');

  // Render functions
  const renderStep1 = () => (
    <div className="step-content">
      <h2>आपली आवश्यकता सांगा / Describe Your Requirements</h2>
      
      <div className="language-selector">
        <label><strong>भाषा निवडा / Select Language:</strong></label>
        <div className="language-options">
          <button 
            className={`lang-btn ${preferredLanguage === 'hi' ? 'active' : ''}`}
            onClick={() => setPreferredLanguage('hi')}
          >
            मराठी/हिंदी
          </button>
          <button 
            className={`lang-btn ${preferredLanguage === 'en' ? 'active' : ''}`}
            onClick={() => setPreferredLanguage('en')}
          >
            English
          </button>
        </div>
      </div>

      <textarea
        value={requirements}
        onChange={(e) => setRequirements(e.target.value)}
        placeholder={preferredLanguage === 'hi' ? 
          "उदाहरण: शेतकरी नोंदणी flow - स्वागत संदेश, पीक विचारा, ठिकाण विचारा, मजूर संख्या, संपर्क क्रमांक..." :
          "Example: Farmer registration flow - welcome message, ask crop type, location, labor count, contact number..."
        }
        rows={8}
      />

      <div className="example-prompts">
        <p><strong>उदाहरणे / Examples:</strong></p>
        <div className="prompt-item" onClick={() => setRequirements(
          preferredLanguage === 'hi' ? 
          "शेतकरी नोंदणी: स्वागत, पीक प्रकार विचारा, शेताचे ठिकाण, मजूर संख्या, फोन नंबर, पुष्टीकरण" :
          "Farmer registration: Welcome, ask crop type, farm location, labor count, phone number, confirmation"
        )}>
          {preferredLanguage === 'hi' ? 'शेतकरी नोंदणी' : 'Farmer Registration'}
        </div>
        <div className="prompt-item" onClick={() => setRequirements(
          preferredLanguage === 'hi' ?
          "मजूर booking: सेवा दाखवा, मजूर निवडा, तारीख विचारा, ठिकाण, पुष्टीकरण" :
          "Labor booking: Show services, select workers, ask date, location, confirmation"
        )}>
          {preferredLanguage === 'hi' ? 'मजूर Booking' : 'Labor Booking'}
        </div>
      </div>

      <button onClick={handleAnalyze} disabled={isAnalyzing} className="primary-button">
        {isAnalyzing ? 'विश्लेषण करत आहे... / Analyzing...' : 'विश्लेषण करा / Analyze'}
      </button>

      {error && <div className="error-box">{error}</div>}
    </div>
  );

  const renderStep2 = () => (
    <div className="step-content">
      <h2>Template आढावा / Template Review</h2>
      
      <div className="analysis-summary">
        <p><strong>आवश्यक Templates:</strong> {allTemplates.length}</p>
        <p><strong>निवडलेले:</strong> {selectedTemplates.length}</p>
      </div>

      <div className="templates-grid">
        {allTemplates.map((template, index) => (
          <div key={index} className={`template-card ${selectedTemplates.includes(index) ? 'selected' : ''}`}>
            <div className="template-header">
              <input 
                type="checkbox" 
                checked={selectedTemplates.includes(index)}
                onChange={() => toggleTemplate(index)}
              />
              <h3>{template.purpose}</h3>
            </div>

            <div className="template-body">
              <div className="field-group">
                <label>नाव / Name:</label>
                <input
                  type="text"
                  value={template.suggested_name}
                  onChange={(e) => updateTemplate(index, 'suggested_name', e.target.value)}
                />
              </div>

              <div className="field-row">
                <div className="field-group">
                  <label>Category:</label>
                  <select
                    value={template.template_requirements.category}
                    onChange={(e) => updateTemplate(index, 'category', e.target.value)}
                  >
                    <option value="UTILITY">Utility</option>
                    <option value="MARKETING">Marketing</option>
                  </select>
                </div>

                <div className="field-group">
                  <label>भाषा / Language:</label>
                  <select
                    value={template.template_requirements.language || preferredLanguage}
                    onChange={(e) => updateTemplate(index, 'language', e.target.value)}
                  >
                    <option value="hi">मराठी/हिंदी</option>
                    <option value="en">English</option>
                    <option value="en_US">English (US)</option>
                  </select>
                </div>
              </div>

              <div className="field-group">
                <label>मजकूर / Content:</label>
                <textarea
                  value={template.template_requirements.body_text}
                  onChange={(e) => updateTemplate(index, 'template_requirements.body_text', e.target.value)}
                  rows={4}
                />
              </div>

              {template.template_requirements.button_options && (
                <div className="buttons-preview">
                  <label>Buttons:</label>
                  {template.template_requirements.button_options.map((btn, i) => (
                    <span key={i} className="button-pill">{btn}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="action-section">
        <h3>पुढे काय करायचे? / What Next?</h3>
        <div className="button-group">
          <button onClick={handleSubmitToMeta} disabled={isSubmitting} className="primary-button">
            {isSubmitting ? 'Submitting...' : `${selectedTemplates.length} Templates Meta ला सबमिट करा / Submit to Meta`}
          </button>
          <button onClick={skipTemplatesAndCreateFlow} className="secondary-button">
            Templates वगळा, Flow तयार करा / Skip & Create Flow
          </button>
          <button onClick={() => setStep(1)} className="secondary-button">
            मागे / Back
          </button>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="step-content">
      <h2>Template Status</h2>
      
      <div className="templates-status">
        {submittedTemplates.map((template, i) => (
          <div key={i} className="status-row">
            <span>{template.name}</span>
            <span className={`status-badge ${template.status.toLowerCase()}`}>
              {template.status}
            </span>
          </div>
        ))}
      </div>

      {allApproved && (
        <div className="success-box" style={{marginTop: '20px'}}>
          <p><strong>✓ सर्व Templates मंजूर!</strong></p>
          <button onClick={createFlowDirectly} className="primary-button">
            Flow आता तयार करा / Create Flow Now
          </button>
        </div>
      )}

      {!allApproved && (
        <div className="info-box">
          <p>⏳ Meta च्या मंजुरीची प्रतीक्षा... / Waiting for Meta approval...</p>
          <p style={{fontSize: '0.9rem'}}>सामान्यपणे 15 मिनिटे - 2 तास लागतात / Usually takes 15min - 2 hours</p>
        </div>
      )}

      <div className="button-group" style={{marginTop: '20px'}}>
        <button onClick={skipTemplatesAndCreateFlow} className="secondary-button">
          प्रतीक्षा न करता Flow तयार करा / Create Flow Without Waiting
        </button>
        <button onClick={() => navigate('/')} className="secondary-button">
          Dashboard वर परत या / Back to Dashboard
        </button>
      </div>
    </div>
  );

  return (
    <div className="flexible-flow-generator">
      <div className="header">
        <h1>🤖 AI Flow Generator</h1>
        <p>पूर्ण नियंत्रण तुमच्या हातात / Full Control in Your Hands</p>
      </div>

      <div className="progress-indicator">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
          1. आवश्यकता / Requirements
        </div>
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
          2. Templates आढावा / Review
        </div>
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
          3. Submit & Flow
        </div>
      </div>

      <div className="content-container">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </div>
    </div>
  );
};

export default FlexibleFlowGenerator;