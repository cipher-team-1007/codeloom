import React from 'react';
import { ProductCard } from './ProductCard';

export function Gallery() {
  return (
  <div className="gallery-grid">
    <ProductCard image="/gallery1.jpg" title="Gallery Item 1" />
    <ProductCard image="/gallery2.jpg" title="Gallery Item 2" />
    <ProductCard image="/gallery3.jpg" title="Gallery Item 3" />
  </div>
  );
}

