import React from 'react';

export function DynamicLink({ isExternal }: { isExternal: boolean }) {
  return (
  <a 
    className={`link ${isExternal ? 'external-link' : 'internal-link'}`} 
    href={isExternal ? "https://example.com" : "/local"}
    target={isExternal ? "_blank" : undefined}
  >
    <span className="icon-arrow" />
  </a>
  );
}

