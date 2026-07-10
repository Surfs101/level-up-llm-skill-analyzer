"use client";

import {
  ArrowRight,
  Bell,
  CheckCircle2,
  Download,
  Menu,
  PlusCircle,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";

import {
  Button,
  Card,
  Chip,
  Divider,
  IconButton,
  Input,
  Textarea,
} from "@/components/ui";

export default function ComponentsDevPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12">
        <h1 className="text-h2">Component primitives</h1>
        <p className="mt-2 text-body text-text-muted">
          Visual review of the UI building blocks. Each section shows every
          variant.
        </p>
      </header>

      <Section title="Button">
        <Row label="Variants">
          <Button variant="primary">Primary action</Button>
          <Button variant="secondary">Secondary action</Button>
          <Button variant="ghost">Ghost action</Button>
        </Row>
        <Row label="Sizes">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </Row>
        <Row label="With icons">
          <Button leftIcon={<Sparkles />}>Generate plan</Button>
          <Button variant="secondary" rightIcon={<ArrowRight />}>
            Continue
          </Button>
          <Button variant="ghost" leftIcon={<Download />} size="sm">
            Export
          </Button>
        </Row>
        <Row label="States">
          <Button loading>Saving</Button>
          <Button disabled>Disabled</Button>
          <Button variant="secondary" disabled>
            Disabled
          </Button>
        </Row>
      </Section>

      <Divider spacing="lg" />

      <Section title="Chip">
        <Row label="Variants">
          <Chip variant="matched" icon={<CheckCircle2 />}>
            JavaScript
          </Chip>
          <Chip variant="missing" icon={<PlusCircle />}>
            Kubernetes
          </Chip>
          <Chip variant="neutral">React</Chip>
          <Chip variant="removable">Frontend</Chip>
        </Row>
        <Row label="Without icons">
          <Chip variant="matched">TypeScript</Chip>
          <Chip variant="missing">GraphQL</Chip>
          <Chip variant="neutral">Tailwind</Chip>
        </Row>
      </Section>

      <Divider spacing="lg" />

      <Section title="Card">
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <h3 className="text-h5">Default card</h3>
            <p className="mt-2 text-body text-text-muted">
              Static container with a 24px padding and a subtle border.
            </p>
          </Card>
          <Card variant="interactive">
            <h3 className="text-h5">Interactive card</h3>
            <p className="mt-2 text-body text-text-muted">
              Hover to see the border lift toward the muted text color.
            </p>
          </Card>
          <Card compact>
            <h3 className="text-h5">Compact card</h3>
            <p className="mt-2 text-body text-text-muted">
              Same chrome with 16px padding for denser layouts.
            </p>
          </Card>
          <Card variant="interactive" compact>
            <h3 className="text-h5">Interactive · compact</h3>
            <p className="mt-2 text-body text-text-muted">
              Both modifiers combined.
            </p>
          </Card>
        </div>
      </Section>

      <Divider spacing="lg" />

      <Section title="Input & textarea">
        <div className="space-y-4">
          <Input placeholder="Type a job title…" />
          <Input placeholder="Disabled input" disabled />
          <Textarea placeholder="Paste the job description here…" />
        </div>
      </Section>

      <Divider spacing="lg" />

      <Section title="Icon button">
        <Row label="Common icons">
          <IconButton icon={<Search />} aria-label="Search" />
          <IconButton icon={<Bell />} aria-label="Notifications" />
          <IconButton icon={<Settings />} aria-label="Settings" />
          <IconButton icon={<Menu />} aria-label="Menu" />
        </Row>
        <Row label="Disabled">
          <IconButton icon={<Bell />} aria-label="Notifications" disabled />
        </Row>
      </Section>

      <Divider spacing="lg" />

      <Section title="Divider">
        <p className="text-caption text-text-muted">Small spacing</p>
        <Divider spacing="sm" />
        <p className="text-caption text-text-muted">Medium spacing</p>
        <Divider spacing="md" />
        <p className="text-caption text-text-muted">Large spacing</p>
        <Divider spacing="lg" />
        <p className="text-caption text-text-muted">After</p>
      </Section>
    </main>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 text-h4">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-2 text-caption text-text-muted">{label}</p>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}
