import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './FlowListPage.css'; // Reuse styles for consistency

const API_URL = 'https://workregister1-8g56.onrender.com/register/whatsapp/api/attributes/';

const AttributesPage = () => {
    const [attributes, setAttributes] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetchAttributes();
    }, []);

    const fetchAttributes = () => {
        setIsLoading(true);
        axios.get(API_URL)
            .then(res => setAttributes(res.data))
            .catch(err => console.error("Error fetching attributes:", err))
            .finally(() => setIsLoading(false));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        axios.post(API_URL, { name, description })
            .then(() => {
                fetchAttributes();
                setName('');
                setDescription('');
            })
            .catch(err => alert("Error creating attribute. Name may already exist."));
    };

    const handleDelete = (id) => {
        if (window.confirm("Are you sure you want to delete this attribute?")) {
            axios.delete(`${API_URL}${id}/`)
                .then(() => fetchAttributes())
                .catch(err => alert("Error deleting attribute."));
        }
    };

    return (
        <div className="flow-list-page">
            <main className="main-content">
                <header className="page-header">
                    <h1>Manage Attributes</h1>
                    <button onClick={() => navigate('/')} className="create-flow-btn">← Back to Flows</button>
                </header>

                <div className="card">
                    <h2>Create New Attribute</h2>
                    <form onSubmit={handleSubmit} className="attribute-form">
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Attribute Name (e.g., email, city)"
                            required
                        />
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Description (optional)"
                        />
                        <button type="submit">Create Attribute</button>
                    </form>
                </div>

                <div className="card flow-table-card">
                    <table className="flow-table">
                        <thead>
                            <tr>
                                <th>Attribute Name</th>
                                <th>Description</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {isLoading ? (
                                <tr><td colSpan="3">Loading...</td></tr>
                            ) : attributes.map(attr => (
                                <tr key={attr.id}>
                                    <td>{attr.name}</td>
                                    <td>{attr.description}</td>
                                    <td className="actions">
                                        <button onClick={() => handleDelete(attr.id)} className="action-btn delete">🗑️ Delete</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </main>
        </div>
    );
};

export default AttributesPage;