import React from 'react';

export function SecondaryButton({ icon }: { icon: string }) {
  return (
  <div className="btn-wrapper secondary-wrapper">
    {}
    <button className="btn-secondary">
    <i className={`icon-${icon}`} />
    </button>
  </div>
  );
}

