import Footer from "@/components/landing/Footer";
import MarketingNav from "@/components/landing/MarketingNav";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <MarketingNav />
      <main>{children}</main>
      <Footer />
    </>
  );
}
