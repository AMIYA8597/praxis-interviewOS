import os

components = [
    "Input", "Card", "Modal", "Badge", "Table", "Spinner", "Tabs",
    "MetricsDisplay", "TranscriptDisplay", "CoachingFeedback", "HintCard"
]

for name in components:
    path = f"packages/ui/__tests__/{name}.test.tsx"
    with open(path, "w") as f:
        f.write(f'''import React from 'react';
import {{ render }} from '@testing-library/react';
import '@testing-library/jest-dom';
import {{ {name} }} from '../src/components/{name}';

describe('{name}', () => {{
  it('renders without crashing', () => {{
    const {{ getByTestId }} = render(<{name} />);
    expect(getByTestId('{name.lower()}')).toBeInTheDocument();
  }});
}});
''')
