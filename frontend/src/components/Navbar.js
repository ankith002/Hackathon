import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <span className="logo-icon"></span>
          <span className="logo-text">CampaignForge</span>
        </Link>

        <button 
          className="navbar-toggle"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          aria-label="Toggle menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        <ul className={`navbar-menu ${isMenuOpen ? 'active' : ''}`}>
          <li>
            <Link 
              to="/" 
              className={isActive('/') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Home
            </Link>
          </li>
          <li>
            <Link 
              to="/dashboard" 
              className={isActive('/dashboard') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Dashboard
            </Link>
          </li>
          <li>
            <Link 
              to="/onboard" 
              className={isActive('/onboard') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Onboard Client
            </Link>
          </li>
          <li>
            <Link 
              to="/content" 
              className={isActive('/content') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Content Approval
            </Link>
          </li>
          <li>
            <Link 
              to="/campaigns" 
              className={isActive('/campaigns') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Campaigns
            </Link>
          </li>
          <li>
            <Link 
              to="/analytics" 
              className={isActive('/analytics') ? 'active' : ''}
              onClick={() => setIsMenuOpen(false)}
            >
              Analytics
            </Link>
          </li>
          <li>
            <Link to="/dashboard" className="btn btn-primary navbar-cta">
              Get Started
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
