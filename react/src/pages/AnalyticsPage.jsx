import React, { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import './AnalyticsPage.css'; // We will create this file for styling

// IMPORTANT: Update this to your Django backend's URL
const API_URL = 'https://workregister1-8g56.onrender.com/register/api/analytics';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1943'];

const AnalyticsPage = () => {
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStep, setLoadingStep] = useState('');
    const [error, setError] = useState(null);
    
    // State to hold the results from the backend
    const [generatedSql, setGeneratedSql] = useState(null);
    const [usedTables, setUsedTables] = useState([]);
    const [fullSchema, setFullSchema] = useState("");
    const [testResults, setTestResults] = useState(null);
    const [finalResults, setFinalResults] = useState(null);
    const [chartType, setChartType] = useState('table');

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
            // Step 1: Send natural language query to get SQL
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

            // Step 2: Automatically run the test query
            setLoadingStep('test');
            const testResponse = await axios.post(`${API_URL}/execute-query/`, { sql_query, test_run: true });
            setTestResults(testResponse.data.results);

        } catch (err) {
            setError(err.response?.data?.error || "An unexpected error occurred. Check the backend console for details.");
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
            // Step 3: Run the full query
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
            default: // table
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

    return (
        <div className="analytics-page">
            <header className="analytics-header">
                <h1>Natural Language Database Query</h1>
                <p>Ask a question about your data in plain English. For example: "How many contacts do I have in each city?"</p>
            </header>

            <div className="query-input-section">
                <form onSubmit={handleQuerySubmit}>
                    <textarea
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="e.g., Show me the total number of flows created, grouped by template name"
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={isLoading}>
                        {isLoading && loadingStep === 'generate' ? 'Generating SQL...' : 
                         isLoading && loadingStep === 'test' ? 'Running Test...' : 'Generate & Test Query'}
                    </button>
                </form>
            </div>
            
            {error && <div className="error-message">{error}</div>}

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
        </div>
    );
};

export default AnalyticsPage;