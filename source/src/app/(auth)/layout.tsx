import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header uiState="guest" />
      <main className="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-12">
        {children}
      </main>
      <Footer />
    </>
  );
}
