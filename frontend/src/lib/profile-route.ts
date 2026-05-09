/**
 * Returns the profile page href for the given user. When the target is the
 * authenticated user themselves, route to the personal /profile/me page so
 * they land on the editable view instead of the public host profile.
 */
export function getProfileHref(userId: string, currentUserId: string | null): string {
  if (currentUserId && userId === currentUserId) {
    return "/profile/me";
  }
  return `/profile/${userId}`;
}
