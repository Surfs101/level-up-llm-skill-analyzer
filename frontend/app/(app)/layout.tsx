import AppNav from "@/components/app/AppNav";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <AppNav />
      <main className="mx-auto max-w-[1100px] px-6 py-12">{children}</main>
    </>
  );
}
