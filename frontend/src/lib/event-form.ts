import type {
  CategoryOption,
  EventCreatePayload,
  EventDetailResponse,
  EventLimitedResponse,
  EventUpdatePayload,
  VenueMetadataPayload,
} from "@/lib/api";

export const EVENT_EDITOR_STEPS = [
  "Basics",
  "Schedule",
  "Location",
  "Media",
  "Venue",
  "Settings",
  "Review",
] as const;

export type EventEditorStep = (typeof EVENT_EDITOR_STEPS)[number];

export interface EventLocationFormValue {
  id: string;
  isPrimary: boolean;
  latitude: string;
  longitude: string;
  name: string;
}

export interface EventFormValues {
  attendeeLimit: string;
  categoryIds: string[];
  description: string;
  endDate: string;
  endTime: string;
  hasAttendeeLimit: boolean;
  healthRequirements: string;
  language: string;
  locations: EventLocationFormValue[];
  price: string;
  quietFriendly: boolean;
  captionsSupport: boolean;
  accessibleRestroom: boolean;
  elevatorAvailable: boolean;
  seatingAvailable: boolean;
  startDate: string;
  startTime: string;
  title: string;
  visibility: "public" | "private";
  wheelchairAccess: boolean;
}

export type EventFormErrors = Partial<Record<string, string>>;

const DEFAULT_DURATION_HOURS = 2;

function pad(value: number) {
  return value.toString().padStart(2, "0");
}

function formatDateInput(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function formatTimeInput(date: Date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function createLocationId() {
  return `location-${Math.random().toString(36).slice(2, 10)}`;
}

function getDefaultStartDate() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 2);
  return start;
}

function buildVenueMetadata(values: EventFormValues): VenueMetadataPayload | null {
  const healthRequirements = values.healthRequirements.trim();
  const language = values.language.trim();
  const price = values.price.trim();

  const metadata: VenueMetadataPayload = {
    accessible_restroom: values.accessibleRestroom,
    captions_support: values.captionsSupport,
    elevator_available: values.elevatorAvailable,
    health_requirements: healthRequirements === "" ? null : healthRequirements,
    language: language === "" ? null : language,
    price: price === "" ? null : price,
    quiet_friendly: values.quietFriendly,
    seating_available: values.seatingAvailable,
    wheelchair_access: values.wheelchairAccess,
  };

  const hasAnyValue =
    metadata.price !== null ||
    metadata.language !== null ||
    metadata.health_requirements !== null ||
    metadata.wheelchair_access ||
    metadata.accessible_restroom ||
    metadata.elevator_available ||
    metadata.seating_available ||
    metadata.captions_support ||
    metadata.quiet_friendly;

  return hasAnyValue ? metadata : null;
}

function parseDateTime(date: string, time: string) {
  if (!date || !time) {
    return null;
  }

  const value = new Date(`${date}T${time}`);
  if (Number.isNaN(value.getTime())) {
    return null;
  }

  return value;
}

function isLatitudeValid(value: string) {
  const parsed = Number(value);
  return value.trim() !== "" && !Number.isNaN(parsed) && parsed >= -90 && parsed <= 90;
}

function isLongitudeValid(value: string) {
  const parsed = Number(value);
  return value.trim() !== "" && !Number.isNaN(parsed) && parsed >= -180 && parsed <= 180;
}

function getDraftDateRange(values: EventFormValues) {
  const now = new Date();
  const fallbackStart = getDefaultStartDate();
  const inputStart = parseDateTime(values.startDate, values.startTime);
  const start = inputStart && inputStart > now ? inputStart : fallbackStart;

  const inputEnd = parseDateTime(values.endDate, values.endTime);
  if (inputEnd && inputEnd > start) {
    return { end: inputEnd, start };
  }

  const fallbackEnd = new Date(start);
  fallbackEnd.setHours(fallbackEnd.getHours() + DEFAULT_DURATION_HOURS);
  return { end: fallbackEnd, start };
}

export function createEmptyLocation(
  overrides: Partial<EventLocationFormValue> = {},
): EventLocationFormValue {
  return {
    id: createLocationId(),
    isPrimary: false,
    latitude: "",
    longitude: "",
    name: "",
    ...overrides,
  };
}

export function createDefaultEventFormValues(): EventFormValues {
  const start = getDefaultStartDate();
  const end = new Date(start);
  end.setHours(end.getHours() + DEFAULT_DURATION_HOURS);

  return {
    accessibleRestroom: false,
    attendeeLimit: "",
    captionsSupport: false,
    categoryIds: [],
    description: "",
    elevatorAvailable: false,
    endDate: formatDateInput(end),
    endTime: formatTimeInput(end),
    hasAttendeeLimit: false,
    healthRequirements: "",
    language: "",
    locations: [createEmptyLocation({ isPrimary: true })],
    price: "",
    quietFriendly: false,
    seatingAvailable: false,
    startDate: formatDateInput(start),
    startTime: formatTimeInput(start),
    title: "",
    visibility: "public",
    wheelchairAccess: false,
  };
}

export function mapEventToFormValues(event: EventDetailResponse): EventFormValues {
  const start = new Date(event.start_datetime);
  const end = new Date(event.end_datetime);

  return {
    accessibleRestroom: event.venue_metadata?.accessible_restroom ?? false,
    attendeeLimit: event.attendee_limit?.toString() ?? "",
    captionsSupport: event.venue_metadata?.captions_support ?? false,
    categoryIds: event.categories.map((category) => category.id),
    description: event.description,
    elevatorAvailable: event.venue_metadata?.elevator_available ?? false,
    endDate: formatDateInput(end),
    endTime: formatTimeInput(end),
    hasAttendeeLimit: event.attendee_limit != null,
    healthRequirements: event.venue_metadata?.health_requirements ?? "",
    language: event.venue_metadata?.language ?? "",
    locations:
      event.locations.length > 0
        ? event.locations.map((location) =>
            createEmptyLocation({
              id: location.id,
              isPrimary: location.is_primary,
              latitude: location.latitude.toString(),
              longitude: location.longitude.toString(),
              name: location.name,
            }),
          )
        : [createEmptyLocation({ isPrimary: true })],
    price: event.venue_metadata?.price ?? "",
    quietFriendly: event.venue_metadata?.quiet_friendly ?? false,
    seatingAvailable: event.venue_metadata?.seating_available ?? false,
    startDate: formatDateInput(start),
    startTime: formatTimeInput(start),
    title: event.title,
    visibility: event.visibility,
    wheelchairAccess: event.venue_metadata?.wheelchair_access ?? false,
  };
}

export function isFullEventResponse(
  event: EventDetailResponse | EventLimitedResponse | { host_id?: string },
): event is EventDetailResponse {
  return "host_id" in event && typeof event.host_id === "string";
}

export function buildEventCreatePayload(values: EventFormValues): EventCreatePayload {
  return {
    attendee_limit: values.hasAttendeeLimit ? Number(values.attendeeLimit) : null,
    category_ids: values.categoryIds,
    description: values.description.trim(),
    end_datetime: buildIsoDateTime(values.endDate, values.endTime),
    locations: buildLocations(values),
    start_datetime: buildIsoDateTime(values.startDate, values.startTime),
    status: "draft",
    title: values.title.trim(),
    venue_metadata: buildVenueMetadata(values),
    visibility: values.visibility,
  };
}

export function buildBootstrapDraftPayload(
  values: EventFormValues,
  categories: CategoryOption[],
): EventCreatePayload {
  const { end, start } = getDraftDateRange(values);
  const fallbackCategoryId = values.categoryIds[0] ?? categories[0]?.id;

  if (!fallbackCategoryId) {
    throw new Error("No event categories are available yet, so the draft cannot be created.");
  }

  const primaryLocation = values.locations[0] ?? createEmptyLocation({ isPrimary: true });
  const bootstrapLocationName =
    primaryLocation.name.trim() || `Draft location ${new Date().toISOString()}`;

  return {
    attendee_limit:
      values.hasAttendeeLimit &&
      values.attendeeLimit.trim() !== "" &&
      Number.isInteger(Number(values.attendeeLimit)) &&
      Number(values.attendeeLimit) > 0
        ? Number(values.attendeeLimit)
        : null,
    category_ids: values.categoryIds.length > 0 ? values.categoryIds : [fallbackCategoryId],
    description: values.description.trim() || "Draft event in progress.",
    end_datetime: end.toISOString(),
    locations: [
      {
        is_primary: true,
        latitude: isLatitudeValid(primaryLocation.latitude) ? Number(primaryLocation.latitude) : 0,
        longitude: isLongitudeValid(primaryLocation.longitude)
          ? Number(primaryLocation.longitude)
          : 0,
        name: bootstrapLocationName,
        order_index: 0,
      },
    ],
    start_datetime: start.toISOString(),
    status: "draft",
    title: values.title.trim() || `Draft event ${Date.now()}`,
    venue_metadata: buildVenueMetadata(values),
    visibility: values.visibility,
  };
}

export function buildEventUpdatePayload(values: EventFormValues): EventUpdatePayload {
  return {
    attendee_limit: values.hasAttendeeLimit ? Number(values.attendeeLimit) : null,
    category_ids: values.categoryIds,
    clear_attendee_limit: !values.hasAttendeeLimit,
    description: values.description.trim(),
    end_datetime: buildIsoDateTime(values.endDate, values.endTime),
    locations: buildLocations(values),
    start_datetime: buildIsoDateTime(values.startDate, values.startTime),
    title: values.title.trim(),
    venue_metadata: buildVenueMetadata(values),
    visibility: values.visibility,
  };
}

export function buildBestEffortEventUpdatePayload(
  values: EventFormValues,
  imageCount: number,
): EventUpdatePayload {
  const payload: EventUpdatePayload = {
    visibility: values.visibility,
  };

  const basicsErrors = validateStep(0, values, imageCount);
  if (!basicsErrors.title && !basicsErrors.description && !basicsErrors.categoryIds) {
    payload.title = values.title.trim();
    payload.description = values.description.trim();
    payload.category_ids = values.categoryIds;
  }

  const scheduleErrors = validateStep(1, values, imageCount);
  if (!scheduleErrors.startDateTime && !scheduleErrors.endDateTime) {
    payload.start_datetime = buildIsoDateTime(values.startDate, values.startTime);
    payload.end_datetime = buildIsoDateTime(values.endDate, values.endTime);
  }

  const locationErrors = validateStep(2, values, imageCount);
  const hasLocationErrors = Object.keys(locationErrors).some(
    (key) => key === "locations" || key.startsWith("location-"),
  );
  if (!hasLocationErrors) {
    payload.locations = buildLocations(values);
  }

  const venueMetadata = buildVenueMetadata(values);
  if (venueMetadata) {
    payload.venue_metadata = venueMetadata;
  }

  const settingsErrors = validateStep(5, values, imageCount);
  if (!values.hasAttendeeLimit) {
    payload.attendee_limit = null;
    payload.clear_attendee_limit = true;
  } else if (!settingsErrors.attendeeLimit) {
    payload.attendee_limit = Number(values.attendeeLimit);
    payload.clear_attendee_limit = false;
  }

  return payload;
}

export function buildIsoDateTime(date: string, time: string) {
  const parsed = parseDateTime(date, time);
  return parsed ? parsed.toISOString() : "";
}

export function getEventDurationLabel(values: EventFormValues) {
  const start = parseDateTime(values.startDate, values.startTime);
  const end = parseDateTime(values.endDate, values.endTime);

  if (!start || !end || end <= start) {
    return null;
  }

  function pluralize(value: number, unit: string) {
    return `${value} ${unit}${value === 1 ? "" : "s"}`;
  }

  let cursor = new Date(start);
  let years = 0;
  let months = 0;
  let days = 0;

  while (true) {
    const next = new Date(cursor);
    next.setFullYear(next.getFullYear() + 1);
    if (next > end) {
      break;
    }

    cursor = next;
    years += 1;
  }

  while (true) {
    const next = new Date(cursor);
    next.setMonth(next.getMonth() + 1);
    if (next > end) {
      break;
    }

    cursor = next;
    months += 1;
  }

  while (true) {
    const next = new Date(cursor);
    next.setDate(next.getDate() + 1);
    if (next > end) {
      break;
    }

    cursor = next;
    days += 1;
  }

  const remainingMinutes = Math.round((end.getTime() - cursor.getTime()) / 60000);
  const hours = Math.floor(remainingMinutes / 60);
  const minutes = remainingMinutes % 60;

  const parts = [
    years > 0 ? pluralize(years, "year") : null,
    months > 0 ? pluralize(months, "month") : null,
    days > 0 ? pluralize(days, "day") : null,
    hours > 0 ? pluralize(hours, "hour") : null,
    minutes > 0 ? pluralize(minutes, "minute") : null,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" ") : "Less than a minute";
}

export function formatEventDateRange(values: EventFormValues) {
  const start = parseDateTime(values.startDate, values.startTime);
  const end = parseDateTime(values.endDate, values.endTime);

  if (!start || !end) {
    return "Add a start and end time";
  }

  const formatter = new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  return `${formatter.format(start)} - ${formatter.format(end)}`;
}

export function validateStep(
  stepIndex: number,
  values: EventFormValues,
  imageCount: number,
): EventFormErrors {
  const errors: EventFormErrors = {};

  if (stepIndex === 0) {
    if (!values.title.trim()) {
      errors.title = "Add a title for the event.";
    }

    if (!values.description.trim()) {
      errors.description = "Add a short description so attendees know what to expect.";
    }

    if (values.categoryIds.length === 0) {
      errors.categoryIds = "Select at least one category.";
    }
  }

  if (stepIndex === 1) {
    const start = parseDateTime(values.startDate, values.startTime);
    const end = parseDateTime(values.endDate, values.endTime);

    if (!values.startDate || !values.startTime || !start) {
      errors.startDateTime = "Choose a valid start date and time.";
    }

    if (!values.endDate || !values.endTime || !end) {
      errors.endDateTime = "Choose a valid end date and time.";
    }

    if (start && start <= new Date()) {
      errors.startDateTime = "Start time needs to be in the future.";
    }

    if (start && end && end <= start) {
      errors.endDateTime = "End time must be after the start time.";
    }
  }

  if (stepIndex === 2) {
    if (values.locations.length === 0) {
      errors.locations = "Add at least one location.";
    }

    values.locations.forEach((location, index) => {
      if (!location.name.trim()) {
        errors[`location-name-${location.id}`] = `Location ${index + 1} needs a name.`;
      }

      const latitude = Number(location.latitude);
      if (location.latitude.trim() === "" || Number.isNaN(latitude)) {
        errors[`location-latitude-${location.id}`] = "Latitude is required.";
      } else if (latitude < -90 || latitude > 90) {
        errors[`location-latitude-${location.id}`] = "Latitude must be between -90 and 90.";
      }

      const longitude = Number(location.longitude);
      if (location.longitude.trim() === "" || Number.isNaN(longitude)) {
        errors[`location-longitude-${location.id}`] = "Longitude is required.";
      } else if (longitude < -180 || longitude > 180) {
        errors[`location-longitude-${location.id}`] = "Longitude must be between -180 and 180.";
      }
    });
  }

  if (stepIndex === 3 && imageCount === 0) {
    errors.images = "Upload at least one image before moving on.";
  }

  if (stepIndex === 5 && values.hasAttendeeLimit) {
    const attendeeLimit = Number(values.attendeeLimit);

    if (!values.attendeeLimit.trim() || Number.isNaN(attendeeLimit)) {
      errors.attendeeLimit = "Add the maximum number of attendees.";
    } else if (!Number.isInteger(attendeeLimit) || attendeeLimit <= 0) {
      errors.attendeeLimit = "Attendee limit must be a positive whole number.";
    }
  }

  return errors;
}

export function getDraftCreationErrors(values: EventFormValues) {
  return {
    ...validateStep(0, values, 0),
    ...validateStep(1, values, 0),
    ...validateStep(2, values, 0),
  };
}

export function getFirstInvalidStep(values: EventFormValues, imageCount: number) {
  for (let stepIndex = 0; stepIndex < EVENT_EDITOR_STEPS.length - 1; stepIndex += 1) {
    if (Object.keys(validateStep(stepIndex, values, imageCount)).length > 0) {
      return stepIndex;
    }
  }

  return null;
}

function buildLocations(values: EventFormValues) {
  const locations = values.locations.map((location, index) => ({
    is_primary: location.isPrimary,
    latitude: Number(location.latitude),
    longitude: Number(location.longitude),
    name: location.name.trim(),
    order_index: index,
  }));

  if (!locations.some((location) => location.is_primary) && locations.length > 0) {
    locations[0].is_primary = true;
  }

  return locations;
}
