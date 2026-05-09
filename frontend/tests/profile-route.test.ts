import { describe, expect, it } from "vitest";

import { getProfileHref } from "@/lib/profile-route";

describe("getProfileHref", () => {
  it("returns the public profile path for another user", () => {
    expect(getProfileHref("user-a", "user-b")).toBe("/profile/user-a");
  });

  it("returns /profile/me when target equals the current user", () => {
    expect(getProfileHref("user-a", "user-a")).toBe("/profile/me");
  });

  it("returns the public profile path when no current user is provided", () => {
    expect(getProfileHref("user-a", null)).toBe("/profile/user-a");
  });
});
