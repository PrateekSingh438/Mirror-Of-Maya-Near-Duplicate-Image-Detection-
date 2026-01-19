import { Sparkles } from 'lucide-react';

const Header = () => {
  return (
    <header className="fixed top-0 left-0 right-0 h-20 bg-gradient-maya backdrop-blur-lg border-b border-saffron-400/20 z-50 shadow-lg shadow-saffron-400/10">
      <div className="h-full px-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Chakra Icon */}
          <div className="chakra-icon">
            <div className="absolute w-full h-full rounded-full border-2 border-saffron-400/50 animate-pulse-chakra"></div>
            <div className="absolute w-7 h-7 rounded-full border border-gold/30 animate-pulse-inner"></div>
            <Sparkles className="chakra-spin w-7 h-7" style={{ color: '#FF9F1C' }} />
          </div>
          
          {/* Title */}
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-saffron-400 via-gold to-parchment-400 bg-clip-text text-transparent">
              Mirror of Maya
            </h1>
            <p className="text-sm italic text-parchment-600">The Sudarshana Chakra reveals truth within illusion</p>
          </div>
        </div>
        
        {/* Divider */}
        <div className="flex-1 h-px mx-8 bg-gradient-to-r from-transparent via-saffron-400/40 to-transparent"></div>
      </div>
    </header>
  );
};

export default Header;

