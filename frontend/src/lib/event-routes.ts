export const CREATE_EVENT_PAGE_PATH = "/create-event";

export function getEditEventPagePath(eventId: string) {
  return `/edit-event/${eventId}`;
}
