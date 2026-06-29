type Color = "blue" | "amber" | "red" | "green" | "gray";

interface Props {
  label: string;
  color?: Color;
}

const colorMap: Record<Color, string> = {
  blue: "bg-blue-100 text-blue-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
  green: "bg-green-100 text-green-800",
  gray: "bg-gray-100 text-gray-700",
};

export function Badge({ label, color = "gray" }: Props) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[color]}`}
    >
      {label}
    </span>
  );
}
