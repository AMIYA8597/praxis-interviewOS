import React from 'react';

export interface ModalProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const Modal: React.FC<ModalProps> = ({ children, ...props }) => {
  return (
    <div data-testid="modal" aria-label="Modal" {...props}>
      {children}
    </div>
  );
};
