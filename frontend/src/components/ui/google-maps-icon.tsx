import React from 'react';

export const GoogleMapsIcon: React.FC<{ className?: string }> = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* Red Top Pin */}
    <path
      d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z"
      fill="#EA4335"
    />
    {/* Inner White Cutout Circle */}
    <circle cx="12" cy="9" r="2.8" fill="#FFFFFF" />
    {/* Bottom Left Green Curve */}
    <path
      d="M12 22s-7-7.75-7-13c0-.82.14-1.61.4-2.35L12 22Z"
      fill="#34A853"
      opacity="0.9"
    />
    {/* Bottom Right Blue Curve */}
    <path
      d="M12 22s7-7.75 7-13c0-.82-.14-1.61-.4-2.35L12 22Z"
      fill="#4285F4"
      opacity="0.9"
    />
    {/* Top Yellow Accent */}
    <path
      d="M12 2c2.15 0 4.07.97 5.36 2.5L12 11.8 6.64 4.5A6.97 6.97 0 0 1 12 2Z"
      fill="#FBBC04"
      opacity="0.95"
    />
    {/* Central Pin Dot */}
    <circle cx="12" cy="9" r="2.5" fill="#FFFFFF" />
  </svg>
);
