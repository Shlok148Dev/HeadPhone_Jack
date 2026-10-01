import type { SVGProps } from "react";

/** Small original line icons (24×24, currentColor). Decorative by default. */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 20, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const ChevronLeft = (p: IconProps) => <Svg {...p}><path d="M15 18l-6-6 6-6" /></Svg>;
export const ChevronRight = (p: IconProps) => <Svg {...p}><path d="M9 18l6-6-6-6" /></Svg>;
export const Close = (p: IconProps) => <Svg {...p}><path d="M18 6L6 18M6 6l12 12" /></Svg>;
export const Send = (p: IconProps) => <Svg {...p}><path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" /></Svg>;
export const Open = (p: IconProps) => (
  <Svg {...p}><path d="M14 4h6v6" /><path d="M10 14L20 4" /><path d="M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6" /></Svg>
);
export const Lock = (p: IconProps) => <Svg {...p}><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></Svg>;
export const Sun = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></Svg>
);
export const Moon = (p: IconProps) => <Svg {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></Svg>;
export const Refresh = (p: IconProps) => <Svg {...p}><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 3v6h-6" /></Svg>;
export const Clock = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>;
export const Check = (p: IconProps) => <Svg {...p}><path d="M5 12l5 5L20 7" /></Svg>;
export const Alert = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></Svg>;
export const Sparkle = (p: IconProps) => <Svg {...p}><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /></Svg>;

// ---- Navigation (original outline set; never platform icons) ------------------------------
export const Home = (p: IconProps) => <Svg {...p}><path d="M3 11l9-7 9 7" /><path d="M5 10v10h5v-6h4v6h5V10" /></Svg>;
export const Friends = (p: IconProps) => (
  <Svg {...p}><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><circle cx="17" cy="9" r="2.5" /><path d="M16 14.2a5 5 0 0 1 5.5 5.3" /></Svg>
);
export const Circles = (p: IconProps) => (
  <Svg {...p}><circle cx="8" cy="9" r="5" /><circle cx="16" cy="9" r="5" /><circle cx="12" cy="16" r="5" /></Svg>
);
export const Blend = (p: IconProps) => (
  <Svg {...p}><path d="M4 7h4c4 0 4 10 8 10h4" /><path d="M4 17h4c1.6 0 2.5-1.6 3.3-3.5" /><path d="M20 7h-4c-1.6 0-2.5 1.6-3.3 3.5" /></Svg>
);
export const Trophy = (p: IconProps) => (
  <Svg {...p}><path d="M8 4h8v5a4 4 0 0 1-8 0V4z" /><path d="M8 6H4a3 3 0 0 0 4 4M16 6h4a3 3 0 0 1-4 4" /><path d="M12 13v4M8 20h8" /></Svg>
);
export const User = (p: IconProps) => <Svg {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></Svg>;
export const Settings = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></Svg>
);
export const Plug = (p: IconProps) => (
  <Svg {...p}><path d="M9 2v5M15 2v5" /><path d="M6 7h12v4a6 6 0 0 1-12 0V7z" /><path d="M12 17v5" /></Svg>
);
export const Info = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></Svg>;
export const LogOut = (p: IconProps) => <Svg {...p}><path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4" /><path d="M10 17l-5-5 5-5M5 12h11" /></Svg>;
export const Eye = (p: IconProps) => <Svg {...p}><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></Svg>;
export const Inbox = (p: IconProps) => <Svg {...p}><path d="M4 13l2.5-8h11L20 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" /><path d="M4 13h4.5l1.5 2.5h4l1.5-2.5H20" /></Svg>;
export const Bell = (p: IconProps) => <Svg {...p}><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" /><path d="M10 20a2 2 0 0 0 4 0" /></Svg>;
