import * as React from "react";

import { cn } from "@/lib/utils";

function Separator({
  className,
  decorative = true,
  orientation = "horizontal",
  ...props
}: React.ComponentProps<"div"> & {
  decorative?: boolean;
  orientation?: "horizontal" | "vertical";
}) {
  return (
    <div
      aria-hidden={decorative}
      data-orientation={orientation}
      data-slot="separator"
      role={decorative ? "presentation" : "separator"}
      className={cn(
        "bg-border shrink-0",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className,
      )}
      {...props}
    />
  );
}

export { Separator };
