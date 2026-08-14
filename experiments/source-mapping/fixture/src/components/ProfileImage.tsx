import React from 'react';

export function ProfileImage({ src }: { src: string }) {
  return <img className="ambiguous-image" src={src} />;
}

