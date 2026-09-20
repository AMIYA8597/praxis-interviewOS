import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CoachingFeedback } from '../src/components/CoachingFeedback';

describe('CoachingFeedback', () => {
  it('renders without crashing', () => {
    const { container } = render(<CoachingFeedback message="Keep up the good work" />);
    expect(container).toBeInTheDocument();
  });
});
