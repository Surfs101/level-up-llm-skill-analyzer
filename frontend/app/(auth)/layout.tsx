// Minimal auth layout — no app shell, no nav. Centers the child card in the viewport.

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      {children}
    </div>
  );
}
