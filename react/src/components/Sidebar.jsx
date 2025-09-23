import React from 'react';

const Sidebar = ({ onHide }) => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <strong>click to hide</strong>
        <button onClick={onHide} className="hide-sidebar-btn">×</button>
      </div>
      <div className="description">Drag nodes to the canvas to build your flow.</div>
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
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'flowFormNode')} draggable>
      
        Form Flow
      </div>
       <div className="dndnode" onDragStart={(event) => onDragStart(event, 'askForImageNode')} draggable>
        Ask for Image
      </div>
       <div className="dndnode" onDragStart={(event) => onDragStart(event, 'mediaNode')} draggable>
        Media Message
      </div>
       <div className="dndnode" onDragStart={(event) => onDragStart(event, 'askLocationNode')} draggable>
        Ask for Location
      </div>
       <div className="dndnode" onDragStart={(event) => onDragStart(event, 'askApiNode')} draggable>
        Api request
      </div>
      {/* --- NEW ADVANCED NODE --- */}
      <div className="sidebar-divider">Advanced</div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'askQuestionNode')} draggable>
        Ask a Question
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'buttonsNode')} draggable>
        Text with Buttons
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'imageNode')} draggable>
        Image & Caption
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'interactiveImageNode')} draggable>
        Image with Buttons
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'interactiveListNode')} draggable>
        Interactive List
      </div>
      <div className="dndnode" onDragStart={(event) => onDragStart(event, 'mediaNode')} draggable>
        Media Message
      </div>
    </aside>
  );
};

export default Sidebar;