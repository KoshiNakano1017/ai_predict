export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white py-8 text-center text-xs text-gray-500">
      <div className="mx-auto max-w-5xl flex flex-col items-center gap-6 px-4 sm:flex-row sm:justify-between">
        <div className="flex flex-wrap justify-center gap-4 sm:gap-6">
          <a href="#" className="hover:text-gray-900 transition-colors">利用規約</a>
          <a href="#" className="hover:text-gray-900 transition-colors">プライバシーポリシー</a>
          <a href="#" className="hover:text-gray-900 transition-colors">お問い合わせ</a>
        </div>
        <p className="text-gray-400">AI予測は参考情報です。投資は自己責任でお願いします。</p>
      </div>
      <div className="mt-8 text-gray-400">
        &copy; 2026 CrossFactor. All rights reserved.
      </div>
    </footer>
  );
}
