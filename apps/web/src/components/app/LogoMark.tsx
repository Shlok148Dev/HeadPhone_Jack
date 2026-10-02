import { cn } from "@/components/ds";

/**
 * Jingle's mark (D-BRAND-03): a cassette whose earphone cable curls into a "j". Single colour
 * (currentColor), so it is white on dark surfaces and black on light ones. Below 32 px the
 * simplified drawing keeps it legible (favicon sizes).
 */
export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  const small = size <= 32;
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={cn("shrink-0", className)}
    >
      {small ? (
        <>
          <rect x="4" y="19" width="42" height="30" rx="6" strokeWidth="5"/>
          <circle cx="17" cy="32" r="4.2" strokeWidth="4"/>
          <circle cx="33" cy="32" r="4.2" strokeWidth="4"/>
          <circle cx="55" cy="10" r="5" fill="currentColor" stroke="none"/>
          <path d="M55 14v32c0 8-6 13-13 13-5 0-9-3-10.5-7.5" strokeWidth="5"/>
        </>
      ) : (
        <>
          <rect x="5" y="20" width="40" height="27" rx="4.5" strokeWidth="3.2"/>
          <rect x="11" y="25.5" width="28" height="10.5" rx="2.6" strokeWidth="2.4"/>
          <circle cx="18.5" cy="30.75" r="2.6" strokeWidth="2.2"/>
          <circle cx="31.5" cy="30.75" r="2.6" strokeWidth="2.2"/>
          <path d="M21.6 30.75h6.8" strokeWidth="2.2"/>
          <path d="M14.5 47l2.8-5.6h15.4l2.8 5.6" strokeWidth="2.4"/>
          <circle cx="49.5" cy="9.6" r="3.4" fill="currentColor" strokeWidth="1.4"/>
          <path d="M49.5 13v2.2" strokeWidth="3.4"/>
          <circle cx="57.6" cy="12.4" r="3.4" fill="currentColor" strokeWidth="1.4"/>
          <path d="M57.4 15.8v2" strokeWidth="3.4"/>
          <path d="M49.5 15v15.5c0 2.6 2 4.2 4.4 4.2" strokeWidth="2.6"/>
          <path d="M57.3 17.6v8.8c0 4.4-3.4 4.2-3.4 8.3v12.8c0 7.7-5.8 12.2-12.4 12.2-5.3 0-9.4-3.3-10.6-8" strokeWidth="2.9"/>
        </>
      )}
    </svg>
  );
}
