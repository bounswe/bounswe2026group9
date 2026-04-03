import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <section className="border-border/70 bg-card/92 shadow-brand-panel w-full max-w-3xl rounded-[2rem] border p-8 text-center sm:p-10">
        <p className="text-accent text-sm font-semibold tracking-[0.24em] uppercase">
          Social Event Mapper
        </p>
        <h1 className="text-foreground mt-4 text-4xl sm:text-5xl">Web Frontend Placeholder</h1>
        <p className="text-muted-foreground mx-auto mt-4 max-w-2xl text-base leading-7 sm:text-lg">
          This temporary landing page replaces the default starter content while the real event
          discovery and creation flows are being built.
        </p>
        <div className="mt-8 flex justify-center">
          <Button asChild size="lg">
            <Link href="/login">Go to login</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
