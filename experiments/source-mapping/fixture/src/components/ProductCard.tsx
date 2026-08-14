import React from 'react';

export function ProductCard({ image, title }: { image: string, title: string }) {
  return (
  <div className="product-card" data-title={title}>
    {}
    <img className="product-image" src={image} />
    <h3>{title}</h3>
  </div>
  );
}

