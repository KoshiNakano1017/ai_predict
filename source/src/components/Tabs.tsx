"use client";

import { useState } from "react";

interface Tab {
  key: string;
  label: string;
}

interface Props {
  tabs: Tab[];
  defaultKey?: string;
  onSelect: (key: string) => void;
}

export function Tabs({ tabs, defaultKey, onSelect }: Props) {
  const [active, setActive] = useState(defaultKey ?? tabs[0]?.key ?? "");

  function handleClick(key: string) {
    setActive(key);
    onSelect(key);
  }

  return (
    <div className="flex gap-1 rounded-lg bg-gray-100 p-1" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={active === t.key}
          onClick={() => handleClick(t.key)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            active === t.key
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
