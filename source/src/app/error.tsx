"use client";

import { useEffect } from "react";
import { Button } from "@/components/Button";
import { logger } from "@/lib/logger";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: Props) {
  useEffect(() => {
    logger.error("GlobalError", error.message, {
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-4">
      <h2 className="text-xl font-bold text-gray-900">
        予期しないエラーが発生しました
      </h2>
      <p className="text-sm text-gray-500">
        問題が続く場合は、ページを再読み込みしてください。
      </p>
      <Button onClick={reset}>再試行</Button>
    </div>
  );
}
