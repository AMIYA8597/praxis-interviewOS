import React from 'react';

export interface TabsProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const Tabs: React.FC<TabsProps> = ({ children, ...props }) => {
  return (
    <div data-testid="tabs" aria-label="Tabs" {...props}>
      {children}
    </div>
  );
};
