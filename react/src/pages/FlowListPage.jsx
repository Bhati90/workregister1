// src/pages/FlowListPage.jsx - Updated version
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './FlowListPage.css';

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp';

const FlowListPage = () => {
  const [flows, setFlows] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchFlows();
  }, []);

  const fetchFlows = () => {
    setLoading(true);
    setError(null);
    
    axios.get(`${API_URL}/api/flows/list/`)
      .then(response => {
        setFlows(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching flows:", error);
        setError("Failed to load flows. Please try again.");
        setLoading(false);
      });
  };

  const handleDelete = (flowId) => {
    if (window.confirm("Are you sure you want to delete this flow?")) {
      axios.delete(`${API_URL}/api/flows/${flowId}/delete/`)
        .then(response => {
          if (response.data.status === 'success') {
            alert("Flow deleted successfully.");
            fetchFlows(); // Refresh the list
          } else {
            alert(`Error: ${response.data.message}`);
          }
        })
        .catch(error => {
          console.error("Error deleting flow:", error);
          alert("Failed to delete flow.");
        });
    }
  };
  
  const handleStatusToggle = (flowId, currentStatus) => {
    axios.post(`${API_URL}/api/flows/${flowId}/status/`, { is_active: !currentStatus })
      .then(response => {
        if (response.data.status === 'success') {
          // Optimistically update the UI
          setFlows(flows.map(f => f.id === flowId ? { ...f, is_active: !currentStatus } : f));
        } else {
          alert(`Error: ${response.data.message}`);
        }
      })
      .catch(error => {
        console.error("Error updating status:", error);
        alert("Failed to update status.");
      });
  };

  const filteredFlows = flows.filter(flow =>
    flow.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  };

  return (
    <div className="flow-list-page">
      <main className="main-content">
        <header className="page-header">
          <h1>Flows</h1>
          <Link to="/attributes" className="manage-attr-btn">Manage Attributes</Link>
          <Link to="/flow/new" className="create-flow-btn">
            + Create Flow
          </Link>
          <Link to="/ai-flow-generator">AI Flow Generator</Link>
          <Link to="/ai-tem-generator">AI Flow Generator temp</Link>
        </header>

        <div className="card quota-card">
          <span>Total Flows</span>
          <strong>{flows.length}</strong>
        </div>

        <div className="card flow-table-card">
          <div className="table-controls">
            <input
              type="text"
              placeholder="Search by flow name"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <button onClick={fetchFlows} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {error && (
            <div className="error-message" style={{
              padding: '10px',
              background: '#fee',
              color: '#c00',
              borderRadius: '4px',
              margin: '10px 0'
            }}>
              {error}
            </div>
          )}

          <table className="flow-table">
            <thead>
              <tr>
                <th>Flow Name</th>
                <th>Template</th>
                <th>Status</th>
                <th>Last Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="5">Loading flows...</td></tr>
              ) : filteredFlows.length > 0 ? (
                filteredFlows.map(flow => (
                  <tr key={flow.id}>
                    <td>
                      <strong>{flow.name}</strong>
                    </td>
                    <td>
                      <span className="template-name">
                        {flow.template_name || 'No template'}
                      </span>
                    </td>
                    <td>
                      <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={flow.is_active} 
                          onChange={() => handleStatusToggle(flow.id, flow.is_active)} 
                        />
                        <span className="slider round"></span>
                      </label>
                      <span className="status-text">
                        {flow.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <span className="date-text">
                        {formatDate(flow.updated_at)}
                      </span>
                    </td>
                    <td className="actions">
                      <Link to={`/flow/${flow.id}`} className="action-btn edit">
                        ✏️ Edit
                      </Link>
                      <button 
                        onClick={() => handleDelete(flow.id)} 
                        className="action-btn delete"
                      >
                        🗑️ Delete
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5">
                    {searchTerm ? 'No flows match your search.' : 'No flows found. Create your first flow!'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default FlowListPage;