import * as React from "react";

import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      type={type}
      className={cn(
        "border-border bg-background text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/20 flex h-12 w-full rounded-lg border px-3 py-2 text-sm transition outline-none focus-visible:ring-3 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
