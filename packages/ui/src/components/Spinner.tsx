import React from 'react';

export interface SpinnerProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const Spinner: React.FC<SpinnerProps> = ({ children, ...props }) => {
  return (
    <div data-testid="spinner" aria-label="Spinner" {...props}>
      {children}
    </div>
  );
};
