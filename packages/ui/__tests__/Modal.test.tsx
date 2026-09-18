import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Modal } from '../src/components/Modal';

describe('Modal', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<Modal />);
    expect(getByTestId('modal')).toBeInTheDocument();
  });
});
