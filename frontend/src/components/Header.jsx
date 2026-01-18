import { Sparkles } from 'lucide-react';
import './Header.css';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
          <div className="chakra-icon">
            <Sparkles className="chakra-spin" size={28} />
          </div>
          <div className="header-title">
            <h1>Mirror of Maya</h1>
            <p className="header-subtitle">Sudarshana Chakra - Discernment Through Illusion</p>
          </div>
        </div>
        <div className="header-divider"></div>
      </div>
    </header>
  );
};

export default Header;

