import Link from "next/link";
import { Button } from "@/components/Button";

export default function NotFound() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-4">
      <h2 className="text-xl font-bold text-gray-900">
        ページが見つかりません
      </h2>
      <p className="text-sm text-gray-500">
        お探しのページは存在しないか、移動された可能性があります。
      </p>
      <Link href="/">
        <Button>トップに戻る</Button>
      </Link>
    </div>
  );
}
