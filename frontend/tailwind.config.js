/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        raw: {
          black: '#000000',
          white: '#FFFFFF',
          blue: '#0000FF',
          sunken: '#F0F0F0',
          sunkenHover: '#E8E8E8',
          disabled: '#CCCCCC',
          disabledBg: '#F5F5F5',
          success: '#008000',
          warning: '#FFA500',
          error: '#FF0000',
          info: '#0000FF',
        }
      },
      fontFamily: {
        headline: ['"Archivo Black"', 'sans-serif'],
        body: ['"Work Sans"', 'sans-serif'],
        mono: ['"Space Mono"', 'monospace'],
      },
      spacing: {
        'sp-1': '4px',
        'sp-2': '8px',
        'sp-3': '16px',
        'sp-4': '24px',
        'sp-5': '40px',
        'sp-6': '64px',
        'sp-7': '80px',
        'sp-8': '120px',
      },
      borderWidth: {
        '1': '1px',
        '3': '3px',
        '5': '5px',
      },
      borderRadius: {
        none: '0px',
        DEFAULT: '0px',
      },
      boxShadow: {
        none: 'none',
      }
    },
  },
  plugins: [],
}

