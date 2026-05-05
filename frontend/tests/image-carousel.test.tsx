import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { ImageCarousel } from "@/components/event/image-carousel";

afterEach(() => {
  cleanup();
});

describe("ImageCarousel", () => {
  it("shows a 'No Photos' placeholder when there are no images", () => {
    render(<ImageCarousel images={[]} title="Empty event" />);
    expect(screen.getByText(/no photos/i)).toBeInTheDocument();
  });

  it("renders the first image by default and uses the title as the alt text", () => {
    render(
      <ImageCarousel
        images={[
          { id: "i1", image_url: "/i1.jpg", upload_date: "2026-01-01" },
          { id: "i2", image_url: "/i2.jpg", upload_date: "2026-01-02" },
        ]}
        title="Sunset Walk"
      />,
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("alt", expect.stringContaining("Sunset Walk"));
    expect(img).toHaveAttribute("src", "/i1.jpg");
  });

  it("advances and rewinds through images, wrapping at the boundaries", async () => {
    render(
      <ImageCarousel
        images={[
          { id: "i1", image_url: "/i1.jpg", upload_date: "" },
          { id: "i2", image_url: "/i2.jpg", upload_date: "" },
          { id: "i3", image_url: "/i3.jpg", upload_date: "" },
        ]}
        title="Trip"
      />,
    );

    const next = screen.getByRole("button", { name: /next/i });
    const prev = screen.getByRole("button", { name: /previous/i });
    const currentSrc = () => screen.getByRole("img").getAttribute("src") ?? "";

    expect(currentSrc()).toContain("/i1.jpg");
    await userEvent.click(next);
    expect(currentSrc()).toContain("/i2.jpg");
    await userEvent.click(next);
    await userEvent.click(next);
    // Wraps back to the first image
    expect(currentSrc()).toContain("/i1.jpg");
    await userEvent.click(prev);
    // Wraps from first → last when going backwards
    expect(currentSrc()).toContain("/i3.jpg");
  });
});
