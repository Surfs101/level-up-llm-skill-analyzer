import Link from "next/link";
import { ArrowLeft } from "lucide-react";

type StubPageProps = {
  title: string;
  description?: string;
};

export default function StubPage({ title, description }: StubPageProps) {
  return (
    <section className="px-6">
      <div className="mx-auto flex min-h-[60vh] max-w-[640px] flex-col items-center justify-center py-24 text-center">
        <h1 className="text-[28px] font-medium leading-[1.2]">{title}</h1>
        {description ? (
          <p className="mt-4 text-body text-text-muted">{description}</p>
        ) : null}
        <Link
          href="/"
          className="mt-8 inline-flex items-center gap-1.5 text-caption text-text-muted transition-colors duration-[140ms] ease-out hover:text-text"
        >
          <ArrowLeft className="size-3.5" aria-hidden />
          Back to home
        </Link>
      </div>
    </section>
  );
}
