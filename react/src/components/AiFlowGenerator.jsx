
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

const AIFlowGenerator = () => {
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedFlow, setGeneratedFlow] = useState(null);
  const [error, setError] = useState('');
  const [allFlows, setAllFlows] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchAllFlows();
  }, []);

  const fetchAllFlows = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/flows/ai-list/`);
      if (response.data.status === 'success') {
        setAllFlows(response.data.flows);
      }
    } catch (error) {
      console.error('Error fetching flows:', error);
    }
  };

  const handleGenerate = async () => {
    if (!userInfo.trim()) {
      setError('Please provide user information');
      return;
    }

    setIsGenerating(true);
    setError('');
    setGeneratedFlow(null);

    try {
      const response = await axios.post(`${API_URL}/api/flows/generate-ai/`, {
        user_info: userInfo
      });

      if (response.data.status === 'success') {
        setGeneratedFlow(response.data.flow);
        fetchAllFlows(); // Refresh the list
      } else {
        setError(response.data.message || 'Failed to generate flow');
      }
    } catch (error) {
      setError(error.response?.data?.message || 'An error occurred while generating the flow');
      console.error('Generation error:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleViewFlow = (flowId) => {
    navigate(`/edit-flow/${flowId}`);
  };

  const examplePrompts = [
    "Create a customer support flow for a restaurant. Users should be able to check menu, make reservations, and ask questions about dietary restrictions.",
    "Build a lead generation flow for a real estate company. Collect name, email, budget range, and preferred location.",
    "Design an appointment booking flow for a dental clinic. Ask for patient name, preferred date, time slot, and reason for visit.",
    "Create an order tracking flow for an e-commerce store. Users can check order status, request returns, and contact support."
  ];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>AI Flow Generator</h1>
        <p style={styles.subtitle}>Describe your requirements and let AI create the perfect WhatsApp flow</p>
      </div>

      <div style={styles.content}>
        <div style={styles.leftPanel}>
          <div style={styles.card}>
            <h2 style={styles.cardTitle}>Describe Your Flow Requirements</h2>
            
            <textarea
              style={styles.textarea}
              value={userInfo}
              onChange={(e) => setUserInfo(e.target.value)}
              placeholder="Example: I need a customer support flow for my restaurant. Customers should be able to view the menu, make reservations, ask about ingredients, and contact us for special requests."
              rows={8}
            />

            <div style={styles.examplesSection}>
              <h3 style={styles.examplesTitle}>Example Prompts:</h3>
              {examplePrompts.map((prompt, index) => (
                <div
                  key={index}
                  style={styles.examplePrompt}
                  onClick={() => setUserInfo(prompt)}
                >
                  {prompt}
                </div>
              ))}
            </div>

            <button
              style={{
                ...styles.generateButton,
                ...(isGenerating ? styles.generatingButton : {})
              }}
              onClick={handleGenerate}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <>
                  <span style={styles.spinner}></span>
                  Generating Flow...
                </>
              ) : (
                'Generate Flow'
              )}
            </button>

            {error && (
              <div style={styles.errorBox}>
                <strong>Error:</strong> {error}
              </div>
            )}
          </div>

          {generatedFlow && (
            <div style={styles.card}>
              <h2 style={styles.cardTitle}>Generated Flow</h2>
              
              <div style={styles.flowInfo}>
                <div style={styles.infoRow}>
                  <strong>Flow Name:</strong>
                  <span>{generatedFlow.name}</span>
                </div>
                <div style={styles.infoRow}>
                  <strong>Template:</strong>
                  <span>{generatedFlow.template_name}</span>
                </div>
                <div style={styles.infoRow}>
                  <strong>Flow ID:</strong>
                  <span>#{generatedFlow.id}</span>
                </div>
              </div>

              {generatedFlow.explanation && (
                <div style={styles.explanation}>
                  <h3 style={styles.explanationTitle}>Design Explanation:</h3>
                  <p style={styles.explanationText}>{generatedFlow.explanation}</p>
                </div>
              )}

              <div style={styles.flowStats}>
                <div style={styles.statItem}>
                  <span style={styles.statNumber}>
                    {generatedFlow.flow_data?.nodes?.length || 0}
                  </span>
                  <span style={styles.statLabel}>Nodes</span>
                </div>
                <div style={styles.statItem}>
                  <span style={styles.statNumber}>
                    {generatedFlow.flow_data?.edges?.length || 0}
                  </span>
                  <span style={styles.statLabel}>Connections</span>
                </div>
              </div>

              <div style={styles.actionButtons}>
                <button
                  style={styles.viewButton}
                  onClick={() => handleViewFlow(generatedFlow.id)}
                >
                  View & Edit Flow
                </button>
                <button
                  style={styles.secondaryButton}
                  onClick={() => setGeneratedFlow(null)}
                >
                  Generate Another
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={styles.rightPanel}>
          <div style={styles.card}>
            <div style={styles.historyHeader}>
              <h2 style={styles.cardTitle}>All Flows</h2>
              <button
                style={styles.refreshButton}
                onClick={fetchAllFlows}
              >
                Refresh
              </button>
            </div>

            {allFlows.length === 0 ? (
              <p style={styles.emptyState}>No flows generated yet</p>
            ) : (
              <div style={styles.flowsList}>
                {allFlows.map((flow) => (
                  <div
                    key={flow.id}
                    style={styles.flowCard}
                    onClick={() => handleViewFlow(flow.id)}
                  >
                    <div style={styles.flowCardHeader}>
                      <h3 style={styles.flowCardTitle}>{flow.name}</h3>
                      <span style={{
                        ...styles.statusBadge,
                        ...(flow.is_active ? styles.activeBadge : styles.inactiveBadge)
                      }}>
                        {flow.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div style={styles.flowCardDetails}>
                      <p style={styles.flowCardTemplate}>
                        Template: {flow.template_name}
                      </p>
                      <div style={styles.flowCardStats}>
                        <span>{flow.node_count} nodes</span>
                        <span>•</span>
                        <span>{flow.edge_count} connections</span>
                      </div>
                      <p style={styles.flowCardDate}>
                        Created: {new Date(flow.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: '20px'
  },
  header: {
    textAlign: 'center',
    marginBottom: '30px'
  },
  title: {
    fontSize: '2.5rem',
    color: '#333',
    marginBottom: '10px'
  },
  subtitle: {
    fontSize: '1.1rem',
    color: '#666'
  },
  content: {
    display: 'grid',
    gridTemplateColumns: '1fr 400px',
    gap: '20px',
    maxWidth: '1400px',
    margin: '0 auto'
  },
  leftPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px'
  },
  rightPanel: {
    display: 'flex',
    flexDirection: 'column'
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  },
  cardTitle: {
    fontSize: '1.5rem',
    color: '#333',
    marginBottom: '16px'
  },
  textarea: {
    width: '100%',
    padding: '12px',
    fontSize: '1rem',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    fontFamily: 'inherit',
    resize: 'vertical',
    marginBottom: '20px'
  },
  examplesSection: {
    marginBottom: '20px'
  },
  examplesTitle: {
    fontSize: '0.9rem',
    color: '#666',
    marginBottom: '10px'
  },
  examplePrompt: {
    padding: '10px',
    margin: '8px 0',
    backgroundColor: '#f8f8f8',
    borderRadius: '6px',
    fontSize: '0.9rem',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    border: '1px solid #e0e0e0'
  },
  generateButton: {
    width: '100%',
    padding: '14px',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#25D366',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    transition: 'background-color 0.2s'
  },
  generatingButton: {
    backgroundColor: '#1da851',
    cursor: 'not-allowed'
  },
  spinner: {
    width: '20px',
    height: '20px',
    border: '3px solid rgba(255,255,255,0.3)',
    borderTop: '3px solid white',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  errorBox: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#ffebee',
    border: '1px solid #ef5350',
    borderRadius: '6px',
    color: '#c62828'
  },
  flowInfo: {
    marginBottom: '20px'
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '10px 0',
    borderBottom: '1px solid #f0f0f0'
  },
  explanation: {
    marginTop: '20px',
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    borderLeft: '4px solid #25D366'
  },
  explanationTitle: {
    fontSize: '1rem',
    color: '#333',
    marginBottom: '8px'
  },
  explanationText: {
    fontSize: '0.95rem',
    color: '#555',
    lineHeight: '1.6'
  },
  flowStats: {
    display: 'flex',
    gap: '20px',
    marginTop: '20px'
  },
  statItem: {
    flex: 1,
    textAlign: 'center',
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px'
  },
  statNumber: {
    display: 'block',
    fontSize: '2rem',
    fontWeight: 'bold',
    color: '#25D366'
  },
  statLabel: {
    display: 'block',
    fontSize: '0.9rem',
    color: '#666',
    marginTop: '4px'
  },
  actionButtons: {
    display: 'flex',
    gap: '12px',
    marginTop: '20px'
  },
  viewButton: {
    flex: 1,
    padding: '12px',
    fontSize: '1rem',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#2196F3',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer'
  },
  secondaryButton: {
    flex: 1,
    padding: '12px',
    fontSize: '1rem',
    fontWeight: 'bold',
    color: '#333',
    backgroundColor: '#e0e0e0',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer'
  },
  historyHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px'
  },
  refreshButton: {
    padding: '8px 16px',
    fontSize: '0.9rem',
    color: '#2196F3',
    backgroundColor: 'transparent',
    border: '1px solid #2196F3',
    borderRadius: '6px',
    cursor: 'pointer'
  },
  emptyState: {
    textAlign: 'center',
    color: '#999',
    padding: '40px 20px'
  },
  flowsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    maxHeight: 'calc(100vh - 200px)',
    overflowY: 'auto'
  },
  flowCard: {
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
    border: '1px solid #e0e0e0'
  },
  flowCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'start',
    marginBottom: '12px'
  },
  flowCardTitle: {
    fontSize: '1rem',
    color: '#333',
    margin: 0,
    flex: 1
  },
  statusBadge: {
    padding: '4px 8px',
    fontSize: '0.75rem',
    borderRadius: '4px',
    fontWeight: 'bold'
  },
  activeBadge: {
    backgroundColor: '#c8e6c9',
    color: '#2e7d32'
  },
  inactiveBadge: {
    backgroundColor: '#ffccbc',
    color: '#d84315'
  },
  flowCardDetails: {
    fontSize: '0.85rem',
    color: '#666'
  },
  flowCardTemplate: {
    marginBottom: '8px',
    fontWeight: '500'
  },
  flowCardStats: {
    display: 'flex',
    gap: '8px',
    marginBottom: '8px'
  },
  flowCardDate: {
    fontSize: '0.8rem',
    color: '#999'
  }
};

export default AIFlowGenerator;