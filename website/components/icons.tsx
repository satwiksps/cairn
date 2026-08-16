import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export function CheckIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true" {...props}>
      <path d="m3 8.5 3 3 7-7" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function GitHubIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M12 .8a11.4 11.4 0 0 0-3.6 22.2c.6.1.8-.2.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.5-1.4-1.3-1.7-1.3-1.7-1.1-.8.1-.8.1-.8 1.2.1 1.8 1.2 1.8 1.2 1.1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.6-.3-5.4-1.3-5.4-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.1 1.2a10.8 10.8 0 0 1 5.7 0C16.9 4.7 18 5 18 5c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.4 5.7.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6A11.4 11.4 0 0 0 12 .8Z" />
    </svg>
  );
}

export function ShieldIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" {...props}>
      <path d="M10 2.2 16 4.5v4.7c0 4-2.4 6.8-6 8.6-3.6-1.8-6-4.6-6-8.6V4.5l6-2.3Z" stroke="currentColor" strokeWidth="1.4" />
      <path d="m7.2 9.8 1.8 1.8 3.8-4" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

export function SteadlithMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 28 28" fill="none" aria-hidden="true" className={className}>
      <path
        d="M5 4h18v5H10v3h13v12H5v-5h13v-3H5V4Z"
        fill="currentColor"
        fillRule="evenodd"
      />
    </svg>
  );
}
