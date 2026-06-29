"use client";

import { Tabs } from "@/components/Tabs";

interface Props {
  onSelect: (key: string) => void;
}

export function RaceDateTabs({ onSelect }: Props) {
  const tabs = [
    { key: "today", label: "本日" },
    { key: "tomorrow", label: "明日" },
    { key: "past", label: "過去" },
  ];

  return <Tabs tabs={tabs} defaultKey="today" onSelect={onSelect} />;
}
