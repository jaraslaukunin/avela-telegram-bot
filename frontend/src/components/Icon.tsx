/**
 * Мини-набор SVG-иконок (stroke, наследуют цвет текста).
 *
 * Без внешних зависимостей: иконок мало, а пакеты ради трёх штук — лишний
 * вес и лишний риск версий.
 */

function baseProps(className?: string) {
  return {
    className,
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
}

export function HomeIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
    </svg>
  );
}

export function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <rect x="3" y="5" width="18" height="16" rx="2.5" />
      <path d="M3 10h18" />
      <path d="M8 3v4M16 3v4" />
    </svg>
  );
}

export function UserIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21c.8-4 3.9-6.2 7.5-6.2s6.7 2.2 7.5 6.2" />
    </svg>
  );
}

export function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2.2" />
      <circle cx="9" cy="17" r="2.2" />
    </svg>
  );
}

export function SearchIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20.5 20.5-3.9-3.9" />
    </svg>
  );
}

export function PinIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <path d="M12 21.5s-6.2-5.2-6.2-10.1a6.2 6.2 0 1 1 12.4 0c0 4.9-6.2 10.1-6.2 10.1Z" />
      <circle cx="12" cy="11" r="2.3" />
    </svg>
  );
}

export function BellIcon({ className }: { className?: string }) {
  return (
    <svg {...baseProps(className)}>
      <path d="M6 9.2a6 6 0 1 1 12 0c0 4.6 1.8 6.2 1.8 6.2H4.2S6 13.8 6 9.2Z" />
      <path d="M10 20.2a2.2 2.2 0 0 0 4 0" />
    </svg>
  );
}
