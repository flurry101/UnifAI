import React from 'react';

export default function RawButton({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'destructive'
  size = 'medium',     // 'small' | 'medium' | 'large'
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) {
  const sizeClasses = {
    small: 'px-4 py-1.5 text-xs tracking-wider',
    medium: 'px-6 py-2.5 text-sm tracking-widest',
    large: 'px-10 py-4 text-base tracking-widest',
  };

  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    destructive: 'btn-destructive',
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`select-none uppercase font-headline transition-none ${variantClasses[variant] || 'btn-primary'} ${sizeClasses[size] || sizeClasses.medium} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

