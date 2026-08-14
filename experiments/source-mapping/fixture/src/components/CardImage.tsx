import React from 'react';

export function CardImage({ src, type }: { src: string, type: string }) {
  return (
  <div className={`card-wrapper wrapper-${type}`}>
    {}
    <img className="card-image" src={src} data-type={type} />
  </div>
  );
}

