import React from 'react';

export default function Footer() {
  return (
    <footer className="border-t-3 border-raw-black bg-raw-white py-8 px-4 sm:px-6 mt-16">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 font-mono text-xs uppercase tracking-wider text-raw-black text-center md:text-left">
        <div>
          © 2026 UNIFIED PLATFORM — ALL RIGHTS RESERVED.
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 bg-raw-success border-1 border-raw-black"></span>
          <span className="font-bold">SYSTEM ONLINE.</span>
        </div>
      </div>
    </footer>
  );
}

