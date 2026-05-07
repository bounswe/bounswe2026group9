import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_FILTER_STATE,
  FilterSidebar,
  type FilterState,
} from "@/components/discovery/filter-sidebar";

const CATEGORIES = [
  { id: "cat-music", name: "Music", is_predefined: true, is_approved: true },
  { id: "cat-food", name: "Food", is_predefined: true, is_approved: true },
];

interface RenderOptions {
  filters?: FilterState;
  isAuthenticated?: boolean;
}

function renderSidebar(options: RenderOptions = {}) {
  const filters = options.filters ?? { ...DEFAULT_FILTER_STATE };
  const onFiltersChange = vi.fn<(next: FilterState) => void>();
  const onApply = vi.fn();
  const onClear = vi.fn();
  const utils = render(
    <FilterSidebar
      filters={filters}
      categories={CATEGORIES}
      categoryCounts={{ "cat-music": 4, "cat-food": 2 }}
      onFiltersChange={onFiltersChange}
      onApply={onApply}
      onClear={onClear}
      activeCount={0}
      isAuthenticated={options.isAuthenticated ?? true}
      mobileOpen={false}
      onMobileClose={vi.fn()}
    />,
  );
  return { ...utils, onFiltersChange, onApply, onClear };
}

afterEach(() => {
  cleanup();
});

describe("FilterSidebar", () => {
  it("renders the five quick-filter buttons in the documented order", () => {
    renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    const group = within(sidebar).getByRole("group", { name: /time window/i });
    const buttons = within(group).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual([
      "Now",
      "Today",
      "Weekend",
      "This Week",
      "Upcoming",
    ]);
  });

  it("renders Bookmarked and Going under My Events only when authenticated", () => {
    const { unmount } = renderSidebar({ isAuthenticated: false });
    expect(screen.queryByText("My Events")).toBeNull();
    expect(screen.queryByRole("button", { name: "Bookmarked" })).toBeNull();
    unmount();

    renderSidebar({ isAuthenticated: true });
    const sidebar = screen.getAllByRole("complementary")[0];
    expect(within(sidebar).getByText("My Events")).toBeInTheDocument();
    expect(within(sidebar).getByRole("button", { name: "Bookmarked" })).toBeInTheDocument();
    expect(within(sidebar).getByRole("button", { name: "Going" })).toBeInTheDocument();
  });

  it("does not include a Past button — Show past events is the only entry point", () => {
    renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    const group = within(sidebar).getByRole("group", { name: /time window/i });
    expect(within(group).queryByRole("button", { name: "Past" })).toBeNull();
    expect(within(sidebar).getByRole("switch", { name: /show past events/i })).toBeInTheDocument();
  });

  it("toggles a quick filter through onFiltersChange", async () => {
    const { onFiltersChange } = renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    await userEvent.click(within(sidebar).getByRole("button", { name: "Today" }));
    expect(onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ temporal: "today" }));
  });

  it("toggles an accessibility checkbox", async () => {
    const { onFiltersChange } = renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    await userEvent.click(within(sidebar).getByRole("checkbox", { name: /wheelchair access/i }));
    const lastCall = onFiltersChange.mock.calls.at(-1);
    expect(lastCall?.[0]).toMatchObject({ accessibility: { wheelchair: true } });
  });

  it("flips the Show past events switch", async () => {
    const { onFiltersChange } = renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    const sw = within(sidebar).getByRole("switch", { name: /show past events/i });
    expect(sw).toHaveAttribute("aria-checked", "false");
    await userEvent.click(sw);
    expect(onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ showPast: true }));
  });

  it("changes the sort option", async () => {
    const { onFiltersChange } = renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    await userEvent.click(
      within(sidebar).getByRole("radio", { name: /distance .*your location/i }),
    );
    expect(onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ sort: "distance" }));
  });

  it("calls onApply and onClear when the action buttons are clicked", async () => {
    const { onApply, onClear } = renderSidebar();
    const sidebar = screen.getAllByRole("complementary")[0];
    await userEvent.click(within(sidebar).getByRole("button", { name: /apply filters/i }));
    expect(onApply).toHaveBeenCalledTimes(1);
    await userEvent.click(within(sidebar).getByRole("button", { name: /clear all/i }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
