import Comparison from "@/components/landing/Comparison";
import Dimensions from "@/components/landing/Dimensions";
import FAQ from "@/components/landing/FAQ";
import FinalCTA from "@/components/landing/FinalCTA";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import Showcase from "@/components/landing/Showcase";
import Trust from "@/components/landing/Trust";

export default function MarketingPage() {
  return (
    <>
      <Hero />
      <Showcase />
      <HowItWorks />
      <Dimensions />
      <Comparison />
      <FAQ />
      <Trust />
      <FinalCTA />
    </>
  );
}
