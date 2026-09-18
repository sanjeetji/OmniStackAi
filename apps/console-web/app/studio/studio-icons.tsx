import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true as const,
};

export function BackArrowIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  );
}

export function SendIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
    </svg>
  );
}

export function FileIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

export function CodeIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="m16 18 6-6-6-6M8 6l-6 6 6 6" />
    </svg>
  );
}

export function PlayIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M5 3v18l15-9Z" />
    </svg>
  );
}

export function WarningIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="m10.29 3.86-8.18 14.18A2 2 0 0 0 4 21h16a2 2 0 0 0 1.89-2.96L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export function CreditIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5c0-1 1-1.5 2.5-1.5s2.5.6 2.5 1.6c0 1.2-1.2 1.4-2.5 1.9-1.3.5-2.5.9-2.5 2.1 0 1 1.1 1.7 2.5 1.7s2.5-.6 2.5-1.5" />
    </svg>
  );
}

export function StopIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="5" y="5" width="14" height="14" rx="1" />
    </svg>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M21 12a9 9 0 0 1-15.3 6.4L3 15" />
      <path d="M3 12a9 9 0 0 1 15.3-6.4L21 9" />
      <path d="M21 3v6h-6M3 21v-6h6" />
    </svg>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  );
}
