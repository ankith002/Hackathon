import React, { useState, useEffect, useMemo, useRef } from 'react';
import './CredentialModal.css';

const CredentialModal = ({ platform, isOpen, onClose, onSave, existingCredentials = {} }) => {
  const [credentials, setCredentials] = useState({});
  const [errors, setErrors] = useState({});
  const initializedRef = useRef(false);
  const prevIsOpenRef = useRef(false);

  useEffect(() => {
    // Only initialize when modal opens, not on every existingCredentials change
    if (isOpen && !prevIsOpenRef.current) {
      const platformLower = platform?.toLowerCase() || '';
      const initialCredentials = {};
      
      // Copy existing credentials
      if (existingCredentials && Object.keys(existingCredentials).length > 0) {
        Object.assign(initialCredentials, existingCredentials);
      }
      
      // Initialize default values for fields that don't have values
      if (platformLower === 'reddit' && !initialCredentials.subreddit) {
        initialCredentials.subreddit = 'test';
      }
      if (platformLower === 'email') {
        if (!initialCredentials.smtp_server) {
          initialCredentials.smtp_server = 'smtp.gmail.com';
        }
        if (!initialCredentials.smtp_port) {
          initialCredentials.smtp_port = '587';
        }
      }
      
      setCredentials(initialCredentials);
      setErrors({});
      initializedRef.current = true;
    } else if (!isOpen && prevIsOpenRef.current) {
      // Reset when modal closes
      setCredentials({});
      setErrors({});
      initializedRef.current = false;
    }
    
    prevIsOpenRef.current = isOpen;
  }, [isOpen, platform]);

  const getPlatformFields = () => {
    const platformLower = platform?.toLowerCase() || '';
    
    if (platformLower === 'linkedin') {
      return [
        { key: 'email', label: 'LinkedIn Email', type: 'email', required: true, hint: 'Your LinkedIn account email' },
        { key: 'password', label: 'LinkedIn Password', type: 'password', required: true, hint: 'Your LinkedIn account password' }
      ];
    } else if (platformLower === 'reddit') {
      return [
        { key: 'email', label: 'Reddit Email/Username', type: 'text', required: true, hint: 'Your Reddit email or username' },
        { key: 'password', label: 'Reddit Password', type: 'password', required: true, hint: 'Your Reddit account password' },
        { key: 'subreddit', label: 'Subreddit', type: 'text', required: true, hint: 'Target subreddit (e.g., test, marketing)', defaultValue: 'test' }
      ];
    } else if (platformLower === 'email') {
      return [
        { key: 'email', label: 'Email Address', type: 'email', required: true, hint: 'Your email address' },
        { key: 'password', label: 'Email Password', type: 'password', required: true, hint: 'Your email password or app-specific password' },
        { key: 'recipient_email', label: 'Recipient Email', type: 'email', required: true, hint: 'Email address to send to' },
        { key: 'smtp_server', label: 'SMTP Server', type: 'text', required: false, hint: 'e.g., smtp.gmail.com', defaultValue: 'smtp.gmail.com' },
        { key: 'smtp_port', label: 'SMTP Port', type: 'number', required: false, hint: 'e.g., 587 for TLS', defaultValue: '587' }
      ];
    }
    return [];
  };
  
  // Memoize platform fields to avoid recreating on every render
  const platformFields = useMemo(() => getPlatformFields(), [platform]);

  const handleChange = (key, value) => {
    setCredentials(prev => {
      const updated = { ...prev };
      updated[key] = value;
      return updated;
    });
    if (errors[key]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  const validate = () => {
    const newErrors = {};
    
    platformFields.forEach(field => {
      if (field.required && !credentials[field.key]) {
        newErrors[field.key] = `${field.label} is required`;
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSave(credentials);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="credential-modal-overlay" onClick={onClose}>
      <div className="credential-modal" onClick={(e) => e.stopPropagation()}>
        <div className="credential-modal-header">
          <h2>🔐 {platform} Credentials</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="credential-modal-body">
          <p className="credential-info">
            Please provide your {platform} credentials to post content automatically.
          </p>
          
          <form onSubmit={handleSubmit} noValidate>
            {platformFields.map(field => (
              <div key={field.key} className="form-group">
                <label htmlFor={`credential-${field.key}`}>
                  {field.label} {field.required && <span className="required">*</span>}
                </label>
                <input
                  type={field.type}
                  id={`credential-${field.key}`}
                  name={field.key}
                  value={String(credentials[field.key] || '')}
                  onChange={(e) => {
                    e.stopPropagation();
                    const value = e.target.value;
                    handleChange(field.key, value);
                  }}
                  onKeyDown={(e) => {
                    e.stopPropagation();
                  }}
                  onKeyUp={(e) => {
                    e.stopPropagation();
                  }}
                  placeholder={field.hint}
                  className={errors[field.key] ? 'error' : ''}
                  autoComplete="off"
                  tabIndex={0}
                  required={field.required}
                />
                {errors[field.key] && (
                  <span className="error-message">{errors[field.key]}</span>
                )}
                {field.hint && !errors[field.key] && (
                  <span className="field-hint">{field.hint}</span>
                )}
              </div>
            ))}
            
            <div className="credential-modal-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Save & Post
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CredentialModal;
