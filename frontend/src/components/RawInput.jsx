import React from 'react';

export default function RawInput({
  label,
  helperText,
  error,
  disabled = false,
  value,
  onChange,
  placeholder,
  type = 'text',
  className = '',
  id,
  ...props
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-raw-black font-headline text-sm uppercase mb-1 tracking-wider"
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        type={type}
        disabled={disabled}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`w-full bg-raw-sunken text-raw-black font-mono text-[15px] p-3 border-3 ${
          error
            ? 'border-raw-error'
            : disabled
            ? 'border-raw-disabled bg-raw-disabledBg text-[#888888]'
            : 'border-raw-black hover:bg-raw-sunkenHover focus:border-5 focus:border-raw-black'
        } outline-none transition-none`}
        {...props}
      />
      {helperText && (
        <p
          className={`mt-1 font-body text-xs ${
            error ? 'text-raw-error font-semibold' : 'text-[#444444]'
          }`}
        >
          {helperText}
        </p>
      )}
    </div>
  );
}

