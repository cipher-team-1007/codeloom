import React from 'react';

export function PrimaryButton({ icon }: { icon: string }) {
  return (
  <div className="btn-wrapper primary-wrapper">
    {}
    <button className="btn-primary">
    <i className={`icon-${icon}`} />
    </button>
  </div>
  );
}

