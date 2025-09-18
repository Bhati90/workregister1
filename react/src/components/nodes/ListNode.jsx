import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

export default memo(({ data, isConnectable }) => {
    const sections = data.sections || [{ 
        title: 'Section 1', 
        rows: [{ id: 'row_1', title: 'Option 1', description: '' }] 
    }];

    const onUpdate = (field, value) => data.onUpdate(field, value);

    const onSectionChange = (index, field, value) => {
        const newSections = [...sections];
        newSections[index][field] = value;
        onUpdate('sections', newSections);
    };

    const onRowChange = (secIndex, rowIndex, field, value) => {
        const newSections = [...sections];
        newSections[secIndex].rows[rowIndex][field] = value;
        // Generate unique row IDs that will be used as sourceHandle
        newSections[secIndex].rows[rowIndex]['id'] = `item_${secIndex}_${rowIndex}`;
        onUpdate('sections', newSections);
    };

    const addRow = (secIndex) => {
        const newSections = [...sections];
        if (newSections[secIndex].rows.length < 10) { // WhatsApp limit per section
            const newIndex = newSections[secIndex].rows.length;
            newSections[secIndex].rows.push({ 
                id: `item_${secIndex}_${newIndex}`, 
                title: `New Option ${newIndex + 1}`, 
                description: '' 
            });
            onUpdate('sections', newSections);
        }
    };
    
    const removeRow = (secIndex, rowIndex) => {
        const newSections = [...sections];
        newSections[secIndex].rows = newSections[secIndex].rows.filter((_, i) => i !== rowIndex);
        // Re-generate IDs for remaining rows to maintain consistency
        newSections[secIndex].rows.forEach((row, i) => {
            row.id = `item_${secIndex}_${i}`;
        });
        onUpdate('sections', newSections);
    };

    const addSection = () => {
        const newSections = [...sections];
        if (newSections.length < 10) { // WhatsApp limit
            const newIndex = newSections.length;
            newSections.push({ 
                title: `Section ${newIndex + 1}`, 
                rows: [{ id: `item_${newIndex}_0`, title: 'Option 1', description: '' }] 
            });
            onUpdate('sections', newSections);
        }
    };

    const removeSection = (secIndex) => {
        const newSections = [...sections];
        if (newSections.length > 1) { // Keep at least one section
            newSections.splice(secIndex, 1);
            // Re-generate all IDs after section removal
            newSections.forEach((section, sIdx) => {
                section.rows.forEach((row, rIdx) => {
                    row.id = `item_${sIdx}_${rIdx}`;
                });
            });
            onUpdate('sections', newSections);
        }
    };

    return (
        <div className="custom-node list-node">
            <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
            <button onClick={() => data.onDelete(data.id)} className="delete-button">×</button>
            
            <div className="node-header"><strong>Interactive List</strong></div>
            
            <div className="node-content">
                <label>Header Text (Optional):</label>
                <input 
                    type="text" 
                    value={data.header || ''} 
                    onChange={(e) => onUpdate('header', e.target.value)} 
                    placeholder="E.g., Choose an option"
                    maxLength={60}
                />

                <label>Body Text (Required):</label>
                <textarea 
                    value={data.body || ''} 
                    onChange={(e) => onUpdate('body', e.target.value)} 
                    rows={3} 
                    placeholder="E.g., Please select one of the following options"
                    maxLength={1024}
                    required
                />

                <label>Footer Text (Optional):</label>
                <input 
                    type="text" 
                    value={data.footer || ''} 
                    onChange={(e) => onUpdate('footer', e.target.value)} 
                    placeholder="E.g., Powered by Your Company"
                    maxLength={60}
                />

                <label>Button Text (Required):</label>
                <input 
                    type="text" 
                    value={data.buttonText || 'View Options'} 
                    onChange={(e) => onUpdate('buttonText', e.target.value)} 
                    placeholder="E.g., View Options"
                    maxLength={20}
                    required
                />

                <hr className="divider" />
                
                <div className="sections-container">
                    {sections.map((sec, secIndex) => (
                        <div key={secIndex} className="list-section">
                            <div className="section-header">
                                <label>Section {secIndex + 1} Title:</label>
                                {sections.length > 1 && (
                                    <button 
                                        onClick={() => removeSection(secIndex)} 
                                        className="remove-section-btn"
                                        title="Remove Section"
                                    >
                                        🗑️
                                    </button>
                                )}
                            </div>
                            <input 
                                type="text" 
                                value={sec.title} 
                                onChange={(e) => onSectionChange(secIndex, 'title', e.target.value)} 
                                placeholder={`Section ${secIndex + 1}`}
                                maxLength={24}
                            />
                            
                            <div className="rows-container">
                                {sec.rows.map((row, rowIndex) => (
                                    <div key={rowIndex} className="list-row-input">
                                        <div className="row-fields">
                                            <input 
                                                type="text" 
                                                value={row.title} 
                                                onChange={(e) => onRowChange(secIndex, rowIndex, 'title', e.target.value)} 
                                                placeholder="Option Title"
                                                maxLength={24}
                                                required
                                            />
                                            <input 
                                                type="text" 
                                                value={row.description || ''} 
                                                onChange={(e) => onRowChange(secIndex, rowIndex, 'description', e.target.value)} 
                                                placeholder="Optional Description"
                                                maxLength={72}
                                            />
                                        </div>
                                        <button 
                                            onClick={() => removeRow(secIndex, rowIndex)} 
                                            className="remove-btn"
                                            title="Remove Option"
                                        >
                                            ×
                                        </button>
                                    </div>
                                ))}
                                
                                {sec.rows.length < 10 && (
                                    <button 
                                        onClick={() => addRow(secIndex)} 
                                        className="add-btn"
                                    >
                                        + Add Option
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                    
                    {sections.length < 10 && (
                        <button onClick={addSection} className="add-section-btn">
                            + Add Section
                        </button>
                    )}
                </div>
            </div>

            {/* Output handles for each list item */}
            <div className="node-footer">
                {sections.map((sec, secIndex) =>
                    sec.rows.map((row, rowIndex) => (
                        <div key={row.id || `row-${secIndex}-${rowIndex}`} className="output-handle-wrapper">
                            <span className="handle-label">{row.title}</span>
                            <Handle
                                type="source"
                                position={Position.Right}
                                id={row.id} // This ID will be used to match user selections
                                isConnectable={isConnectable}
                                style={{ 
                                    background: '#555',
                                    width: 8,
                                    height: 8
                                }}
                            />
                        </div>
                    ))
                )}
            </div>
        </div>
    );
});