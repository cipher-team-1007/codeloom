import React from 'react';
import { ProductCard } from './components/ProductCard';
import { Gallery } from './components/Gallery';
import { PrimaryButton } from './components/PrimaryButton';
import { SecondaryButton } from './components/SecondaryButton';
import { DynamicLink } from './components/DynamicLink';
import { CardImage } from './components/CardImage';

import { ProfileImage } from './components/ProfileImage';
import { BannerImage } from './components/BannerImage';

export default function App() {
  return (
  <main>
    <h1>Accessibility Fixture</h1>

    <section>
    <h2>Case 1: Simple Unique Element (ProductCard)</h2>
    <ProductCard image="/placeholder1.jpg" title="Product 1" />
    </section>

    <section>
    <h2>Case 2: Repeated Component (Gallery)</h2>
    <Gallery />
    </section>

    <section>
    <h2>Case 3: Similar Elements (Primary vs Secondary Button)</h2>
    <div className="button-group">
      <PrimaryButton icon="star" />
      <SecondaryButton icon="heart" />
    </div>
    </section>

    <section>
    <h2>Case 4: Dynamic Attribute (DynamicLink)</h2>
    <DynamicLink isExternal={true} />
    </section>

    <section>
    <h2>Case 5: True Ambiguous Case</h2>
    {}
    <div id="true-ambiguous-container">
      <ProfileImage src="/profile.jpg" />
      <BannerImage src="/banner.jpg" />
    </div>
    </section>
  </main>
  );
}

