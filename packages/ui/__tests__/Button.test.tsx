import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Button } from '../src/components/Button';

describe('Button', () => {
  it('renders with label', () => {
    const { getByText } = render(<Button>Click me</Button>);
    expect(getByText('Click me')).toBeInTheDocument();
  });
  
  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    const { getByText } = render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(getByText('Click'));
    expect(onClick).toHaveBeenCalled();
  });
  
  it('disables when disabled prop is true', () => {
    const { getByRole } = render(<Button disabled>Click</Button>);
    expect(getByRole('button')).toBeDisabled();
  });
});
