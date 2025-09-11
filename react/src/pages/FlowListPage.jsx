// src/pages/FlowListPage.jsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './FlowListPage.css'; // We'll create this CSS file next

const API_URL = 'http://127.0.0.1:8000/register/whatsapp'; // Your Django backend URL

const FlowListPage = () => {
  const [flows, setFlows] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFlows();
  }, []);

  const fetchFlows = () => {
    setLoading(true);
    axios.get(`${API_URL}/api/flows/list/`)
      .then(response => {
        setFlows(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Error fetching flows:", error);
        setLoading(false);
      });
  };

  const handleDelete = (flowId) => {
    if (window.confirm("Are you sure you want to delete this flow?")) {
      axios.delete(`${API_URL}/api/flows/${flowId}/delete/`)
        .then(() => {
          alert("Flow deleted successfully.");
          fetchFlows(); // Refresh the list
        })
        .catch(error => {
          console.error("Error deleting flow:", error);
          alert("Failed to delete flow.");
        });
    }
  };
  
  const handleStatusToggle = (flowId, currentStatus) => {
    axios.post(`${API_URL}/api/flows/${flowId}/status/`, { is_active: !currentStatus })
      .then(() => {
        // Optimistically update the UI
        setFlows(flows.map(f => f.id === flowId ? { ...f, is_active: !currentStatus } : f));
      })
      .catch(error => {
        console.error("Error updating status:", error);
        alert("Failed to update status.");
      });
  };

  const filteredFlows = flows.filter(flow =>
    flow.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flow-list-page">
      {/* <aside className="sidebar-nav">
        You can build out this sidebar as needed
        <div className="sidebar-nav-item active">Flow Builder</div> 
         ... other items ... 
      </aside> */}
      <main className="main-content">
        <header className="page-header">
          <h1>Flows</h1>
          <Link to="/flow/new" className="create-flow-btn">
            + Create Flow
          </Link>
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
          </div>
          <table className="flow-table">
            <thead>
              <tr>
                <th>Flow Name</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="3">Loading flows...</td></tr>
              ) : filteredFlows.length > 0 ? (
                filteredFlows.map(flow => (
                  <tr key={flow.id}>
                    <td>{flow.name}</td>
                    <td>
                      <label className="switch">
                        <input type="checkbox" checked={flow.is_active} onChange={() => handleStatusToggle(flow.id, flow.is_active)} />
                        <span className="slider round"></span>
                      </label>
                    </td>
                    <td className="actions">
                      <Link to={`/flow/${flow.id}`} className="action-btn">✏️ Edit</Link>
                      <button onClick={() => handleDelete(flow.id)} className="action-btn delete">🗑️ Delete</button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan="3">No flows found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default FlowListPage;