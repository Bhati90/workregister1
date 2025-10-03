import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import './AnalyticsPage.css';

const API_URL = 'http://127.0.0.1:8000/register/api/analytics';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1943'];

const AnalyticsPage = () => {
    // Existing states
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStep, setLoadingStep] = useState('');
    const [error, setError] = useState(null);
    const [generatedSql, setGeneratedSql] = useState(null);
    const [usedTables, setUsedTables] = useState([]);
    const [fullSchema, setFullSchema] = useState("");
    const [testResults, setTestResults] = useState(null);
    const [finalResults, setFinalResults] = useState(null);
    const [chartType, setChartType] = useState('table');

    // New states for AI Analysis
    const [aiAnalysis, setAiAnalysis] = useState(null);
    const [flowPrompts, setFlowPrompts] = useState(null);
    const [selectedSegment, setSelectedSegment] = useState(null);
    const [segmentDetails, setSegmentDetails] = useState(null);
    const [activeTab, setActiveTab] = useState('query'); // 'query' or 'ai-analysis'
    const [autoAnalyzing, setAutoAnalyzing] = useState(false);

    // Auto-run analysis on component mount
    useEffect(() => {
        handleAutoAnalysis();
    }, []);

    const handleAutoAnalysis = async () => {
        setAutoAnalyzing(true);
        setError(null);
        try {
            const response = await axios.post(`${API_URL}/auto-analyze-farmers/`);
            setAiAnalysis(response.data.analysis);
            setFlowPrompts(response.data.flow_prompts);
        } catch (err) {
            console.error("Auto-analysis error:", err);
            setError("Could not perform automatic farmer analysis: " + (err.response?.data?.message || err.message));
        } finally {
            setAutoAnalyzing(false);
        }
    };

    const handleSegmentClick = async (segment) => {
        setSelectedSegment(segment);
        setIsLoading(true);
        try {
            const response = await axios.post(`${API_URL}/segment-details/`, {
                segment_id: segment.segment_id
            });
            setSegmentDetails(response.data);
        } catch (err) {
            setError("Could not load segment details: " + (err.response?.data?.message || err.message));
        } finally {
            setIsLoading(false);
        }
    };

    const copyPromptToClipboard = (promptText) => {
        navigator.clipboard.writeText(promptText);
        alert("Prompt copied to clipboard!");
    };

    const handleQuerySubmit = async (e) => {
        e.preventDefault();
        if (!query.trim()) {
            setError("Please enter a query.");
            return;
        }
        setIsLoading(true);
        setLoadingStep('generate');
        setError(null);
        setGeneratedSql(null);
        setTestResults(null);
        setFinalResults(null);

        try {
            const response = await axios.post(`${API_URL}/generate-query/`, { query });
            const { sql_query, used_tables, full_schema } = response.data;

            if (sql_query.includes("-- Failed")) {
                setError("The AI could not understand your query. Please try rephrasing it.");
                setIsLoading(false);
                return;
            }

            setGeneratedSql(sql_query);
            setUsedTables(used_tables);
            setFullSchema(full_schema);

            setLoadingStep('test');
            const testResponse = await axios.post(`${API_URL}/execute-query/`, { sql_query, test_run: true });
            setTestResults(testResponse.data.results);

        } catch (err) {
            setError(err.response?.data?.error || "An unexpected error occurred.");
        } finally {
            setIsLoading(false);
            setLoadingStep('');
        }
    };
    
    const handleFullExecution = async () => {
        setIsLoading(true);
        setLoadingStep('execute');
        setError(null);
        try {
            const response = await axios.post(`${API_URL}/execute-query/`, { sql_query: generatedSql, test_run: false });
            setFinalResults(response.data.results);
            setChartType(response.data.chart_type);
        } catch (err) {
            setError(err.response?.data?.error || "An unexpected error occurred during full execution.");
        } finally {
            setIsLoading(false);
            setLoadingStep('');
        }
    };
    
    const highlightSchema = () => {
        let highlighted = fullSchema;
        usedTables.forEach(table => {
            const regex = new RegExp(`(CREATE TABLE ${table})`, "g");
            highlighted = highlighted.replace(regex, `<span class="highlight">$1</span>`);
        });
        return { __html: highlighted };
    };

    const renderChart = () => {
        if (!finalResults || finalResults.length === 0) {
            return <p>The full query returned no results.</p>;
        }

        const keys = Object.keys(finalResults[0]);

        switch (chartType) {
            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height={400}>
                        <BarChart data={finalResults} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={keys[0]} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey={keys[1]} fill="#8884d8" />
                        </BarChart>
                    </ResponsiveContainer>
                );
            case 'pie':
                 return (
                    <ResponsiveContainer width="100%" height={400}>
                        <PieChart>
                            <Pie data={finalResults} dataKey={keys[1]} nameKey={keys[0]} cx="50%" cy="50%" outerRadius={150} fill="#8884d8" label>
                                {finalResults.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                );
            default:
                return (
                    <div className="table-container">
                        <table>
                           <thead>
                               <tr>{keys.map(key => <th key={key}>{key}</th>)}</tr>
                           </thead>
                           <tbody>
                               {finalResults.map((row, index) => (
                                   <tr key={index}>{Object.values(row).map((val, i) => <td key={i}>{String(val)}</td>)}</tr>
                               ))}
                           </tbody>
                       </table>
                    </div>
                );
        }
    };

    const renderAIAnalysis = () => {
        if (autoAnalyzing) {
            return (
                <div className="loading-analysis">
                    <div className="spinner"></div>
                    <p>🤖 AI is analyzing your farmer data...</p>
                </div>
            );
        }

        if (!aiAnalysis) {
            return (
                <div className="no-analysis">
                    <p>No analysis available.</p>
                    <button onClick={handleAutoAnalysis}>Run Analysis</button>
                </div>
            );
        }

        return (
            <div className="ai-analysis-container">
                {/* Summary Section */}
                <div className="analysis-summary">
                    <h2>📊 Farmer Analysis Summary</h2>
                    <div className="summary-stats">
                        <div className="stat-card">
                            <h3>{aiAnalysis.analysis_summary.total_farmers}</h3>
                            <p>Total Farmers</p>
                        </div>
                        <div className="stat-card">
                            <h3>{aiAnalysis.segments?.length || 0}</h3>
                            <p>Segments Identified</p>
                        </div>
                        <div className="stat-card">
                            <h3>{aiAnalysis.immediate_opportunities?.length || 0}</h3>
                            <p>Opportunities</p>
                        </div>
                    </div>
                    
                    <div className="key-insights">
                        <h3>🎯 Key Insights</h3>
                        <ul>
                            {aiAnalysis.analysis_summary.key_insights?.map((insight, idx) => (
                                <li key={idx}>{insight}</li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Segments Section */}
                <div className="segments-section">
                    <h2>👥 Farmer Segments</h2>
                    <div className="segments-grid">
                        {aiAnalysis.segments?.map((segment, idx) => (
                            <div 
                                key={idx} 
                                className={`segment-card priority-${segment.priority.toLowerCase()}`}
                                onClick={() => handleSegmentClick(segment)}
                            >
                                <div className="segment-header">
                                    <h3>{segment.segment_name}</h3>
                                    <span className={`badge priority-${segment.priority.toLowerCase()}`}>
                                        {segment.priority}
                                    </span>
                                </div>
                                <div className="segment-stats">
                                    <p><strong>{segment.farmer_count}</strong> farmers</p>
                                    <p className="conversion">Conversion: <strong>{segment.conversion_potential}</strong></p>
                                    <p className="revenue">Revenue: <strong>{segment.estimated_revenue}</strong></p>
                                </div>
                                <div className="segment-characteristics">
                                    {segment.characteristics?.slice(0, 3).map((char, i) => (
                                        <span key={i} className="characteristic-tag">{char}</span>
                                    ))}
                                </div>
                                <button className="view-details-btn">View Details →</button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Flow Prompts Section */}
                <div className="flow-prompts-section">
                    <h2>🚀 Ready-to-Use Flow Prompts</h2>
                    <p className="section-description">
                        Copy these prompts and use them to create WhatsApp flows that will convert your farmers into customers.
                    </p>
                    
                    {flowPrompts?.flow_prompts?.map((prompt, idx) => (
                        <div key={idx} className={`prompt-card priority-${prompt.priority.toLowerCase()}`}>
                            <div className="prompt-header">
                                <h3>
                                    {prompt.prompt_title}
                                    <span className={`badge priority-${prompt.priority.toLowerCase()}`}>
                                        {prompt.priority}
                                    </span>
                                </h3>
                                <p className="prompt-meta">
                                    Target: <strong>{prompt.segment_targeted}</strong> | 
                                    Language: <strong>{prompt.language}</strong> | 
                                    Expected Conversion: <strong>{prompt.estimated_conversion_rate}</strong>
                                </p>
                            </div>
                            
                            <div className="prompt-content">
                                <h4>📝 Full Prompt (Copy This):</h4>
                                <div className="prompt-text">
                                    <pre>{prompt.full_prompt}</pre>
                                    <button 
                                        className="copy-btn"
                                        onClick={() => copyPromptToClipboard(prompt.full_prompt)}
                                    >
                                        📋 Copy Prompt
                                    </button>
                                </div>
                            </div>
                            
                            <div className="prompt-details">
                                <p><strong>Expected Templates:</strong> {prompt.expected_templates}</p>
                                <div className="implementation-notes">
                                    <h4>Implementation Notes:</h4>
                                    <ul>
                                        {prompt.implementation_notes?.map((note, i) => (
                                            <li key={i}>{note}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Immediate Opportunities */}
                <div className="opportunities-section">
                    <h2>💰 Immediate Revenue Opportunities</h2>
                    <div className="opportunities-grid">
                        {aiAnalysis.immediate_opportunities?.map((opp, idx) => (
                            <div key={idx} className="opportunity-card">
                                <h3>{opp.opportunity}</h3>
                                <p className="revenue-potential">Potential Revenue: <strong>{opp.potential_revenue}</strong></p>
                                <p className="difficulty">Difficulty: <span className={`badge-${opp.implementation_difficulty}`}>{opp.implementation_difficulty}</span></p>
                                <div className="action-items">
                                    <h4>Action Items:</h4>
                                    <ol>
                                        {opp.action_items?.map((item, i) => (
                                            <li key={i}>{item}</li>
                                        ))}
                                    </ol>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Automation Recommendations */}
                <div className="automation-section">
                    <h2>🤖 Automation Recommendations</h2>
                    {aiAnalysis.automation_recommendations?.map((auto, idx) => (
                        <div key={idx} className={`automation-card priority-${auto.implementation_priority.toLowerCase()}`}>
                            <h3>
                                {auto.automation_type}
                                <span className={`badge priority-${auto.implementation_priority.toLowerCase()}`}>
                                    {auto.implementation_priority}
                                </span>
                            </h3>
                            <p>{auto.description}</p>
                            <p className="target-segments">
                                Target Segments: {auto.target_segments?.join(', ')}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    const renderSegmentDetails = () => {
        if (!segmentDetails) return null;

        const detailed = segmentDetails.detailed_analysis;

        return (
            <div className="segment-details-modal">
                <div className="modal-content">
                    <button className="close-modal" onClick={() => setSegmentDetails(null)}>✕</button>
                    
                    <h2>{segmentDetails.segment.segment_name}</h2>
                    <p className="segment-description">{segmentDetails.segment.farmer_count} farmers | {segmentDetails.segment.conversion_potential} conversion potential</p>
                    
                    {detailed && (
                        <div className="segment-full-info">
                            {/* Stage Distribution */}
                            <div className="info-section">
                                <h3>📊 Stage Distribution Analysis</h3>
                                <div className="stage-breakdown">
                                    {detailed.stage_distribution?.breakdown?.map((stage, idx) => (
                                        <div key={idx} className={`stage-card urgency-${stage.urgency?.toLowerCase()}`}>
                                            <div className="stage-header">
                                                <h4>{stage.stage}</h4>
                                                <span className="stage-percentage">{stage.percentage}%</span>
                                            </div>
                                            <p className="farmer-count">{stage.farmer_count} farmers</p>
                                            <p className="urgency-badge">{stage.urgency} urgency</p>
                                            <p className="action-needed">{stage.action_needed}</p>
                                        </div>
                                    ))}
                                </div>
                                <div className="key-insights">
                                    <h4>Key Insights:</h4>
                                    <ul>
                                        {detailed.stage_distribution?.key_insights?.map((insight, i) => (
                                            <li key={i}>{insight}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            {/* Template Requirements */}
                            <div className="info-section">
                                <h3>📱 WhatsApp Template Requirements</h3>
                                <p className="section-hint">Check if these templates exist before creating flows</p>
                                
                                {detailed.template_requirements?.map((template, idx) => (
                                    <div key={idx} className={`template-card priority-${template.priority?.toLowerCase()}`}>
                                        <div className="template-header">
                                            <div>
                                                <h4>{template.template_name}</h4>
                                                <span className={`exists-badge ${template.likely_exists ? 'exists' : 'needs-creation'}`}>
                                                    {template.likely_exists ? '✓ Likely Exists' : '⚠ Needs Creation'}
                                                </span>
                                            </div>
                                            <span className={`priority-badge ${template.priority?.toLowerCase()}`}>
                                                {template.priority}
                                            </span>
                                        </div>
                                        
                                        <div className="template-meta">
                                            <span>Type: {template.template_type}</span>
                                            <span>Language: {template.language}</span>
                                            <span>Context: {template.usage_context}</span>
                                        </div>
                                        
                                        <div className="template-body">
                                            <h5>Body Text:</h5>
                                            <pre>{template.body_text}</pre>
                                        </div>
                                        
                                        <div className="template-variables">
                                            <h5>Variables:</h5>
                                            {template.variables?.map((v, i) => (
                                                <div key={i} className="variable-item">
                                                    <code>{v.position}</code> = {v.name} 
                                                    <span className="example">(e.g., "{v.example}")</span>
                                                </div>
                                            ))}
                                        </div>
                                        
                                        {template.buttons && template.buttons.length > 0 && (
                                            <div className="template-buttons">
                                                <h5>Buttons:</h5>
                                                {template.buttons.map((btn, i) => (
                                                    <button key={i} className="template-button-preview">
                                                        {btn.text}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Flow Creation Prompts */}
                            <div className="info-section highlight-section">
                                <h3>🤖 AI Flow Creation Prompts</h3>
                                <p className="section-hint">Copy these prompts to your AI flow maker</p>
                                
                                {detailed.flow_creation_prompts?.map((flowPrompt, idx) => (
                                    <div key={idx} className="flow-prompt-card">
                                        <h4>{flowPrompt.prompt_title}</h4>
                                        
                                        <div className="prompt-meta-info">
                                            <div className="meta-item">
                                                <strong>Required Templates:</strong>
                                                <div className="template-tags">
                                                    {flowPrompt.required_templates?.map((t, i) => (
                                                        <span key={i} className="template-tag">{t}</span>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="meta-item">
                                                <strong>Expected Outcome:</strong> {flowPrompt.expected_outcome}
                                            </div>
                                        </div>
                                        
                                        <div className="prompt-box">
                                            <div className="prompt-header-bar">
                                                <span>Complete Prompt (Copy This)</span>
                                                <button 
                                                    className="copy-prompt-btn"
                                                    onClick={() => copyPromptToClipboard(flowPrompt.complete_prompt)}
                                                >
                                                    📋 Copy to Clipboard
                                                </button>
                                            </div>
                                            <pre className="prompt-text">{flowPrompt.complete_prompt}</pre>
                                        </div>
                                        
                                        <div className="implementation-notes">
                                            <h5>Implementation Notes:</h5>
                                            <ul>
                                                {flowPrompt.implementation_notes?.map((note, i) => (
                                                    <li key={i}>{note}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Implementation Checklist */}
                            <div className="info-section">
                                <h3>✅ Implementation Checklist</h3>
                                <div className="checklist">
                                    {detailed.implementation_checklist?.map((step, idx) => (
                                        <div key={idx} className="checklist-item">
                                            <div className="step-number">{step.step}</div>
                                            <div className="step-content">
                                                <h5>{step.action}</h5>
                                                <p>{step.details}</p>
                                                <div className="step-meta">
                                                    <span className="timeline">Timeline: {step.timeline}</span>
                                                    <span className="responsible">Responsible: {step.responsible}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Revenue Breakdown */}
                            {detailed.revenue_breakdown && (
                                <div className="info-section revenue-section">
                                    <h3>💰 Revenue Breakdown</h3>
                                    <div className="revenue-stats">
                                        <div className="revenue-stat">
                                            <span className="label">Per Farmer Value</span>
                                            <span className="value">{detailed.revenue_breakdown.per_farmer_value}</span>
                                        </div>
                                        <div className="revenue-stat highlight">
                                            <span className="label">Total Potential</span>
                                            <span className="value">{detailed.revenue_breakdown.total_potential}</span>
                                        </div>
                                    </div>
                                    <p className="assumptions">{detailed.revenue_breakdown.conversion_assumptions}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {!detailed && (
                        <div className="loading-details">
                            <div className="spinner"></div>
                            <p>Loading detailed analysis...</p>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="analytics-page">
            <header className="analytics-header">
                <h1>🧠 AI-Powered Farmer Analytics</h1>
                <div className="tab-navigation">
                    <button 
                        className={activeTab === 'ai-analysis' ? 'active' : ''}
                        onClick={() => setActiveTab('ai-analysis')}
                    >
                        🤖 AI Analysis & Prompts
                    </button>
                    <button 
                        className={activeTab === 'query' ? 'active' : ''}
                        onClick={() => setActiveTab('query')}
                    >
                        💬 Natural Language Query
                    </button>
                </div>
            </header>

            {error && <div className="error-message">{error}</div>}

            {activeTab === 'ai-analysis' && renderAIAnalysis()}
            
            {activeTab === 'query' && (
                <>
                    <div className="query-input-section">
                        <p>Ask a question about your data in plain English.</p>
                        <form onSubmit={handleQuerySubmit}>
                            <textarea
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="e.g., Show me farmers who haven't been contacted in the last 30 days"
                                disabled={isLoading}
                            />
                            <button type="submit" disabled={isLoading}>
                                {isLoading && loadingStep === 'generate' ? 'Generating SQL...' : 
                                 isLoading && loadingStep === 'test' ? 'Running Test...' : 'Generate & Test Query'}
                            </button>
                        </form>
                    </div>

                    {generatedSql && (
                        <div className="results-section confirmation-step">
                            <h2>Step 1: Confirmation</h2>
                            <div className="sql-schema-container">
                                <div className="schema-display">
                                    <h3>Database Schema</h3>
                                    <pre dangerouslySetInnerHTML={highlightSchema()}></pre>
                                </div>
                                <div className="sql-display">
                                    <h3>Generated SQL Query</h3>
                                    <pre>{generatedSql}</pre>
                                </div>
                            </div>

                            <h3>Test Run Results (First 100 Rows)</h3>
                            <div className="table-container">
                               {testResults && testResults.length > 0 ? (
                                   <table>
                                       <thead>
                                           <tr>{Object.keys(testResults[0]).map(key => <th key={key}>{key}</th>)}</tr>
                                       </thead>
                                       <tbody>
                                           {testResults.map((row, index) => (
                                               <tr key={index}>{Object.values(row).map((val, i) => <td key={i}>{String(val)}</td>)}</tr>
                                           ))}
                                       </tbody>
                                   </table>
                               ) : <p>The test query returned no results.</p>}
                            </div>
                            
                            <button onClick={handleFullExecution} disabled={isLoading} className="execute-full-btn">
                                 {isLoading && loadingStep === 'execute' ? 'Executing Full Query...' : 'Looks Good! Run Full Query & Visualize'}
                            </button>
                        </div>
                    )}
                    
                    {finalResults && (
                        <div className="results-section final-step">
                            <h2>Step 2: Final Results</h2>
                            <div className="chart-container">
                               {renderChart()}
                            </div>
                        </div>
                    )}
                </>
            )}

            {segmentDetails && renderSegmentDetails()}
        </div>
    );
};

export default AnalyticsPage;