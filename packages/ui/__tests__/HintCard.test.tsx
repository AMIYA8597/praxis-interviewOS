import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HintCard } from '../src/components/HintCard';

describe('HintCard', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<HintCard />);
    expect(getByTestId('hintcard')).toBeInTheDocument();
  });
});
