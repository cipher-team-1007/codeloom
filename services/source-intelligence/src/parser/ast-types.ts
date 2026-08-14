export interface AstAttribute {
  type: 'literal' | 'dynamic' | 'boolean';
  value: string | boolean;
}

export interface AstElement {
  file: string;
  component: string;
  tagName: string;
  attributes: Record<string, AstAttribute>;
  location: { line: number; column: number };
  parentTags: string[];
}

