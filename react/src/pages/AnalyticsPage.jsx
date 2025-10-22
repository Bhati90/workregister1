import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Calendar, Users, Phone, MapPin, TrendingUp, AlertCircle } from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000/register/api/analytics';
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1943'];

const AnalyticsPage = () => {
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
    const [aiAnalysis, setAiAnalysis] = useState(null);
    const [flowPrompts, setFlowPrompts] = useState(null);
    const [selectedSegment, setSelectedSegment] = useState(null);
    const [segmentDetails, setSegmentDetails] = useState(null);
    const [segmentFarmers, setSegmentFarmers] = useState(null);
    const [calendarEvents, setCalendarEvents] = useState(null);
    const [activeTab, setActiveTab] = useState('ai-analysis');
    const [autoAnalyzing, setAutoAnalyzing] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [templateFarmers, setTemplateFarmers] = useState(null);
    const [selectedDate, setSelectedDate] = useState(null);
    const [calendarView, setCalendarView] = useState('upcoming');
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [calendarFilter, setCalendarFilter] = useState('all');
    const [cacheStatus, setCacheStatus] = useState(null);
    const [showQuotaWarning, setShowQuotaWarning] = useState(false);
    const [templatePrompts, setTemplatePrompts] = useState(null);
    const [segmentPackages, setSegmentPackages] = useState(null);

    useEffect(() => {
        checkCacheStatus(); 
        handleAutoAnalysis();
        loadCalendarEvents();
    }, []);

    const checkCacheStatus = async () => {
        try {
            const response = await axios.get(`${API_URL}/cache-status/`);
            setCacheStatus(response.data);
        } catch (err) {
            console.error("Cache status check failed:", err);
        }
    };

    const handleAutoAnalysis = async (forceRefresh = false) => {
    setAutoAnalyzing(true);
    setError(null);
    try {
        const formData = new FormData();
        formData.append('force_refresh', forceRefresh ? 'true' : 'false');
        
        const response = await axios.post(`${API_URL}/auto-analyze-farmers/`, formData);
        
        setAiAnalysis(response.data.analysis);
        setSegmentPackages(response.data.segment_packages);
        setFlowPrompts(response.data.flow_prompts);// NEW
        setCacheStatus({
            has_cache: true,
            cached_at: response.data.cached_at,
            from_cache: response.data.from_cache
        });
    } catch (err) {
        console.error("Auto-analysis error:", err);
        setError("Analysis failed: " + (err.response?.data?.message || err.message));
    } finally {
        setAutoAnalyzing(false);
    }
};

  const handleRefreshCache = async () => {
    // Confirm with user before making API call
    if (!window.confirm('⚠️ This will use an API call.\n\nFree tier: 50 calls/day\nAre you sure you want to refresh?')) {
        return;
    }
    
    setAutoAnalyzing(true);
    setError(null);
    setShowQuotaWarning(false);
    
    try {
        console.log("🔄 Starting cache refresh...");
        
        const response = await axios.post(`${API_URL}/refresh-cache/`);
        
        console.log("✅ Refresh response received:", response.data);
        console.log("📊 Analysis:", response.data.analysis);
        console.log("📦 Segment Packages:", response.data.segment_packages);
        console.log("🔄 Flow Prompts:", response.data.flow_prompts);
        
        // Validate response structure
        if (!response.data.analysis) {
            throw new Error("No analysis data in response");
        }
        
        // Update ALL state with refreshed data
        setAiAnalysis(response.data.analysis);
        
        // Set segment packages (new format with templates)
        if (response.data.segment_packages) {
            setSegmentPackages(response.data.segment_packages);
            console.log(`✅ Set ${response.data.segment_packages.segment_packages?.length || 0} segment packages`);
        } else {
            console.warn("⚠️ No segment_packages in response");
            setSegmentPackages({ segment_packages: [] });
        }
        
        // Set flow prompts (backward compatibility)
        if (response.data.flow_prompts) {
            setFlowPrompts(response.data.flow_prompts);
            console.log(`✅ Set ${response.data.flow_prompts.flow_prompts?.length || 0} flow prompts`);
        } else {
            console.warn("⚠️ No flow_prompts in response");
            setFlowPrompts({ flow_prompts: [] });
        }
         setFlowPrompts(response.data.flow_prompts);
         setSegmentPackages(response.data.segment_packages);
        
        
        // Update cache status
        setCacheStatus({
            has_cache: true,
            cached_at: response.data.cached_at || new Date().toISOString(),
            from_cache: false
        });
        
        // Count results
        const segmentCount = response.data.analysis?.segments?.length || 0;
        const opportunityCount = response.data.analysis?.immediate_opportunities?.length || 0;
        const automationCount = response.data.analysis?.automation_recommendations?.length || 0;
        const packageCount = response.data.segment_packages?.segment_packages?.length || 0;
        const promptCount = response.data.flow_prompts?.flow_prompts?.length || 0;
        
        console.log("📈 Results summary:", {
            segments: segmentCount,
            opportunities: opportunityCount,
            automations: automationCount,
            packages: packageCount,
            prompts: promptCount
        });
        
        // Show success message with details
        let message = '✅ Analysis refreshed successfully!\n\n';
        message += `📊 Segments: ${segmentCount}\n`;
        message += `💰 Opportunities: ${opportunityCount}\n`;
        message += `🤖 Automations: ${automationCount}\n`;
        message += `📱 Segment Packages: ${packageCount}\n`;
        message += `🔄 Flow Prompts: ${promptCount}\n\n`;
        
        if (packageCount === 0 && promptCount === 0) {
            message += '⚠️ Warning: No templates/prompts generated!\nCheck console for details.';
        }
        
        alert(message);
        
    } catch (err) {
        console.error("❌ Refresh error:", err);
        console.error("Error details:", err.response?.data);
        
        // Handle quota exceeded (429 error)
        if (err.response?.status === 429) {
            setShowQuotaWarning(true);
            setError(err.response.data.message || "API quota exceeded. Free tier: 50 requests/day. Please try again tomorrow.");
        } 
        // Handle other errors
        else {
            const errorMessage = err.response?.data?.message || err.message || "Unknown error occurred";
            setError(`Could not refresh analysis: ${errorMessage}`);
            
            // Show user-friendly error
            alert(`❌ Refresh Failed\n\n${errorMessage}\n\nCheck console (F12) for details.`);
        }
    } finally {
        setAutoAnalyzing(false);
        console.log("🏁 Refresh complete");
    }
};
    
    const renderTemplateManagement = () => {
        if (!aiAnalysis || !flowPrompts) {
            return (
                <div className="no-analysis">
                    <p>Run AI analysis first to see template recommendations.</p>
                    <button onClick={() => handleAutoAnalysis(false)}>Run Analysis</button>
                </div>
            );
        }

        const allTemplates = [];
        
        aiAnalysis.segments?.forEach(segment => {
            flowPrompts.flow_prompts?.forEach(prompt => {
                if (prompt.segment_targeted === segment.segment_name) {
                    allTemplates.push({
                        ...prompt,
                        segment_id: segment.segment_id,
                        segment_name: segment.segment_name,
                        farmer_count: segment.farmer_count,
                        priority: prompt.priority
                    });
                }
            });
        });

        const handleTemplateClick = async (template) => {
            setSelectedTemplate(template);
            setIsLoading(true);
            try {
                const response = await axios.post(`${API_URL}/segment-farmers/`, {
                    segment_id: template.segment_id
                });
                setTemplateFarmers(response.data);
            } catch (err) {
                setError("Could not load farmers: " + (err.response?.data?.message || err.message));
            } finally {
                setIsLoading(false);
            }
        };

        return (
            <div className="template-management-section">
                <div className="template-header">
                    <h2>📱 WhatsApp Templates & Flow Management</h2>
                    <p>All recommended templates with target farmers and ready-to-use prompts</p>
                </div>

                <div className="template-stats">
                    <div className="stat-box">
                        <h3>{allTemplates.length}</h3>
                        <p>Total Templates</p>
                    </div>
                    <div className="stat-box">
                        <h3>{allTemplates.filter(t => t.priority === 'HIGH').length}</h3>
                        <p>High Priority</p>
                    </div>
                    <div className="stat-box">
                        <h3>{allTemplates.reduce((sum, t) => sum + t.farmer_count, 0)}</h3>
                        <p>Total Reach</p>
                    </div>
                </div>

                <div className="templates-grid">
                    {allTemplates.map((template, idx) => (
                        <div 
                            key={idx} 
                            className={`template-management-card priority-${template.priority.toLowerCase()}`}
                            onClick={() => handleTemplateClick(template)}
                        >
                            <div className="template-card-header">
                                <div>
                                    <h3>{template.prompt_title}</h3>
                                    <span className="segment-tag">{template.segment_name}</span>
                                </div>
                                <span className={`priority-badge ${template.priority.toLowerCase()}`}>
                                    {template.priority}
                                </span>
                            </div>

                            <div className="template-card-stats">
                                <div className="stat-item">
                                    <Users size={16} />
                                    <span>{template.farmer_count} farmers</span>
                                </div>
                                <div className="stat-item">
                                    <TrendingUp size={16} />
                                    <span>{template.estimated_conversion_rate} conversion</span>
                                </div>
                                <div className="stat-item">
                                    <Phone size={16} />
                                    <span>{template.expected_templates} templates</span>
                                </div>
                            </div>

                            <div className="template-language">
                                <strong>Language:</strong> {template.language.toUpperCase()}
                            </div>

                            <div className="template-actions-preview">
                                <button className="view-farmers-btn" onClick={(e) => {
                                    e.stopPropagation();
                                    handleTemplateClick(template);
                                }}>
                                    View Target Farmers →
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {selectedTemplate && renderTemplateDetailModal()}
            </div>
        );
    };
const renderTemplateDetailModal = () => {
    if (!selectedTemplate) return null;

    return (
        <div className="template-detail-modal" onClick={() => setSelectedTemplate(null)}>
            <div className="modal-content extra-large" onClick={e => e.stopPropagation()}>
                <div className="modal-scroll-wrapper">
                    <button className="close-modal" onClick={() => setSelectedTemplate(null)}>✕</button>
                    
                    <div className="template-detail-header">
                        <h2>{selectedTemplate.prompt_title}</h2>
                        <span className={`priority-badge large ${selectedTemplate.priority.toLowerCase()}`}>
                            {selectedTemplate.priority}
                        </span>
                    </div>

                    {/* NEW: Template Bodies Section */}
                    {selectedTemplate.templates && selectedTemplate.templates.length > 0 && (
                        <div className="template-section">
                            <h3>📱 WhatsApp Templates ({selectedTemplate.templates.length})</h3>
                            <p className="section-hint">Complete template specifications ready to submit to Meta</p>
                            
                            {selectedTemplate.templates.map((template, idx) => (
                                <div key={idx} className="single-template-card">
                                    <div className="template-card-header">
                                        <h4>{template.template_name}</h4>
                                        <div className="template-meta">
                                            <span className="badge">{template.template_category}</span>
                                            <span className="badge">{template.template_language.toUpperCase()}</span>
                                        </div>
                                    </div>

                                    <div className="template-body-preview">
                                        <h5>📝 Template Body:</h5>
                                        <div className="body-text">
                                            <pre>{template.template_body}</pre>
                                        </div>
                                    </div>

                                    <div className="template-variables">
                                        <h5>🔧 Variables ({template.variables.length}):</h5>
                                        <div className="variables-grid">
                                            {template.variables.map((v, vidx) => (
                                                <div key={vidx} className="variable-item">
                                                    <strong>{`{{${v.position}}}`}</strong>
                                                    <span className="var-name">{v.variable_name}</span>
                                                    <span className="var-example">Example: {v.example}</span>
                                                    <span className="var-field">From: {v.data_field}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {template.buttons && template.buttons.length > 0 && (
                                        <div className="template-buttons">
                                            <h5>🔘 Buttons:</h5>
                                            {template.buttons.map((btn, bidx) => (
                                                <div key={bidx} className="button-preview">
                                                    <span className="btn-type">{btn.type}</span>
                                                    <span className="btn-text">{btn.text}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className="meta-creation-prompt">
                                        <h5>📋 Meta Template Creation Prompt:</h5>
                                        <button 
                                            className="copy-prompt-btn"
                                            onClick={() => {
                                                navigator.clipboard.writeText(template.meta_template_creation_prompt);
                                                alert('Template creation prompt copied!');
                                            }}
                                        >
                                            📋 Copy Meta Submission Prompt
                                        </button>
                                        <pre>{template.meta_template_creation_prompt}</pre>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Complete Flow Prompt */}
                    <div className="template-section">
                        <h3>🤖 Complete Flow Implementation Prompt</h3>
                        <button 
                            className="copy-prompt-btn"
                            onClick={() => {
                                navigator.clipboard.writeText(selectedTemplate.full_flow_prompt || selectedTemplate.full_prompt);
                                alert('Flow prompt copied!');
                            }}
                        >
                            📋 Copy Complete Flow Prompt
                        </button>
                        <div className="prompt-box-large">
                            <pre>{selectedTemplate.full_flow_prompt || selectedTemplate.full_prompt}</pre>
                        </div>
                    </div>

                        <div className="template-section">
                            <h3><Users size={20} /> Target Farmers ({templateFarmers?.total_farmers || selectedTemplate.farmer_count})</h3>
                            
                            {isLoading ? (
                                <div className="loading-farmers">
                                    <div className="spinner"></div>
                                    <p>Loading farmer details...</p>
                                </div>
                            ) : templateFarmers ? (
                                <>
                                    <div className="farmers-actions">
                                        <button 
                                            className="export-btn"
                                            onClick={() => exportFarmersToCSV(templateFarmers.farmers)}
                                        >
                                            📥 Export All ({templateFarmers.total_farmers})
                                        </button>
                                        <button 
                                            className="copy-numbers-btn"
                                            onClick={() => {
                                                const numbers = templateFarmers.farmers.map(f => f.phone_number).join(', ');
                                                navigator.clipboard.writeText(numbers);
                                                alert(`Copied ${templateFarmers.total_farmers} phone numbers!`);
                                            }}
                                        >
                                            📋 Copy All Numbers
                                        </button>
                                        <button 
                                            className="whatsapp-bulk-btn"
                                            onClick={() => {
                                                const numbers = templateFarmers.farmers.map(f => f.phone_number).join('\n');
                                                const blob = new Blob([numbers], { type: 'text/plain' });
                                                const url = window.URL.createObjectURL(blob);
                                                const a = document.createElement('a');
                                                a.href = url;
                                                a.download = 'whatsapp_numbers.txt';
                                                a.click();
                                            }}
                                        >
                                            💬 Download for Bulk WhatsApp
                                        </button>
                                    </div>

                                    <div className="farmers-table-container">
                                        <table className="farmers-table">
                                            <thead>
                                                <tr>
                                                    <th>#</th>
                                                    <th>Farmer Name</th>
                                                    <th>Phone Number</th>
                                                    <th>Farm Size</th>
                                                    <th>Crop</th>
                                                    <th>Match Reason</th>
                                                    <th>Action</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {templateFarmers.farmers.map((farmer, idx) => (
                                                    <tr key={idx}>
                                                        <td>{idx + 1}</td>
                                                        <td><strong>{farmer.farmer_name}</strong></td>
                                                        <td>
                                                            <a href={`tel:${farmer.phone_number}`}>
                                                                {farmer.phone_number}
                                                            </a>
                                                        </td>
                                                        <td>{farmer.farm_size} acres</td>
                                                        <td>{farmer.crop_name || 'N/A'}</td>
                                                        <td className="match-reason-cell">{farmer.match_reason}</td>
                                                        <td>
                                                            <button 
                                                                className="whatsapp-btn-table"
                                                                onClick={() => window.open(`https://wa.me/${farmer.phone_number}`, '_blank')}
                                                            >
                                                                WhatsApp
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </>
                            ) : (
                                <p>Click to load farmer details</p>
                            )}
                        </div>

                        <div className="template-section">
                            <h3>📋 Implementation Notes</h3>
                            <ul className="implementation-list">
                                {selectedTemplate.implementation_notes?.map((note, i) => (
                                    <li key={i}>{note}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const loadCalendarEvents = async () => {
        try {
            const response = await axios.get(`${API_URL}/calendar/`);
            setCalendarEvents(response.data);
        } catch (err) {
            console.error("Calendar load error:", err);
        }
    };

    const handleSegmentClick = async (segment) => {
        setSelectedSegment(segment);
        setIsLoading(true);
        setSegmentFarmers(null);
        try {
            const [detailsResponse, farmersResponse] = await Promise.all([
                axios.post(`${API_URL}/segment-details/`, { segment_id: segment.segment_id }),
                axios.post(`${API_URL}/segment-farmers/`, { segment_id: segment.segment_id })
            ]);
            setSegmentDetails(detailsResponse.data);
            setSegmentFarmers(farmersResponse.data);
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

    const exportFarmersToCSV = (farmers) => {
        const headers = Object.keys(farmers[0]).join(',');
        const rows = farmers.map(f => Object.values(f).map(v => `"${v}"`).join(','));
        const csv = [headers, ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'farmers_export.csv';
        a.click();
    };

    const renderCalendarView = () => {
        if (!calendarEvents) {
            return <div className="loading-calendar">Loading calendar...</div>;
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        
        const eventsByDate = calendarEvents.events_by_date || {};
        
        let filteredDates = Object.keys(eventsByDate).filter(dateStr => {
            const eventDate = new Date(dateStr);
            eventDate.setHours(0, 0, 0, 0);
            
            if (calendarView === 'upcoming') {
                return eventDate >= sevenDaysAgo;
            } else if (calendarView === 'history') {
                return eventDate < today;
            }
            return true;
        });

        if (calendarFilter !== 'all') {
            filteredDates = filteredDates.filter(dateStr => {
                const events = eventsByDate[dateStr];
                return events.some(e => e.event_type === calendarFilter);
            });
        }

        filteredDates.sort();

        if (calendarView === 'full') {
            return renderFullCalendar(eventsByDate, filteredDates);
        }

        return (
            <div className="calendar-section">
                <div className="calendar-header">
                    <h2><Calendar size={24} /> Important Dates Calendar</h2>
                    <p>{calendarEvents.total_events} total events</p>
                </div>

                <div className="calendar-controls">
                    <div className="view-switcher">
                        <button 
                            className={calendarView === 'upcoming' ? 'active' : ''}
                            onClick={() => setCalendarView('upcoming')}
                        >
                            📅 Upcoming & Last 7 Days
                        </button>
                        <button 
                            className={calendarView === 'history' ? 'active' : ''}
                            onClick={() => setCalendarView('history')}
                        >
                            📜 Full History
                        </button>
                        <button 
                            className={calendarView === 'full' ? 'active' : ''}
                            onClick={() => setCalendarView('full')}
                        >
                            📆 Month View
                        </button>
                    </div>

                    <div className="event-filter">
                        <select value={calendarFilter} onChange={(e) => setCalendarFilter(e.target.value)}>
                            <option value="all">All Events</option>
                            <option value="harvest">🌾 Harvest Only</option>
                            <option value="growth_stage">🌱 Growth Stages</option>
                            <option value="intervention">💊 Interventions</option>
                        </select>
                    </div>
                </div>

                <div className="calendar-grid">
                    {filteredDates.map(dateStr => {
                        const events = eventsByDate[dateStr];
                        const eventDate = new Date(dateStr);
                        const daysUntil = Math.ceil((eventDate - today) / (1000 * 60 * 60 * 24));
                        const isUrgent = daysUntil >= -7 && daysUntil <= 7;
                        const isPast = daysUntil < 0;
                        
                        const groupedEvents = events.reduce((acc, event) => {
                            const key = `${event.event_type}_${event.title}`;
                            if (!acc[key]) {
                                acc[key] = {
                                    ...event,
                                    farmers: []
                                };
                            }
                            acc[key].farmers.push({
                                name: event.farmer_name,
                                phone: event.farmer_phone,
                                id: event.farmer_id,
                                details: event.details
                            });
                            return acc;
                        }, {});

                        const consolidatedEvents = Object.values(groupedEvents);
                        
                        return (
                            <div 
                                key={dateStr} 
                                className={`calendar-date-card ${isUrgent ? 'urgent' : ''} ${isPast ? 'past' : ''}`}
                                onClick={() => setSelectedDate(dateStr)}
                            >
                                <div className="date-header">
                                    <div className="date-info">
                                        <span className="date-day">{eventDate.toLocaleDateString('en-US', { weekday: 'short' })}</span>
                                        <span className="date-number">{eventDate.getDate()}</span>
                                        <span className="date-month">{eventDate.toLocaleDateString('en-US', { month: 'short' })}</span>
                                    </div>
                                    {isUrgent && !isPast && <span className="urgent-badge">URGENT</span>}
                                    {isPast ? (
                                        <span className="past-badge">{Math.abs(daysUntil)} days ago</span>
                                    ) : (
                                        <span className="days-until">{daysUntil} days</span>
                                    )}
                                </div>

                                <div className="events-list">
                                    {consolidatedEvents.slice(0, 2).map((event, idx) => (
                                        <div key={idx} className={`event-item event-${event.event_type}`}>
                                            <div className="event-title">{event.title}</div>
                                            <div className="event-farmers">
                                                <Users size={14} /> {event.farmers.length} farmer{event.farmers.length > 1 ? 's' : ''}
                                            </div>
                                            <div className="event-reason">{event.action_needed}</div>
                                        </div>
                                    ))}
                                    {consolidatedEvents.length > 2 && (
                                        <div className="more-events">+{consolidatedEvents.length - 2} more</div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {filteredDates.length === 0 && (
                    <div className="no-events">
                        <p>No events found for the selected filters.</p>
                    </div>
                )}

                {selectedDate && renderDateDetailsModal(eventsByDate[selectedDate], selectedDate)}
            </div>
        );
    };

    const renderFullCalendar = (eventsByDate, filteredDates) => {
        const monthsData = {};
        
        filteredDates.forEach(dateStr => {
            const date = new Date(dateStr);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            
            if (!monthsData[monthKey]) {
                monthsData[monthKey] = {
                    year: date.getFullYear(),
                    month: date.getMonth(),
                    dates: []
                };
            }
            
            monthsData[monthKey].dates.push({
                dateStr,
                date: date.getDate(),
                events: eventsByDate[dateStr]
            });
        });

        const sortedMonths = Object.keys(monthsData).sort();

        return (
            <div className="calendar-section">
                <div className="calendar-header">
                    <h2><Calendar size={24} /> Month View Calendar</h2>
                </div>

                <div className="calendar-controls">
                    <div className="event-filter">
                        <select value={calendarFilter} onChange={(e) => setCalendarFilter(e.target.value)}>
                            <option value="all">All Events</option>
                            <option value="harvest">🌾 Harvest Only</option>
                            <option value="growth_stage">🌱 Growth Stages</option>
                            <option value="intervention">💊 Interventions</option>
                        </select>
                    </div>
                    <button onClick={() => setCalendarView('upcoming')} className="back-btn">
                        ← Back to List View
                    </button>
                </div>

                <div className="month-calendar-container">
                    {sortedMonths.map(monthKey => {
                        const monthData = monthsData[monthKey];
                        const monthName = new Date(monthData.year, monthData.month).toLocaleDateString('en-US', { 
                            month: 'long', 
                            year: 'numeric' 
                        });

                        const firstDay = new Date(monthData.year, monthData.month, 1);
                        const lastDay = new Date(monthData.year, monthData.month + 1, 0);
                        const startingDayOfWeek = firstDay.getDay();
                        const totalDays = lastDay.getDate();

                        const calendarGrid = [];
                        
                        for (let i = 0; i < startingDayOfWeek; i++) {
                            calendarGrid.push(<div key={`empty-${i}`} className="calendar-day empty"></div>);
                        }

                        for (let day = 1; day <= totalDays; day++) {
                            const dateStr = `${monthData.year}-${String(monthData.month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                            const dayData = monthData.dates.find(d => d.dateStr === dateStr);
                            const hasEvents = dayData && dayData.events.length > 0;
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);
                            const isToday = dateStr === today.toISOString().split('T')[0];

                            calendarGrid.push(
                                <div 
                                    key={day} 
                                    className={`calendar-day ${hasEvents ? 'has-events' : ''} ${isToday ? 'today' : ''}`}
                                    onClick={() => hasEvents && setSelectedDate(dateStr)}
                                >
                                    <div className="day-number">{day}</div>
                                    {hasEvents && (
                                        <div className="event-dots">
                                            {dayData.events.slice(0, 3).map((e, i) => (
                                                <span key={i} className={`dot dot-${e.event_type}`}></span>
                                            ))}
                                            {dayData.events.length > 3 && <span className="more">+{dayData.events.length - 3}</span>}
                                        </div>
                                    )}
                                </div>
                            );
                        }

                        return (
                            <div key={monthKey} className="month-calendar">
                                <h3>{monthName}</h3>
                                <div className="calendar-weekdays">
                                    <div>Sun</div>
                                    <div>Mon</div>
                                    <div>Tue</div>
                                    <div>Wed</div>
                                    <div>Thu</div>
                                    <div>Fri</div>
                                    <div>Sat</div>
                                </div>
                                <div className="calendar-days-grid">
                                    {calendarGrid}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {selectedDate && renderDateDetailsModal(eventsByDate[selectedDate], selectedDate)}
            </div>
        );
    };
const renderDateDetailsModal = (events, dateStr) => {
    if (!events) return null;

    const eventDate = new Date(dateStr);
    
    const groupedEvents = events.reduce((acc, event) => {
        const key = `${event.event_type}_${event.title}`;
        if (!acc[key]) {
            acc[key] = {
                ...event,
                farmers: []
            };
        }
        acc[key].farmers.push({
            name: event.farmer_name,
            phone: event.farmer_phone,
            id: event.farmer_id,
            details: event.details,
            recommended_template: event.recommended_template,
            recommended_flow: event.recommended_flow,
            needs_template_creation: event.needs_template_creation,
            create_template_prompt: event.create_template_prompt,
            farmer_details: event.farmer_details
        });
        return acc;
    }, {});

    const consolidatedEvents = Object.values(groupedEvents);

    return (
        <div className="date-details-modal" onClick={() => setSelectedDate(null)}>
            <div className="modal-content large" onClick={e => e.stopPropagation()}>
                <button className="close-modal" onClick={() => setSelectedDate(null)}>✕</button>
                <h2>Events on {eventDate.toLocaleDateString('en-US', { dateStyle: 'full' })}</h2>
                
                <div className="events-detailed">
                    {consolidatedEvents.map((event, idx) => (
                        <div key={idx} className={`event-detail-card priority-${event.priority.toLowerCase()}`}>
                            <div className="event-header">
                                <h3>{event.title}</h3>
                                <span className={`priority-badge ${event.priority.toLowerCase()}`}>{event.priority}</span>
                            </div>
                            
                            <div className="event-importance">
                                <strong>Why Important:</strong>
                                <p>{event.action_needed}</p>
                            </div>

                            {/* NEW: Template & Flow Recommendations */}
                            <div className="template-flow-recommendations">
                                <h4>📱 WhatsApp Communication Plan</h4>
                                
                                {/* Show matched template */}
                                {event.recommended_template ? (
                                    <div className="recommendation-box template-box">
                                        <div className="recommendation-header">
                                            <span className="recommendation-icon">✅</span>
                                            <strong>Recommended Template</strong>
                                            <span className={`confidence-badge ${event.recommended_template.confidence.toLowerCase()}`}>
                                                {event.recommended_template.confidence} Match
                                            </span>
                                        </div>
                                        <div className="recommendation-details">
                                            <p><strong>Name:</strong> {event.recommended_template.template_name}</p>
                                            <p><strong>Language:</strong> {event.recommended_template.template_language.toUpperCase()}</p>
                                            <p><strong>Category:</strong> {event.recommended_template.template_category}</p>
                                            <p className="match-reason">
                                                <strong>Why:</strong> {event.recommended_template.match_reason}
                                            </p>
                                        </div>
                                        <button 
                                            className="use-template-btn"
                                            onClick={() => {
                                                const farmerNumbers = event.farmers.map(f => f.phone).join(', ');
                                                alert(`✅ Use template: "${event.recommended_template.template_name}"\n\nFor farmers:\n${farmerNumbers}\n\nCopy numbers and send via WhatsApp Business API`);
                                            }}
                                        >
                                            📤 Use This Template
                                        </button>
                                    </div>
                                ) : event.needs_template_creation ? (
                                    <div className="recommendation-box needs-creation-box">
                                        <div className="recommendation-header">
                                            <span className="recommendation-icon">⚠️</span>
                                            <strong>No Suitable Template Found</strong>
                                            <span className="needs-creation-badge">Create New</span>
                                        </div>
                                        
                                        {event.create_template_prompt && !event.create_template_prompt.error ? (
                                            <>
                                                <div className="recommendation-details">
                                                    <p className="suggestion-text">
                                                        We've generated a custom template for this event type. 
                                                        Copy the prompt below and create it in Meta Business Manager.
                                                    </p>
                                                    
                                                    <div className="template-preview">
                                                        <h5>📝 Suggested Template:</h5>
                                                        <p><strong>Name:</strong> {event.create_template_prompt.template_name}</p>
                                                        <p><strong>Category:</strong> {event.create_template_prompt.template_category}</p>
                                                        <div className="body-preview">
                                                            <strong>Body:</strong>
                                                            <pre>{event.create_template_prompt.template_body}</pre>
                                                        </div>
                                                    </div>
                                                </div>
                                                
                                                <button 
                                                    className="copy-prompt-btn"
                                                    onClick={() => {
                                                        const promptText = event.create_template_prompt.meta_template_creation_prompt;
                                                        navigator.clipboard.writeText(promptText);
                                                        alert('✅ Template creation prompt copied!\n\nPaste this in Meta Business Manager to create the template.');
                                                    }}
                                                >
                                                    📋 Copy Template Creation Prompt
                                                </button>
                                                
                                                <details className="full-prompt-details" style={{marginTop: '12px'}}>
                                                    <summary>👁️ View Complete Prompt</summary>
                                                    <pre className="full-prompt-text">
                                                        {event.create_template_prompt.meta_template_creation_prompt}
                                                    </pre>
                                                </details>
                                            </>
                                        ) : (
                                            <p className="error-text">Could not generate template prompt. Please create manually.</p>
                                        )}
                                    </div>
                                ) : (
                                    <div className="recommendation-box no-match-box">
                                        <p>No template recommendation available</p>
                                    </div>
                                )}

                                {/* Show matched flow */}
                                {event.recommended_flow && (
                                    <div className="recommendation-box flow-box">
                                        <div className="recommendation-header">
                                            <span className="recommendation-icon">🔄</span>
                                            <strong>Recommended Flow</strong>
                                            <span className={`confidence-badge ${event.recommended_flow.confidence.toLowerCase()}`}>
                                                {event.recommended_flow.confidence} Match
                                            </span>
                                        </div>
                                        <div className="recommendation-details">
                                            <p><strong>Flow Name:</strong> {event.recommended_flow.flow_name}</p>
                                            <p><strong>Flow ID:</strong> {event.recommended_flow.flow_id}</p>
                                            <p className="match-reason">
                                                <strong>Why:</strong> {event.recommended_flow.match_reason}
                                            </p>
                                        </div>
                                        <button 
                                            className="use-flow-btn"
                                            onClick={() => {
                                                alert(`✅ Use flow: "${event.recommended_flow.flow_name}"\n\nFlow ID: ${event.recommended_flow.flow_id}\n\nTrigger this flow for the affected farmers.`);
                                            }}
                                        >
                                            🔄 Use This Flow
                                        </button>
                                    </div>
                                )}
                            </div>

                            <div className="farmers-list-compact">
                                <h4><Users size={16} /> {event.farmers.length} Farmer{event.farmers.length > 1 ? 's' : ''} Affected</h4>
                                
                                {event.farmers.map((farmer, fIdx) => (
                                    <div key={fIdx} className="farmer-row">
                                        <div className="farmer-info">
                                            <span className="farmer-name">{farmer.name}</span>
                                            <a href={`tel:${farmer.phone}`} className="farmer-phone">
                                                <Phone size={14} /> {farmer.phone}
                                            </a>
                                            {farmer.farmer_details && (
                                                <div className="farmer-context">
                                                    <span className="context-item">
                                                        🌾 {farmer.farmer_details.crop || 'N/A'}
                                                    </span>
                                                    <span className="context-item">
                                                        📏 {farmer.farmer_details.farm_size || 'N/A'} acres
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                        <button 
                                            className="whatsapp-btn-small"
                                            onClick={() => window.open(`https://wa.me/${farmer.phone}`, '_blank')}
                                        >
                                            WhatsApp
                                        </button>
                                    </div>
                                ))}
                            </div>

                            <div className="bulk-actions">
                                <button 
                                    className="export-farmers-btn"
                                    onClick={() => exportFarmersToCSV(event.farmers.map(f => ({
                                        farmer_name: f.name,
                                        phone_number: f.phone,
                                        event_type: event.event_type,
                                        action_needed: event.action_needed,
                                        recommended_template: event.recommended_template?.template_name || 'None',
                                        recommended_flow: event.recommended_flow?.flow_name || 'None'
                                    })))}
                                >
                                    📥 Export All Numbers
                                </button>
                                <button 
                                    className="copy-numbers-btn"
                                    onClick={() => {
                                        const numbers = event.farmers.map(f => f.phone).join(', ');
                                        navigator.clipboard.writeText(numbers);
                                        alert('All phone numbers copied!');
                                    }}
                                >
                                    📋 Copy All Numbers
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
    const renderSegmentFarmers = () => {
        if (!segmentFarmers) return null;

        return (
            <div className="segment-farmers-section">
                <div className="farmers-header">
                    <h3>
                        <Users size={20} /> 
                        Farmers in this Segment ({segmentFarmers.total_farmers})
                    </h3>
                    <button 
                        className="export-btn"
                        onClick={() => exportFarmersToCSV(segmentFarmers.farmers)}
                    >
                        Export to CSV
                    </button>
                </div>

                <div className="farmers-grid">
                    {segmentFarmers.farmers.map((farmer, idx) => (
                        <div key={idx} className="farmer-card">
                            <div className="farmer-header">
                                <h4>{farmer.farmer_name}</h4>
                                <span className="farmer-id">#{farmer.farmer_id}</span>
                            </div>

                            <div className="farmer-contact">
                                <div className="contact-row">
                                    <Phone size={16} />
                                    <a href={`tel:${farmer.phone_number}`}>{farmer.phone_number}</a>
                                    <button 
                                        className="whatsapp-btn"
                                        onClick={() => window.open(`https://wa.me/${farmer.phone_number}`, '_blank')}
                                        title="Contact on WhatsApp"
                                    >
                                        WhatsApp
                                    </button>
                                </div>
                                {farmer.farm_size && (
                                    <div className="contact-row">
                                        <MapPin size={16} />
                                        <span>{farmer.farm_size} acres</span>
                                    </div>
                                )}
                            </div>

                            {farmer.crop_name && (
                                <div className="farmer-crop">
                                    <strong>Crop:</strong> {farmer.crop_name}
                                    {farmer.current_stage && <span className="stage-badge">{farmer.current_stage}</span>}
                                </div>
                            )}

                            {farmer.last_intervention && (
                                <div className="intervention-info">
                                    <strong>Last Activity:</strong> {farmer.last_intervention}
                                    {farmer.last_intervention_date && (
                                        <span className="intervention-date"> ({new Date(farmer.last_intervention_date).toLocaleDateString()})</span>
                                    )}
                                </div>
                            )}

                            {farmer.avg_intervention_cost && (
                                <div className="value-info">
                                    💰 <strong>Avg Spend:</strong> ₹{farmer.avg_intervention_cost}
                                    {farmer.total_spend && <span> | Total: ₹{farmer.total_spend}</span>}
                                </div>
                            )}

                            {farmer.last_fertilizer_used && farmer.last_fertilizer_used !== 'None' && (
                                <div className="product-info">
                                    🌱 <strong>Last Fertilizer:</strong> {farmer.last_fertilizer_used}
                                </div>
                            )}

                            {farmer.days_inactive && farmer.days_inactive > 30 && (
                                <div className="inactive-warning">
                                    ⚠️ <strong>Inactive:</strong> {farmer.days_inactive} days
                                </div>
                            )}

                            {farmer.days_until_harvest !== undefined && (
                                <div className="harvest-info">
                                    <AlertCircle size={16} />
                                    <span>Harvesting in {farmer.days_until_harvest} days</span>
                                </div>
                            )}

                            <div className="match-reason">
                                <TrendingUp size={14} />
                                <span>{farmer.match_reason}</span>
                            </div>

                            {farmer.next_crop_recommendation && (
                                <div className="next-crop">
                                    <strong>Next Crop:</strong> {farmer.next_crop_recommendation}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        );
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
                    {cacheStatus?.has_cache && (
                        <p style={{fontSize: '0.875rem', color: '#666'}}>
                            Loading cached data from: {new Date(cacheStatus.cached_at).toLocaleString()}
                        </p>
                    )}
                </div>
            );
        }

        if (!aiAnalysis) {
            return (
                <div className="no-analysis">
                    <p>No analysis available.</p>
                    <button onClick={() => handleAutoAnalysis(false)}>Run Analysis</button>
                </div>
            );
        }

        return (
            <div className="ai-analysis-container">
                {cacheStatus?.has_cache && (
                    <div className="cache-status-banner">
                        <div className="cache-info">
                            {cacheStatus.from_cache ? (
                                <>
                                    <span className="cache-icon">📦</span>
                                    <span>Showing cached analysis from: <strong>{new Date(cacheStatus.cached_at).toLocaleString()}</strong></span>
                                    {cacheStatus.expires_in_hours !== undefined && (
                                        <span className="cache-expiry"> (Expires in {Math.round(cacheStatus.expires_in_hours)}h)</span>
                                    )}
                                </>
                            ) : (
                                <>
                                    <span className="cache-icon">✅</span>
                                    <span>Fresh analysis from: <strong>{new Date(cacheStatus.cached_at).toLocaleString()}</strong></span>
                                </>
                            )}
                        </div>
                        <button 
                            className="refresh-cache-btn"
                            onClick={handleRefreshCache}
                            disabled={autoAnalyzing}
                        >
                            🔄 Refresh Analysis
                        </button>
                    </div>
                )}

                {showQuotaWarning && (
                    <div className="quota-warning-banner">
                        <div className="warning-content">
                            <span className="warning-icon">⚠️</span>
                            <div>
                                <strong>API Quota Limit Reached</strong>
                                <p>Gemini API free tier: 50 requests/day. Showing cached data. Fresh analysis available tomorrow.</p>
                            </div>
                        </div>
                        <button onClick={() => setShowQuotaWarning(false)} className="close-warning">✕</button>
                    </div>
                )}

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
                                    {segment.intervention_insights?.avg_intervention_cost && (
                                        <p className="avg-spend">Avg Spend: <strong>₹{segment.intervention_insights.avg_intervention_cost}</strong></p>
                                    )}
                                </div>
                                <div className="segment-characteristics">
                                    {segment.characteristics?.slice(0, 3).map((char, i) => (
                                        <span key={i} className="characteristic-tag">{char}</span>
                                    ))}
                                </div>
                                {segment.intervention_insights?.upsell_products && segment.intervention_insights.upsell_products.length > 0 && (
                                    <div className="upsell-products">
                                        <strong>💡 Upsell:</strong>
                                        {segment.intervention_insights.upsell_products.slice(0, 2).map((product, i) => (
                                            <span key={i} className="product-tag">{product}</span>
                                        ))}
                                    </div>
                                )}
                                <button className="view-details-btn">View Details →</button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* <div className="flow-prompts-section">
                    <h2>🚀 Ready-to-Use Flow Prompts</h2>
                    <p className="section-description">
                        Copy these prompts and use them to create WhatsApp flows. Click on segments above to see which farmers to send to.
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
                </div> */}
               <div className="flow-prompts-section">
    <h2>🚀 Ready-to-Use Prompts</h2>
    <p className="section-description">
        Complete prompts for creating templates and flows. Copy and use directly.
    </p>
    
    {segmentPackages?.segment_packages?.map((pkg, idx) => (
        <div key={idx} className={`prompt-card priority-${pkg.priority.toLowerCase()}`}>
            <div className="prompt-header">
                <h3>
                    {pkg.segment_name}
                    <span className={`badge priority-${pkg.priority.toLowerCase()}`}>
                        {pkg.priority}
                    </span>
                </h3>
                <p className="prompt-meta">
                    Farmers: <strong>{pkg.farmer_count}</strong> | 
                    Language: <strong>{pkg.language.toUpperCase()}</strong> | 
                    Conversion: <strong>{pkg.estimated_conversion_rate}</strong>
                </p>
            </div>
            
            {/* STEP 1: Template Creation */}
            {pkg.step_1_templates && pkg.step_1_templates.length > 0 && (
                <div className="template-creation-section">
                    <h4>📱 Step 1: Create Templates ({pkg.step_1_templates.length})</h4>
                    <p className="step-description">Create these templates first before building the flow</p>
                    
                    {pkg.step_1_templates.map((template, tidx) => (
                        <div key={tidx} className="template-prompt-box">
                            <div className="template-prompt-header">
                                <strong>{template.template_name}</strong>
                                <div className="template-badges">
                                    <span className="badge">{template.template_category}</span>
                                    <span className="badge">{template.template_language.toUpperCase()}</span>
                                </div>
                            </div>
                            
                            {/* Template Body Preview */}
                            <div className="template-body-preview">
                                <h5>📝 Template Text:</h5>
                                <pre className="template-text-preview">{template.template_body}</pre>
                            </div>
                            
                            {/* Variables */}
                            <div className="template-variables-compact">
                                <h5>🔧 Variables ({template.variables.length}):</h5>
                                <div className="variables-grid-compact">
                                    {template.variables.map((v, vidx) => (
                                        <div key={vidx} className="variable-chip">
                                            <strong>{`{{${v.position}}}`}</strong> = {v.variable_name}
                                            <span className="variable-example">"{v.example}"</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            
                            {/* Buttons */}
                            {template.buttons && template.buttons.length > 0 && (
                                <div className="template-buttons-preview">
                                    <h5>🔘 Buttons:</h5>
                                    <div className="buttons-row">
                                        {template.buttons.map((btn, bidx) => (
                                            <span key={bidx} className="button-chip">{btn.text}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            
                            {/* Copy Button */}
                            <button 
                                className="copy-template-prompt-btn"
                                onClick={() => {
                                    copyPromptToClipboard(template.meta_template_creation_prompt);
                                    alert('Template prompt copied! Paste in Meta Business Manager.');
                                }}
                            >
                                📋 Copy Complete Template Creation Prompt
                            </button>
                            
                            {/* Expandable Full Prompt */}
                            <details className="full-prompt-details">
                                <summary>👁️ View Full Template Prompt</summary>
                                <pre className="full-prompt-text">{template.meta_template_creation_prompt}</pre>
                            </details>
                        </div>
                    ))}
                </div>
            )}
            
            {/* STEP 2: Flow Creation */}
            <div className="flow-prompt-section">
                <h4>🔄 Step 2: Create Flow (After Templates Approved)</h4>
                <p className="step-description">Use this prompt after all {pkg.step_1_templates?.length || 0} template(s) are approved by Meta</p>
                
                <div className="prompt-content">
                    <div className="prompt-text">
                        <pre>{pkg.step_2_flow_prompt}</pre>
                        <button 
                            className="copy-btn"
                            onClick={() => {
                                copyPromptToClipboard(pkg.step_2_flow_prompt);
                                alert('Flow prompt copied! Use in AI Flow Maker.');
                            }}
                        >
                            📋 Copy Flow Creation Prompt
                        </button>
                    </div>
                </div>
            </div>
            
            {/* Implementation Details */}
            <div className="prompt-details">
                <div className="stats-row">
                    <div className="stat-item">
                        <strong>Templates Needed:</strong> {pkg.step_1_templates?.length || 0}
                    </div>
                    <div className="stat-item">
                        <strong>Target Farmers:</strong> {pkg.farmer_count}
                    </div>
                    <div className="stat-item">
                        <strong>Expected Conversion:</strong> {pkg.estimated_conversion_rate}
                    </div>
                </div>
                
                <div className="implementation-steps">
                    <h4>📋 Implementation Checklist:</h4>
                    <ol>
                        <li>
                            <strong>Create Templates ({pkg.step_1_templates?.length || 0}):</strong>
                            <ul>
                                {pkg.step_1_templates?.map((t, i) => (
                                    <li key={i}>Copy prompt for "{t.template_name}" and submit to Meta</li>
                                ))}
                            </ul>
                        </li>
                        <li><strong>Wait for Approval:</strong> Usually 15 minutes - 2 hours</li>
                        <li><strong>Create Flow:</strong> Copy Step 2 prompt above and create flow</li>
                        <li><strong>Test:</strong> Send to 5-10 farmers to verify</li>
                        <li><strong>Deploy:</strong> Roll out to all {pkg.farmer_count} farmers</li>
                    </ol>
                </div>
                
                {pkg.implementation_notes && pkg.implementation_notes.length > 0 && (
                    <div className="additional-notes">
                        <h5>💡 Additional Notes:</h5>
                        <ul>
                            {pkg.implementation_notes.map((note, i) => (
                                <li key={i}>{note}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    ))}
    
    {(!segmentPackages || !segmentPackages.segment_packages || segmentPackages.segment_packages.length === 0) && (
        <div className="no-prompts">
            <p>No prompts available. Run analysis first.</p>
        </div>
    )}
</div>

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
                    <button className="close-modal" onClick={() => {
                        setSegmentDetails(null);
                        setSegmentFarmers(null);
                    }}>✕</button>
                    
                    <h2>{segmentDetails.segment.segment_name}</h2>
                    <p className="segment-description">{segmentDetails.segment.farmer_count} farmers | {segmentDetails.segment.conversion_potential} conversion potential</p>
                    
                    {renderSegmentFarmers()}
                    
                    {detailed && (
                        <div className="segment-full-info">
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
                            </div>

                            <div className="info-section">
                                <h3>📱 WhatsApp Template Requirements</h3>
                                {detailed.template_requirements?.map((template, idx) => (
                                    <div key={idx} className={`template-card priority-${template.priority?.toLowerCase()}`}>
                                        <div className="template-header">
                                            <div>
                                                <h4>{template.template_name}</h4>
                                                <span className={`exists-badge ${template.likely_exists ? 'exists' : 'needs-creation'}`}>
                                                    {template.likely_exists ? '✓ Likely Exists' : '⚠ Needs Creation'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="template-body">
                                            <h5>Body Text:</h5>
                                            <pre>{template.body_text}</pre>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="info-section highlight-section">
                                <h3>🤖 AI Flow Creation Prompts</h3>
                                {detailed.flow_creation_prompts?.map((flowPrompt, idx) => (
                                    <div key={idx} className="flow-prompt-card">
                                        <h4>{flowPrompt.prompt_title}</h4>
                                        <div className="prompt-box">
                                            <button 
                                                className="copy-prompt-btn"
                                                onClick={() => copyPromptToClipboard(flowPrompt.complete_prompt)}
                                            >
                                                📋 Copy to Clipboard
                                            </button>
                                            <pre className="prompt-text">{flowPrompt.complete_prompt}</pre>
                                        </div>
                                    </div>
                                ))}
                            </div>
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
                        🤖 AI Analysis & Segments
                    </button>
                    <button 
                        className={activeTab === 'templates' ? 'active' : ''}
                        onClick={() => setActiveTab('templates')}
                    >
                        📱 Templates & Flows
                    </button>
                    <button 
                        className={activeTab === 'calendar' ? 'active' : ''}
                        onClick={() => setActiveTab('calendar')}
                    >
                        📅 Calendar View
                    </button>
                    <button 
                        className={activeTab === 'query' ? 'active' : ''}
                        onClick={() => setActiveTab('query')}
                    >
                        💬 Natural Language Query
                    </button>
                    <a href = "ai-tem-generator" 
                    className='temai'
                    >
                        template generate
                    </a>
                </div>
            </header>

            {error && <div className="error-message">{error}</div>}

            {activeTab === 'ai-analysis' && renderAIAnalysis()}
            {activeTab === 'templates' && renderTemplateManagement()}
            {activeTab === 'calendar' && renderCalendarView()}
            
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

            <style jsx>
                {`
.template-flow-recommendations {
    margin: 20px 0;
    padding: 16px;
    background: #f8f9fa;
    border-radius: 12px;
}

.template-flow-recommendations h4 {
    margin: 0 0 16px 0;
    color: #333;
    display: flex;
    align-items: center;
    gap: 8px;
}

.recommendation-box {
    background: white;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 4px solid #ccc;
}

.template-box {
    border-left-color: #00C49F;
}

.flow-box {
    border-left-color: #0088FE;
}

.needs-creation-box {
    border-left-color: #FFBB28;
    background: #fffbf0;
}

.no-match-box {
    border-left-color: #999;
    background: #f5f5f5;
    text-align: center;
    color: #666;
}

.recommendation-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.recommendation-icon {
    font-size: 1.5rem;
}

.confidence-badge {
    margin-left: auto;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 600;
}

.confidence-badge.high {
    background: #d4edda;
    color: #155724;
}

.confidence-badge.medium {
    background: #fff3cd;
    color: #856404;
}

.needs-creation-badge {
    margin-left: auto;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #fff3cd;
    color: #856404;
}

.recommendation-details {
    margin: 12px 0;
    padding: 12px;
    background: #f8f9fa;
    border-radius: 6px;
}

.recommendation-details p {
    margin: 6px 0;
    font-size: 0.875rem;
}

.match-reason {
    color: #666;
    font-style: italic;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #e0e0e0;
}

.use-template-btn, .use-flow-btn {
    width: 100%;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
    margin-top: 8px;
}

.use-template-btn {
    background: #00C49F;
    color: white;
}

.use-template-btn:hover {
    background: #00A080;
}

.use-flow-btn {
    background: #0088FE;
    color: white;
}

.use-flow-btn:hover {
    background: #0066CC;
}

.suggestion-text {
    background: white;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 12px;
    border-left: 3px solid #FFBB28;
}

.template-preview {
    background: white;
    padding: 12px;
    border-radius: 6px;
    margin-top: 12px;
}

.template-preview h5 {
    margin: 0 0 8px 0;
    color: #333;
}

.body-preview {
    margin-top: 8px;
    padding: 8px;
    background: #f8f9fa;
    border-radius: 4px;
}

.body-preview pre {
    margin: 8px 0 0 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.875rem;
    background: white;
    padding: 8px;
    border-radius: 4px;
}

.copy-prompt-btn {
    width: 100%;
    background: #0088FE;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 12px;
}

.copy-prompt-btn:hover {
    background: #0066CC;
}

.full-prompt-details {
    margin-top: 12px;
    cursor: pointer;
}

.full-prompt-details summary {
    padding: 8px;
    background: #f8f9fa;
    border-radius: 4px;
    cursor: pointer;
}

.full-prompt-text {
    margin-top: 8px;
    padding: 12px;
    background: white;
    border-radius: 4px;
    font-size: 0.75rem;
    max-height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.error-text {
    color: #c62828;
    font-size: 0.875rem;
    text-align: center;
    padding: 12px;
}

.farmer-context {
    display: flex;
    gap: 12px;
    margin-top: 4px;
    flex-wrap: wrap;
}

.context-item {
    font-size: 0.75rem;
    color: #666;
    background: #f0f0f0;
    padding: 2px 8px;
    border-radius: 12px;
}

                .analytics-page { padding: 20px; max-width: 1400px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
                .analytics-header { margin-bottom: 30px; }
                .analytics-header h1 { font-size: 2rem; margin-bottom: 20px; }
                .tab-navigation { display: flex; gap: 10px; border-bottom: 2px solid #e0e0e0; }
                .tab-navigation button { padding: 12px 24px; border: none; background: transparent; cursor: pointer; font-size: 1rem; border-bottom: 3px solid transparent; transition: all 0.3s; }
                .tab-navigation button.active { border-bottom-color: #0088FE; color: #0088FE; font-weight: 600; }
                .error-message { background: #fee; border-left: 4px solid #c00; padding: 15px; margin: 20px 0; border-radius: 4px; }
                
                .cache-status-banner { background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%); padding: 16px 24px; border-radius: 12px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #0088FE; }
                .cache-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
                .cache-icon { font-size: 1.5rem; }
                .cache-expiry { color: #666; font-size: 0.875rem; }
                .refresh-cache-btn { background: #0088FE; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; white-space: nowrap; }
                .refresh-cache-btn:hover { background: #0066CC; }
                .refresh-cache-btn:disabled { background: #ccc; cursor: not-allowed; }
                
                .quota-warning-banner { background: #fff3cd; border: 2px solid #ffc107; border-radius: 12px; padding: 16px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
                .warning-content { display: flex; gap: 12px; align-items: flex-start; flex: 1; }
                .warning-icon { font-size: 1.5rem; }
                .warning-content strong { display: block; margin-bottom: 4px; color: #856404; }
                .warning-content p { margin: 0; color: #856404; font-size: 0.875rem; }
                .close-warning { background: transparent; border: none; font-size: 1.2rem; cursor: pointer; color: #856404; padding: 0; width: 24px; height: 24px; }
                .close-warning:hover { color: #533f03; }
                
                .calendar-section { background: #fff; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                .calendar-header { margin-bottom: 24px; }
                .calendar-header h2 { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
                .calendar-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .calendar-date-card { background: #f8f9fa; border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
                .calendar-date-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-color: #0088FE; }
                 
                .calendar-date-card.urgent { border-color: #FF4444; background: #fff5f5; }
                .date-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
                .date-info { display: flex; flex-direction: column; align-items: center; background: #fff; padding: 8px 12px; border-radius: 8px; min-width: 60px; }
                .date-day { font-size: 0.75rem; color: #666; text-transform: uppercase; }
                .date-number { font-size: 1.5rem; font-weight: bold; color: #333; }
                .date-month { font-size: 0.875rem; color: #666; }
                .urgent-badge { background: #FF4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
                .days-until { font-size: 0.875rem; color: #666; background: #fff; padding: 4px 8px; border-radius: 4px; }
                .events-list { display: flex; flex-direction: column; gap: 8px; }
                .event-item { padding: 8px; border-radius: 6px; font-size: 0.875rem; }
                .event-harvest { background: #fff3cd; border-left: 3px solid #FF8042; }
                .event-growth_stage { background: #d1ecf1; border-left: 3px solid #00C49F; }
                .event-intervention { background: #d4edda; border-left: 3px solid #0088FE; }
                .event-title { font-weight: 600; margin-bottom: 4px; }
                .event-farmer { display: flex; align-items: center; gap: 4px; color: #666; font-size: 0.75rem; }
                .event-farmers { display: flex; align-items: center; gap: 4px; color: #666; font-size: 0.75rem; }
                .event-reason { font-size: 0.75rem; color: #666; margin-top: 4px; font-style: italic; }
                .more-events { text-align: center; color: #666; font-size: 0.875rem; padding: 8px; }
                
                .calendar-controls { display: flex; justify-content: space-between; align-items: center; margin: 20px 0; gap: 16px; flex-wrap: wrap; }
                .view-switcher { display: flex; gap: 8px; }
                .view-switcher button { padding: 10px 20px; border: 2px solid #e0e0e0; background: white; border-radius: 8px; cursor: pointer; transition: all 0.3s; }
                .view-switcher button.active { background: #0088FE; color: white; border-color: #0088FE; }
                .view-switcher button:hover:not(.active) { border-color: #0088FE; }
                .event-filter select { padding: 10px 16px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; cursor: pointer; }
                .back-btn { padding: 10px 20px; background: #666; color: white; border: none; border-radius: 8px; cursor: pointer; }
                .back-btn:hover { background: #444; }
                
                .calendar-date-card.past { opacity: 0.7; border: 2px dashed #ccc; }
                .past-badge { background: #999; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; }
                
                .month-calendar-container { display: flex; flex-direction: column; gap: 32px; }
                .month-calendar { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                .month-calendar h3 { margin: 0 0 16px 0; font-size: 1.5rem; color: #333; }
                .calendar-weekdays { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px; font-weight: 600; text-align: center; color: #666; }
                .calendar-days-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
                .calendar-day { aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 8px; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; transition: all 0.3s; }
                .calendar-day.empty { border: none; cursor: default; }
                .calendar-day.today { background: #e7f3ff; border-color: #0088FE; font-weight: bold; }
                .calendar-day.has-events { background: #f0f7ff; border-color: #0088FE; }
                .calendar-day.has-events:hover { transform: scale(1.05); box-shadow: 0 4px 12px rgba(0,136,254,0.3); }
                .day-number { font-size: 1rem; margin-bottom: 4px; }
                .event-dots { display: flex; gap: 2px; flex-wrap: wrap; justify-content: center; }
                .dot { width: 6px; height: 6px; border-radius: 50%; }
                .dot-harvest { background: #FF8042; }
                .dot-growth_stage { background: #00C49F; }
                .dot-intervention { background: #0088FE; }
                .event-dots .more { font-size: 0.65rem; color: #666; }
                
                .date-details-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
                .date-details-modal .modal-content { background: white; padding: 32px; border-radius: 16px; max-width: 800px; max-height: 90vh; overflow-y: auto; position: relative; }
                .modal-content.large { max-width: 1000px; }
                .events-detailed { display: flex; flex-direction: column; gap: 16px; margin-top: 20px; }
                .event-detail-card { background: #f8f9fa; padding: 20px; border-radius: 12px; border-left: 4px solid #ccc; }
                .event-detail-card.priority-high { border-left-color: #FF4444; }
                .event-detail-card.priority-medium { border-left-color: #FFBB28; }
                .event-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
                .event-importance { background: #fff3cd; padding: 12px; border-radius: 8px; margin: 16px 0; border-left: 4px solid #FFBB28; }
                .event-importance p { margin: 8px 0 0 0; color: #856404; }
                .farmers-list-compact { margin: 20px 0; }
                .farmers-list-compact h4 { display: flex; align-items: center; gap: 8px; margin: 0 0 12px 0; }
                .farmer-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }
                .farmer-info { display: flex; flex-direction: column; gap: 4px; }
                .farmer-name { font-weight: 600; color: #333; }
                .farmer-phone { display: flex; align-items: center; gap: 4px; color: #0088FE; text-decoration: none; font-size: 0.875rem; }
                .whatsapp-btn-small { background: #25D366; color: white; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
                .whatsapp-btn-small:hover { background: #20BA5A; }
                .bulk-actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
                .export-farmers-btn, .copy-numbers-btn { flex: 1; padding: 12px; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
                .export-farmers-btn { background: #0088FE; color: white; }
                .export-farmers-btn:hover { background: #0066CC; }
                .copy-numbers-btn { background: #f0f0f0; color: #333; }
                .copy-numbers-btn:hover { background: #e0e0e0; }
                .no-events { text-align: center; padding: 60px 20px; color: #666; }
                
                .segment-farmers-section { background: #f8f9fa; padding: 24px; border-radius: 12px; margin: 24px 0; }
                .farmers-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
                .farmers-header h3 { display: flex; align-items: center; gap: 8px; margin: 0; }
                .export-btn { background: #0088FE; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; }
                .export-btn:hover { background: #0066CC; }
                .farmers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
                .farmer-card { background: white; padding: 16px; border-radius: 12px; border: 1px solid #e0e0e0; transition: all 0.3s; }
                .farmer-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
                .farmer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
                .farmer-header h4 { margin: 0; color: #333; }
                .farmer-id { font-size: 0.75rem; color: #999; background: #f0f0f0; padding: 2px 8px; border-radius: 4px; }
                .farmer-contact { margin: 12px 0; }
                .contact-row { display: flex; align-items: center; gap: 8px; margin: 8px 0; }
                .contact-row a { color: #0088FE; text-decoration: none; flex: 1; }
                .whatsapp-btn { background: #25D366; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 0.875rem; }
                .whatsapp-btn:hover { background: #20BA5A; }
                .farmer-crop { margin: 12px 0; padding: 8px; background: #f0f7ff; border-radius: 6px; font-size: 0.875rem; }
                .stage-badge { background: #0088FE; color: white; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-size: 0.75rem; }
                .intervention-info { margin: 8px 0; padding: 8px; background: #e7f3ff; border-radius: 6px; font-size: 0.875rem; }
                .intervention-date { color: #666; font-size: 0.75rem; margin-left: 4px; }
                .value-info { margin: 8px 0; padding: 8px; background: #e8f5e9; border-radius: 6px; font-size: 0.875rem; color: #2e7d32; }
                .product-info { margin: 8px 0; padding: 8px; background: #fff3e0; border-radius: 6px; font-size: 0.875rem; }
                .inactive-warning { margin: 8px 0; padding: 8px; background: #ffebee; border-radius: 6px; font-size: 0.875rem; color: #c62828; font-weight: 600; }
                .harvest-info { display: flex; align-items: center; gap: 6px; padding: 8px; background: #fff3cd; border-radius: 6px; color: #856404; font-size: 0.875rem; font-weight: 600; margin: 8px 0; }
                .match-reason { display: flex; align-items: center; gap: 6px; padding: 8px; background: #e7f3ff; border-radius: 6px; color: #004085; font-size: 0.875rem; margin: 8px 0; }
                .next-crop { padding: 8px; background: #d4edda; border-radius: 6px; font-size: 0.875rem; margin: 8px 0; }
                
                .close-modal { position: absolute; top: 16px; right: 16px; background: #f0f0f0; border: none; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; }
                .close-modal:hover { background: #e0e0e0; }
                .loading-analysis, .loading-calendar { text-align: center; padding: 60px 20px; }
                .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #0088FE; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                
                .analysis-summary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px; border-radius: 16px; margin-bottom: 24px; }
                .summary-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }
                .stat-card { background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); padding: 20px; border-radius: 12px; text-align: center; }
                .stat-card h3 { font-size: 2.5rem; margin: 0 0 8px 0; }
                .stat-card p { margin: 0; opacity: 0.9; }
                .key-insights { margin-top: 24px; }
                .key-insights ul { list-style: none; padding: 0; }
                .key-insights li { padding: 8px 0; padding-left: 24px; position: relative; }
                .key-insights li:before { content: '✓'; position: absolute; left: 0; color: #4ade80; font-weight: bold; }
                
                .segments-section { margin: 32px 0; }
                .segments-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; margin-top: 20px; }
                .segment-card { background: white; border-radius: 16px; padding: 24px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
                .segment-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); border-color: #0088FE; }
                .segment-card.priority-high { border-left: 4px solid #FF4444; }
                .segment-card.priority-medium { border-left: 4px solid #FFBB28; }
                .segment-card.priority-low { border-left: 4px solid #00C49F; }
                .segment-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
                .segment-header h3 { margin: 0; font-size: 1.25rem; }
                .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
                .badge.priority-high { background: #fee; color: #c00; }
                .badge.priority-medium { background: #fff3cd; color: #856404; }
                .badge.priority-low { background: #d4edda; color: #155724; }
                .priority-badge.large { padding: 8px 16px; font-size: 1rem; }
                .segment-stats { margin: 16px 0; }
                .segment-stats p { margin: 8px 0; }
                .conversion { color: #0088FE; }
                .revenue { color: #00C49F; font-weight: 600; }
                .avg-spend { color: #FF8042; font-weight: 600; }
                .segment-characteristics { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
                .characteristic-tag { background: #f0f0f0; padding: 4px 12px; border-radius: 16px; font-size: 0.875rem; }
                .upsell-products { margin: 12px 0; padding: 8px; background: #fff3e0; border-radius: 6px; font-size: 0.875rem; }
                .upsell-products strong { display: block; margin-bottom: 4px; }
                .product-tag { display: inline-block; background: #ff9800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px; margin-top: 4px; }
                .view-details-btn { width: 100%; background: #0088FE; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 12px; }
                .view-details-btn:hover { background: #0066CC; }
                
                .flow-prompts-section { margin: 32px 0; background: #f8f9fa; padding: 32px; border-radius: 16px; }
                .section-description { color: #666; margin-bottom: 24px; }
                .prompt-card { background: white; padding: 24px; border-radius: 12px; margin-bottom: 20px; border-left: 4px solid #ccc; }
                .prompt-card.priority-high { border-left-color: #FF4444; }
                .prompt-card.priority-medium { border-left-color: #FFBB28; }
                .prompt-header h3 { margin: 0 0 12px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
                .prompt-meta { color: #666; font-size: 0.875rem; margin-bottom: 16px; }
                .prompt-content { margin: 20px 0; }
                .prompt-text { position: relative; }
                .prompt-text pre { background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; max-height: 300px; margin: 12px 0; }
                .copy-btn, .copy-prompt-btn { background: #0088FE; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
                .copy-btn:hover, .copy-prompt-btn:hover { background: #0066CC; }
                .prompt-details { margin-top: 16px; padding-top: 16px; border-top: 1px solid #e0e0e0; }
                .implementation-notes ul { margin: 8px 0; padding-left: 20px; }
                
                .opportunities-section { margin: 32px 0; }
                .opportunities-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; margin-top: 20px; }
                .opportunity-card { background: white; padding: 24px; border-radius: 12px; border-left: 4px solid #00C49F; }
                .revenue-potential { font-size: 1.25rem; color: #00C49F; font-weight: 700; margin: 12px 0; }
                .difficulty { margin: 12px 0; }
                .badge-easy { background: #d4edda; color: #155724; padding: 4px 12px; border-radius: 16px; }
                .badge-medium { background: #fff3cd; color: #856404; padding: 4px 12px; border-radius: 16px; }
                .badge-hard { background: #fee; color: #c00; padding: 4px 12px; border-radius: 16px; }
                .action-items { margin-top: 16px; }
                .action-items ol { margin: 8px 0; padding-left: 20px; }
                
                .automation-section { margin: 32px 0; }
                .automation-card { background: white; padding: 24px; border-radius: 12px; margin-bottom: 16px; border-left: 4px solid #764ba2; }
                .automation-card.priority-high { border-left-color: #FF4444; }
                .automation-card.priority-medium { border-left-color: #FFBB28; }
                .automation-card h3 { display: flex; justify-content: space-between; align-items: center; margin: 0 0 12px 0; }
                .target-segments { color: #666; font-size: 0.875rem; margin-top: 12px; }
                
                .segment-details-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
                .segment-details-modal .modal-content { background: white; padding: 32px; border-radius: 16px; max-width: 1200px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative; }
                .segment-description { color: #666; margin-bottom: 24px; }
                .segment-full-info { margin-top: 24px; }
                .info-section { background: #f8f9fa; padding: 24px; border-radius: 12px; margin-bottom: 24px; }
                .info-section h3 { margin: 0 0 20px 0; }
                .stage-breakdown { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
                .stage-card { background: white; padding: 16px; border-radius: 8px; border-left: 3px solid #ccc; }
                .stage-card.urgency-high { border-left-color: #FF4444; background: #fff5f5; }
                .stage-card.urgency-medium { border-left-color: #FFBB28; background: #fffbf0; }
                .stage-card.urgency-low { border-left-color: #00C49F; background: #f0fff4; }
                .stage-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
                .stage-header h4 { margin: 0; font-size: 1rem; }
                .stage-percentage { font-size: 1.5rem; font-weight: bold; color: #0088FE; }
                .farmer-count { color: #666; font-size: 0.875rem; margin: 4px 0; }
                .urgency-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin: 4px 0; }
                .action-needed { font-size: 0.875rem; color: #333; margin-top: 8px; font-style: italic; }
                
                .template-card { background: white; padding: 20px; border-radius: 12px; margin-bottom: 16px; border-left: 4px solid #ccc; }
                .template-card.priority-high { border-left-color: #FF4444; }
                .template-card.priority-medium { border-left-color: #FFBB28; }
                .template-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
                .template-header h4 { margin: 0; }
                .exists-badge { display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 0.75rem; margin-left: 8px; }
                .exists-badge.exists { background: #d4edda; color: #155724; }
                .exists-badge.needs-creation { background: #fff3cd; color: #856404; }
                .template-body { margin: 16px 0; }
                .template-body h5 { margin: 8px 0; font-size: 0.875rem; color: #666; }
                .template-body pre { background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 0.875rem; overflow-x: auto; }
                
                .highlight-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
                .highlight-section h3 { color: white; }
                .flow-prompt-card { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 12px; margin-bottom: 16px; color: #333; }
                .flow-prompt-card h4 { margin: 0 0 16px 0; }
                .prompt-box { background: #f5f5f5; padding: 16px; border-radius: 8px; margin-top: 12px; position: relative; }
                .prompt-header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
                .prompt-box pre { background: white; padding: 16px; border-radius: 6px; margin: 0; max-height: 400px; overflow-y: auto; font-size: 0.875rem; }
                
                .template-management-section { padding: 24px; }
                .template-header { margin-bottom: 24px; }
                .template-header h2 { font-size: 2rem; margin-bottom: 8px; }
                .template-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }
                .stat-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 12px; text-align: center; }
                .stat-box h3 { font-size: 2.5rem; margin: 0 0 8px 0; }
                .stat-box p { margin: 0; opacity: 0.9; }
                .templates-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }
                .template-management-card { background: white; padding: 24px; border-radius: 12px; cursor: pointer; transition: all 0.3s; border-left: 4px solid #ccc; }
                .template-management-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
                .template-management-card.priority-high { border-left-color: #FF4444; }
                .template-management-card.priority-medium { border-left-color: #FFBB28; }
                .template-management-card.priority-low { border-left-color: #00C49F; }
                .template-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
                .template-card-header h3 { margin: 0 0 8px 0; font-size: 1.25rem; }
                .segment-tag { display: inline-block; background: #f0f0f0; padding: 4px 12px; border-radius: 16px; font-size: 0.875rem; color: #666; }
                .template-card-stats { display: flex; flex-direction: column; gap: 8px; margin: 16px 0; }
                .stat-item { display: flex; align-items: center; gap: 8px; color: #666; font-size: 0.875rem; }
                .template-language { margin: 12px 0; padding: 8px; background: #f0f7ff; border-radius: 6px; font-size: 0.875rem; }
                .template-actions-preview { margin-top: 16px; }
                .view-farmers-btn { width: 100%; background: #0088FE; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer; font-weight: 600; }
                .view-farmers-btn:hover { background: #0066CC; }
                
.temai {
  padding: 12px 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
  color: black; /* ✅ make text black */
  text-decoration: none; /
}

.temai:hover {
  border-bottom: 3px solid #000; /* optional hover effect */
}


                .template-detail-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; overflow-y: auto; }
                .modal-content.extra-large { max-width: 1400px; width: 100%; background: white; border-radius: 16px; position: relative; max-height: 90vh; display: flex; flex-direction: column; }
                .modal-scroll-wrapper { padding: 32px; overflow-y: auto; flex: 1; }
                .template-detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #e0e0e0; position: sticky; top: -32px; background: white; z-index: 10; padding-top: 32px; margin-top: -32px; }
                .template-detail-header h2 { margin: 0; font-size: 1.75rem; }
                .template-detail-meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
                .meta-item { background: #f8f9fa; padding: 12px; border-radius: 8px; }
                .meta-item strong { display: block; margin-bottom: 4px; color: #666; font-size: 0.875rem; }
                .template-section { margin-bottom: 32px; }
                .template-section h3 { margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }
                .section-hint { color: #666; font-size: 0.875rem; margin-bottom: 12px; }
                .prompt-box-large { background: #f5f5f5; padding: 20px; border-radius: 12px; position: relative; }
                .prompt-box-large pre { background: white; padding: 20px; border-radius: 8px; max-height: 400px; overflow-y: auto; font-size: 0.875rem; margin: 12px 0 0 0; white-space: pre-wrap; word-wrap: break-word; }
                .farmers-actions { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
                .whatsapp-bulk-btn { background: #25D366; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; }
                .whatsapp-bulk-btn:hover { background: #20BA5A; }
                .loading-farmers { text-align: center; padding: 40px; }
                .farmers-table-container { overflow-x: auto; background: white; border-radius: 8px; max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; }
                .farmers-table { width: 100%; border-collapse: collapse; min-width: 900px; }
                .farmers-table th, .farmers-table td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }
                .farmers-table th { background: #f8f9fa; font-weight: 600; position: sticky; top: 0; z-index: 5; }
                .farmers-table tr:hover { background: #f8f9fa; }
                .farmers-table a { color: #0088FE; text-decoration: none; }
                .match-reason-cell { font-size: 0.875rem; color: #666; max-width: 250px; white-space: normal; }
                .whatsapp-btn-table { background: #25D366; color: white; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; }
                .whatsapp-btn-table:hover { background: #20BA5A; }
                .implementation-list { padding-left: 24px; }
                .implementation-list li { margin: 8px 0; line-height: 1.6; }
                
                .query-input-section { background: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; }
                .query-input-section form { display: flex; flex-direction: column; gap: 16px; }
                .query-input-section textarea { width: 100%; min-height: 100px; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; font-family: inherit; resize: vertical; }
                .query-input-section button { background: #0088FE; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600; }
                .query-input-section button:hover { background: #0066CC; }
                .query-input-section button:disabled { background: #ccc; cursor: not-allowed; }
                
                .results-section { background: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; }
                .results-section h2 { margin: 0 0 20px 0; }
                .sql-schema-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
                .schema-display, .sql-display { background: #f8f9fa; padding: 16px; border-radius: 8px; }
                .schema-display h3, .sql-display h3 { margin: 0 0 12px 0; font-size: 1rem; }
                .schema-display pre, .sql-display pre { background: white; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.875rem; max-height: 400px; overflow-y: auto; }
                .highlight { background: #fff3cd; padding: 2px 4px; border-radius: 3px; }
                .table-container { overflow-x: auto; margin: 20px 0; }
                .table-container table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
                .table-container th, .table-container td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
                .table-container th { background: #f8f9fa; font-weight: 600; position: sticky; top: 0; }
                .table-container tr:hover { background: #f8f9fa; }
                .execute-full-btn { background: #00C49F; color: white; border: none; padding: 14px 28px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600; margin-top: 20px; }
                .execute-full-btn:hover { background: #00A080; }
                .execute-full-btn:disabled { background: #ccc; cursor: not-allowed; }
                
                .chart-container { margin-top: 20px; }
                .no-analysis { text-align: center; padding: 60px 20px; }
                .no-analysis button { background: #0088FE; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 600; }
                .no-analysis button:hover { background: #0066CC; }
                
                @media (max-width: 768px) {
                    .tab-navigation { flex-direction: column; }
                    .sql-schema-container { grid-template-columns: 1fr; }
                    .summary-stats { grid-template-columns: 1fr; }
                    .segments-grid { grid-template-columns: 1fr; }
                    .calendar-grid { grid-template-columns: 1fr; }
                    .farmers-grid { grid-template-columns: 1fr; }
                    .templates-grid { grid-template-columns: 1fr; }
                    .template-detail-meta { grid-template-columns: 1fr; }
                    .calendar-controls { flex-direction: column; align-items: stretch; }
                    .view-switcher { flex-direction: column; }
                    .farmers-table { font-size: 0.75rem; }
                    .farmers-table th, .farmers-table td { padding: 8px; }
                    .cache-status-banner { flex-direction: column; gap: 12px; align-items: stretch; }
                    .refresh-cache-btn { width: 100%; }
                    .quota-warning-banner { flex-direction: column; gap: 12px; }

                    .variables-grid-compact {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
    margin-top: 10px;
}

.variable-chip {
    background: #f8f9fa;
    padding: 8px 12px;
    border-radius: 6px;
    border-left: 3px solid #007bff;
    font-size: 0.8rem;
}

.variable-chip strong {
    color: #007bff;
    font-family: 'Courier New', monospace;
    display: block;
    margin-bottom: 4px;
}

.variable-example {
    color: #666;
    font-size: 0.75rem;
    display: block;
    margin-top: 4px;
}

.stats-row {
    display: flex;
    gap: 20px;
    margin: 15px 0;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
}

.stat-item {
    flex: 1;
}

.stat-item strong {
    color: #495057;
}

.implementation-steps ol {
    margin-left: 20px;
    line-height: 1.8;
}

.implementation-steps li {
    margin: 10px 0;
}

.additional-notes {
    margin-top: 15px;
    padding: 15px;
    background: #fff3cd;
    border-radius: 6px;
    border-left: 4px solid #ffc107;
}

.no-prompts {
    text-align: center;
    padding: 40px;
    color: #666;
}
                }
            `}</style>
        </div>
    );
};

export default AnalyticsPage;