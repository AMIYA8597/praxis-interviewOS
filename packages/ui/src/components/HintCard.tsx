import React from 'react';

export interface HintCardProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const HintCard: React.FC<HintCardProps> = ({ children, ...props }) => {
  return (
    <div data-testid="hintcard" aria-label="HintCard" {...props}>
      {children}
    </div>
  );
};
