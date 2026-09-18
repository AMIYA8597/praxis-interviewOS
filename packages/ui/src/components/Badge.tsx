import React from 'react';

export interface BadgeProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const Badge: React.FC<BadgeProps> = ({ children, ...props }) => {
  return (
    <div data-testid="badge" aria-label="Badge" {...props}>
      {children}
    </div>
  );
};
