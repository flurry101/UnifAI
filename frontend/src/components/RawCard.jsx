import React from 'react';

export default function RawCard({
  children,
  elevated = false,
  className = '',
  ...props
}) {
  const borderClass = elevated ? 'border-5 border-raw-black' : 'border-3 border-raw-black';

  return (
    <div
      className={`bg-raw-white ${borderClass} p-6 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

