import type { Config } from 'tailwindcss'
import daisyui from "daisyui";
import plugin from "@tailwindcss/typography";
import aspectRatio from '@tailwindcss/aspect-ratio';



export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
      daisyui,
      plugin,
      aspectRatio
     
      
  ],
  daisyui: {
    themes: [
      {
        light: {
          "primary": "#2563eb",
          "primary-content": "#eff6ff",
          "secondary": "#0ea5e9",
          "secondary-content": "#f0f9ff",
          "accent": "#38bdf8",
          "accent-content": "#082f49",
          "neutral": "#1e293b",
          "neutral-content": "#f8fafc",
          "base-100": "#ffffff",
          "base-200": "#f8fafc",
          "base-300": "#e2e8f0",
          "base-content": "#0f172a",
          "info": "#2563eb",
          "info-content": "#eff6ff",
          "success": "#059669",
          "success-content": "#ecfdf5",
          "warning": "#d97706",
          "warning-content": "#fffbeb",
          "error": "#dc2626",
          "error-content": "#fef2f2",
        },
      },
      'night',
    ]
  }
} satisfies Config

