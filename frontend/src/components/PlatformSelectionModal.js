import React, { useState } from 'react';
import './PlatformSelectionModal.css';

const PlatformSelectionModal = ({ isOpen, onClose, onSelect }) => {
  const [selectedPlatform, setSelectedPlatform] = useState(null);

  const platforms = [
    { id: 'linkedin', name: 'LinkedIn', icon: '💼', color: '#0077b5' },
    { id: 'reddit', name: 'Reddit', icon: '🤖', color: '#ff4500' },
    { id: 'email', name: 'Email', icon: '📧', color: '#34a853' }
  ];

  const handleSelect = (platform) => {
    setSelectedPlatform(platform);
  };

  const handleConfirm = () => {
    if (selectedPlatform) {
      onSelect(selectedPlatform);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="platform-modal-overlay" onClick={onClose}>
      <div className="platform-modal" onClick={(e) => e.stopPropagation()}>
        <div className="platform-modal-header">
          <h2>📤 Select Platform to Post</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="platform-modal-body">
          <p className="platform-info">
            Choose where you want to post this content:
          </p>
          
          <div className="platform-options">
            {platforms.map(platform => (
              <div
                key={platform.id}
                className={`platform-option ${selectedPlatform?.id === platform.id ? 'selected' : ''}`}
                onClick={() => handleSelect(platform)}
                style={{ '--platform-color': platform.color }}
              >
                <div className="platform-icon">{platform.icon}</div>
                <div className="platform-name">{platform.name}</div>
                {selectedPlatform?.id === platform.id && (
                  <div className="checkmark">✓</div>
                )}
              </div>
            ))}
          </div>
          
          <div className="platform-modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary" 
              onClick={handleConfirm}
              disabled={!selectedPlatform}
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlatformSelectionModal;
