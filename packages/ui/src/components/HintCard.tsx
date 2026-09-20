import React from 'react';

export interface HintCardProps {
  hint: string;
  level: number;
}

export const HintCard: React.FC<HintCardProps> = ({ hint, level }) => {
  const getLevelLabel = () => {
    switch (level) {
      case 1: return 'Level 1: Clarify';
      case 2: return 'Level 2: Approach';
      case 3: return 'Level 3: Solution';
      default: return `Level ${level}`;
    }
  };

  const getLevelColor = () => {
    switch (level) {
      case 1: return 'bg-indigo-900 border-indigo-700 text-indigo-100';
      case 2: return 'bg-blue-900 border-blue-700 text-blue-100';
      case 3: return 'bg-green-900 border-green-700 text-green-100';
      default: return 'bg-gray-800 border-gray-700 text-gray-200';
    }
  };

  return (
    <div className={`p-4 rounded border ${getLevelColor()} shadow-md`}>
      <h4 className="text-sm font-bold uppercase tracking-widest opacity-80 mb-2">
        {getLevelLabel()}
      </h4>
      <p className="text-base leading-relaxed whitespace-pre-wrap">{hint}</p>
    </div>
  );
};
