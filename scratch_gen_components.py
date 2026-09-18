import os

components = [
    "Button", "Input", "Card", "Modal", "Badge", "Table", "Spinner", "Tabs",
    "MetricsDisplay", "TranscriptDisplay", "CoachingFeedback", "HintCard"
]

for name in components:
    path = f"packages/ui/src/components/{name}.tsx"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w") as f:
            f.write(f'''import React from 'react';

export interface {name}Props {{
  children?: React.ReactNode;
  [key: string]: any;
}}

export const {name}: React.FC<{name}Props> = ({{ children, ...props }}) => {{
  return (
    <div data-testid="{name.lower()}" aria-label="{name}" {{...props}}>
      {{children}}
    </div>
  );
}};
''')
