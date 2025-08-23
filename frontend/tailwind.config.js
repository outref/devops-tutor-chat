/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom colors based on KodeKloud theme
        'kk-bg-dark': '#011627', // rgb(1, 22, 39)
        'kk-text': '#d6deeb', // rgb(214, 222, 235)
        'kk-purple': '#c792ea', // rgb(199, 146, 234)
        'kk-teal': '#7fdbca', // rgb(127, 219, 202)
        'kk-blue': '#0ea5e9',
        'kk-sky': '#22d3ee',
        'kk-indigo': '#818cf8',
        'kk-slate-800': 'rgb(30 41 59 / 0.6)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
