import React from 'react';

export default function StatusChip({
  label,
  status = 'default', // 'active' | 'warning' | 'error' | 'default'
  className = '',
}) {
  const styles = {
    active: 'border-raw-success text-raw-success',
    warning: 'border-raw-warning text-raw-warning',
    error: 'border-raw-error text-raw-error',
    default: 'border-raw-black text-raw-black',
  };

  const selectedStyle = styles[status] || styles.default;

  return (
    <span
      className={`inline-block bg-raw-white border-2 ${selectedStyle} px-2.5 py-0.5 font-mono text-[11px] font-bold tracking-wider uppercase ${className}`}
    >
      {label}
    </span>
  );
}

