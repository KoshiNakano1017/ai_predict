import { type ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  "data-testid"?: string;
}

const styles: Record<Variant, string> = {
  primary:
    "bg-brand-primary text-white hover:bg-blue-700 focus:ring-brand-primary",
  secondary:
    "bg-gray-100 text-gray-800 hover:bg-gray-200 focus:ring-gray-400 border border-gray-300",
  danger: "bg-brand-danger text-white hover:bg-red-600 focus:ring-red-400",
  ghost: "bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-gray-300",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
