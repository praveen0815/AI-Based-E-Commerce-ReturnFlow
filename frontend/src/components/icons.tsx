import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function iconProps(props: IconProps): IconProps {
  return {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
    ...props,
  };
}

export function LogoMark(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M5 16.5 12 6l7 10.5" />
      <path d="M8 16.5h8" />
    </svg>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M6 6l12 12" />
      <path d="M18 6 6 18" />
    </svg>
  );
}

export function BellIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2H4.5L6 16Z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </svg>
  );
}

export function LayoutIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M4 9h16" />
      <path d="M9 9v11" />
    </svg>
  );
}

export function ActivityIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M4 13h4l2-5 4 10 2-5h4" />
    </svg>
  );
}

export function ServerIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <rect x="4" y="4" width="16" height="6" rx="1.5" />
      <rect x="4" y="14" width="16" height="6" rx="1.5" />
      <path d="M8 7h.01M8 17h.01" />
    </svg>
  );
}

export function PackageIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M7 8.5 12 4l5 4.5" />
      <path d="M7 8.5V19.5h10V8.5" />
      <path d="M4.5 10.5 12 15l7.5-4.5" />
    </svg>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20" />
      <circle cx="10" cy="8" r="3" />
      <path d="M20 20v-1.2a3 3 0 0 0-2.2-2.9" />
      <path d="M16.2 5.2a3 3 0 0 1 0 5.6" />
    </svg>
  );
}

export function ClipboardIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <rect x="6" y="4" width="12" height="16" rx="2" />
      <path d="M9 4.5h6v2H9z" />
      <path d="M9 11h6M9 15h4" />
    </svg>
  );
}

export function BookIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <path d="M5 5.5h7a3 3 0 0 1 3 3V19.5H8a3 3 0 0 1-3-3z" />
      <path d="M19 5.5h-7a3 3 0 0 0-3 3V19.5h7a3 3 0 0 0 3-3z" />
    </svg>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <svg {...iconProps(props)}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5v2.2M12 18.3v2.2M4.9 6.5l1.6 1.6M17.5 15.9l1.6 1.6M3.5 12h2.2M18.3 12h2.2M4.9 17.5l1.6-1.6M17.5 8.1l1.6-1.6" />
    </svg>
  );
}
