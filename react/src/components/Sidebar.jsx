// src/components/Sidebar.jsx
import React from 'react';

const Sidebar = () => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="sidebar">
      <div className="description">Drag nodes to the canvas to build your flow.</div>
      {/* --- ADD THIS BACK --- */}
      <div 
        className="dndnode" 
        onDragStart={(event) => onDragStart(event, 'templateNode')} 
        draggable
      >
        WhatsApp Template
      </div>
      <div 
        className="dndnode" 
        onDragStart={(event) => onDragStart(event, 'textNode')} 
        draggable
      >
        Text Message
      </div>

       {/* --- NEW NODES --- */}
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'buttonsNode')} draggable>
        Text with Buttons
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'imageNode')} draggable>
        Image & Caption
      </div>
    </aside>
  );
};

export default Sidebar;