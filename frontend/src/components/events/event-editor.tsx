"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  Clock3,
  Globe,
  GripVertical,
  LoaderCircle,
  Lock,
  Menu,
  MapPin,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Navbar } from "@/components/layout/navbar";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CREATE_EVENT_PAGE_PATH, getEditEventPagePath } from "@/lib/event-routes";
import {
  changeEventStatus,
  createEvent,
  deleteEventImage,
  getCategories,
  getErrorMessage,
  getEvent,
  type CategoryOption,
  type EventDetailResponse,
  type EventImage,
  updateEvent,
  uploadEventImage,
} from "@/lib/api";
import {
  buildBestEffortEventUpdatePayload,
  buildBootstrapDraftPayload,
  buildEventCreatePayload,
  buildEventUpdatePayload,
  createDefaultEventFormValues,
  createEmptyLocation,
  EVENT_EDITOR_STEPS,
  formatEventDateRange,
  getDraftCreationErrors,
  getEventDurationLabel,
  getFirstInvalidStep,
  isFullEventResponse,
  mapEventToFormValues,
  validateStep,
  type EventFormErrors,
  type EventFormValues,
} from "@/lib/event-form";
import { cn } from "@/lib/utils";

const EventLocationMap = dynamic(
  () => import("@/components/events/event-location-map").then((module) => module.EventLocationMap),
  {
    loading: () => (
      <div className="border-border/80 bg-brand-surface/35 mt-5 h-[420px] animate-pulse rounded-[12px] border sm:h-[480px] xl:h-[540px]" />
    ),
    ssr: false,
  },
);

interface EventEditorProps {
  eventId?: string;
  mode: "create" | "edit";
}

type FeedbackTone = "error" | "info" | "success";

interface FeedbackMessage {
  message: string;
  tone: FeedbackTone;
}

const STEP_COPY = [
  {
    description: "Name the event, describe the vibe, and tag the right categories.",
    title: "Event basics",
  },
  {
    description: "Choose a future timeslot and make sure the end time wraps after the start.",
    title: "Schedule",
  },
  {
    description: "Add one or more locations. The first primary stop becomes the main venue.",
    title: "Location",
  },
  {
    description: "Upload the cover and supporting images for the event gallery.",
    title: "Media",
  },
  {
    description: "Optional venue details help attendees understand accessibility and logistics.",
    title: "Venue metadata",
  },
  {
    description: "Choose whether the event is visible to everyone or only to approved viewers.",
    title: "Settings",
  },
  {
    description: "Review everything, make final adjustments, then publish.",
    title: "Review & publish",
  },
] as const;

function toBoolean(value: boolean | "indeterminate") {
  return value === true;
}

function FeedbackBanner({ feedback }: { feedback: FeedbackMessage }) {
  return (
    <div
      className={cn(
        "rounded-lg border px-5 py-4 text-sm leading-6",
        feedback.tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-900",
        feedback.tone === "error" && "border-red-200 bg-red-50 text-red-900",
        feedback.tone === "info" && "border-border/80 bg-background/70 text-foreground",
      )}
    >
      {feedback.message}
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) {
    return null;
  }

  return <p className="mt-2 text-sm text-red-700">{message}</p>;
}

function SectionLabel({
  children,
  helper,
}: {
  children: React.ReactNode;
  helper?: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label>{children}</Label>
      {helper ? <p className="text-muted-foreground text-sm">{helper}</p> : null}
    </div>
  );
}

function ToggleCard({
  active,
  description,
  icon,
  onClick,
  title,
}: {
  active: boolean;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  title: string;
}) {
  return (
    <button
      type="button"
      className={cn(
        "rounded-[12px] border px-5 py-5 text-left transition",
        active
          ? "border-brand-dark bg-brand-bg/90 shadow-brand-card"
          : "border-border/80 bg-card/90 hover:border-brand-mid hover:bg-background/60",
      )}
      onClick={onClick}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="bg-background/70 text-brand-dark rounded-lg p-3">{icon}</div>
        <div
          className={cn(
            "flex size-6 items-center justify-center rounded-full border",
            active
              ? "border-brand-dark bg-brand-dark text-white"
              : "border-border text-transparent",
          )}
        >
          <Check className="size-3.5" />
        </div>
      </div>
      <p className="text-lg font-semibold">{title}</p>
      <p className="text-muted-foreground mt-2 text-sm leading-6">{description}</p>
    </button>
  );
}

function StepRail({
  currentStep,
  mobileOpen,
  onMobileClose,
  onMobileOpen,
  onStepSelect,
  stepStates,
}: {
  currentStep: number;
  mobileOpen: boolean;
  onMobileClose: () => void;
  onMobileOpen: () => void;
  onStepSelect: (stepIndex: number) => void;
  stepStates: Array<{ canSelect: boolean; complete: boolean }>;
}) {
  const currentStepLabel = EVENT_EDITOR_STEPS[currentStep];

  return (
    <aside className="h-fit lg:min-w-[240px] lg:px-6 lg:py-8 lg:sticky lg:top-6">
      <div className="lg:hidden">
        <button
          className="border-border/80 bg-background/80 flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left shadow-sm"
          onClick={onMobileOpen}
          type="button"
        >
          <span className="border-border/80 bg-background flex size-9 shrink-0 items-center justify-center rounded-lg border">
            <Menu className="size-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-muted-foreground text-[11px] font-semibold uppercase tracking-[0.12em]">
              Steps
            </p>
            <p className="truncate text-sm font-semibold">
              Step {currentStep + 1}: {currentStepLabel}
            </p>
          </div>
        </button>

        <div
          aria-hidden={!mobileOpen}
          className={cn("fixed inset-0 z-[70] lg:hidden", mobileOpen ? "" : "pointer-events-none")}
        >
          <button
            aria-label="Close steps"
            className={cn(
              "absolute inset-0 bg-black/35 transition-opacity",
              mobileOpen ? "opacity-100" : "opacity-0",
            )}
            onClick={onMobileClose}
            type="button"
          />
          <div
            className={cn(
              "bg-card absolute left-0 top-0 flex h-full w-[min(22rem,88vw)] flex-col border-r border-border/80 shadow-brand-panel transition-transform duration-200",
              mobileOpen ? "translate-x-0" : "-translate-x-full",
            )}
          >
            <div className="border-border/80 flex items-center gap-3 border-b px-4 py-4">
              <span className="border-border/80 bg-background flex size-9 shrink-0 items-center justify-center rounded-lg border">
                <Menu className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">Event steps</p>
                <p className="text-muted-foreground text-xs">
                  Follow the checklist from basics to review.
                </p>
              </div>
              <button
                aria-label="Close steps"
                className="border-border/80 text-muted-foreground hover:bg-brand-mid-alpha hover:text-foreground flex size-8 items-center justify-center rounded-lg border transition-colors"
                onClick={onMobileClose}
                type="button"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              {EVENT_EDITOR_STEPS.map((step, index) => {
                const isComplete = stepStates[index]?.complete ?? false;
                const isActive = index === currentStep;
                const canSelect = stepStates[index]?.canSelect ?? false;

                return (
                  <div className={cn("relative", index < EVENT_EDITOR_STEPS.length - 1 && "pb-8")} key={step}>
                    {index < EVENT_EDITOR_STEPS.length - 1 ? (
                      <div
                        className={cn(
                          "absolute top-9 left-[15px] h-[calc(100%-18px)] w-[2px]",
                          isComplete ? "bg-brand-mid" : "bg-brand-mid-alpha",
                        )}
                      />
                    ) : null}
                    <button
                      className={cn(
                        "relative flex w-full items-start gap-4 rounded-xl text-left transition",
                        canSelect
                          ? "hover:bg-brand-mid-alpha/60 focus-visible:ring-ring/20 cursor-pointer px-2 py-2 outline-none focus-visible:ring-3"
                          : "cursor-default px-2 py-2",
                      )}
                      disabled={!canSelect}
                      onClick={() => onStepSelect(index)}
                      type="button"
                    >
                      <div className="relative z-10 flex flex-col items-center">
                        <div
                          className={cn(
                            "bg-background flex size-8 items-center justify-center rounded-full border-2 text-[13px] font-bold transition",
                            isActive && "border-brand-dark bg-brand-dark text-white",
                            isComplete && "border-brand-mid bg-brand-mid text-white",
                            !isActive &&
                              !isComplete &&
                              "border-border bg-background text-muted-foreground",
                          )}
                        >
                          {isComplete ? <Check className="size-4" /> : index + 1}
                        </div>
                      </div>
                      <div className="pt-[5px]">
                        <p
                          className={cn(
                            "text-sm leading-[1.3]",
                            isActive && "text-foreground font-semibold",
                            isComplete && "text-foreground",
                            !isActive && !isComplete && "text-muted-foreground",
                            !canSelect && !isActive && "opacity-70",
                          )}
                        >
                          {step}
                        </p>
                      </div>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="hidden lg:block">
        {EVENT_EDITOR_STEPS.map((step, index) => {
          const isComplete = stepStates[index]?.complete ?? false;
          const isActive = index === currentStep;
          const canSelect = stepStates[index]?.canSelect ?? false;

          return (
            <div className={cn("relative", index < EVENT_EDITOR_STEPS.length - 1 && "pb-8")} key={step}>
              {index < EVENT_EDITOR_STEPS.length - 1 ? (
                <div
                  className={cn(
                    "absolute top-9 left-[15px] h-[calc(100%-18px)] w-[2px]",
                    isComplete ? "bg-brand-mid" : "bg-brand-mid-alpha",
                  )}
                />
              ) : null}
              <button
                className={cn(
                  "relative flex w-full items-start gap-4 rounded-xl text-left transition",
                  canSelect
                    ? "hover:bg-brand-mid-alpha/60 focus-visible:ring-ring/20 cursor-pointer px-2 py-2 outline-none focus-visible:ring-3"
                    : "cursor-default px-2 py-2",
                )}
                disabled={!canSelect}
                onClick={() => onStepSelect(index)}
                type="button"
              >
                <div className="relative z-10 flex flex-col items-center">
                  <div
                    className={cn(
                      "bg-background flex size-8 items-center justify-center rounded-full border-2 text-[13px] font-bold transition",
                      isActive && "border-brand-dark bg-brand-dark text-white",
                      isComplete && "border-brand-mid bg-brand-mid text-white",
                      !isActive &&
                        !isComplete &&
                        "border-border bg-background text-muted-foreground",
                    )}
                  >
                    {isComplete ? <Check className="size-4" /> : index + 1}
                  </div>
                </div>

                <div className="pt-[5px]">
                  <p
                    className={cn(
                      "text-sm leading-[1.3]",
                      isActive && "text-foreground font-semibold",
                      isComplete && "text-foreground",
                      !isActive && !isComplete && "text-muted-foreground",
                      !canSelect && !isActive && "opacity-70",
                    )}
                  >
                    {step}
                  </p>
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function SummaryCard({
  children,
  onEdit,
  title,
}: {
  children: React.ReactNode;
  onEdit: () => void;
  title: string;
}) {
  return (
    <Card className="border-border/80 bg-card/92 shadow-brand-card rounded-[12px]">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-xl">{title}</CardTitle>
          <Button onClick={onEdit} size="sm" type="button" variant="ghost">
            Edit
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">{children}</CardContent>
    </Card>
  );
}

export function EventEditor({ eventId, mode }: EventEditorProps) {
  const router = useRouter();
  const { user } = useAuth();
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [eventStatus, setEventStatus] = useState<EventDetailResponse["status"] | "draft">("draft");
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(
    mode === "create"
      ? {
          message: "You can save progress anytime while building the event.",
          tone: "info",
        }
      : null,
  );
  const [fieldErrors, setFieldErrors] = useState<EventFormErrors>({});
  const [formValues, setFormValues] = useState<EventFormValues>(createDefaultEventFormValues);
  const [images, setImages] = useState<EventImage[]>([]);
  const [isBootstrapping, setIsBootstrapping] = useState(mode === "edit");
  const [isDeletingImageId, setIsDeletingImageId] = useState<string | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingImages, setIsUploadingImages] = useState(false);
  const [isEditAccessDenied, setIsEditAccessDenied] = useState(false);
  const [activeLocationId, setActiveLocationId] = useState<string | null>(null);
  const [dragLocationId, setDragLocationId] = useState<string | null>(null);
  const [dragOverLocationId, setDragOverLocationId] = useState<string | null>(null);
  const [hasConfirmedSchedule, setHasConfirmedSchedule] = useState(mode === "edit");
  const [hasConfirmedSettings, setHasConfirmedSettings] = useState(mode === "edit");
  const [mobileStepsOpen, setMobileStepsOpen] = useState(false);
  const [persistedEventId, setPersistedEventId] = useState<string | null>(eventId ?? null);
  const [startedAtLoad, setStartedAtLoad] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadEditor() {
      setIsBootstrapping(mode === "edit");
      setIsEditAccessDenied(false);

      try {
        const [loadedCategories, loadedEvent] = await Promise.all([
          getCategories(),
          mode === "edit" && eventId ? getEvent(eventId) : Promise.resolve(null),
        ]);

        if (ignore) {
          return;
        }

        setCategories(loadedCategories);

        if (loadedEvent) {
          if (!isFullEventResponse(loadedEvent)) {
            throw new Error(
              "This event cannot be edited because the full event details are unavailable.",
            );
          }

          const fullEvent = loadedEvent;
          if (mode === "edit" && user?.id && fullEvent.host_id !== user.id) {
            setIsEditAccessDenied(true);
            setFeedback({
              message: "Only the host can open this event in edit mode.",
              tone: "error",
            });
            return;
          }

          setFormValues(mapEventToFormValues(fullEvent));
          setImages(fullEvent.images);
          setPersistedEventId(fullEvent.id);
          setEventStatus(fullEvent.status);
          setStartedAtLoad(new Date(fullEvent.start_datetime) <= new Date());
        }
      } catch (error) {
        if (!ignore) {
          setFeedback({
            message: getErrorMessage(error, "Unable to load the event editor."),
            tone: "error",
          });
        }
      } finally {
        if (!ignore) {
          setIsBootstrapping(false);
        }
      }
    }

    void loadEditor();

    return () => {
      ignore = true;
    };
  }, [eventId, mode, user?.id]);

  const currentCopy = STEP_COPY[currentStep];
  const durationLabel = useMemo(() => getEventDurationLabel(formValues), [formValues]);
  const selectedCategories = useMemo(
    () => categories.filter((category) => formValues.categoryIds.includes(category.id)),
    [categories, formValues.categoryIds],
  );
  const editHref = persistedEventId ? getEditEventPagePath(persistedEventId) : undefined;
  const activeLocation = useMemo(
    () => formValues.locations.find((location) => location.id === activeLocationId) ?? null,
    [activeLocationId, formValues.locations],
  );
  const activeLocationIndex = useMemo(
    () =>
      activeLocation
        ? formValues.locations.findIndex((location) => location.id === activeLocation.id)
        : -1,
    [activeLocation, formValues.locations],
  );
  const selectedAccessibilityCount = useMemo(
    () =>
      [
        formValues.wheelchairAccess,
        formValues.accessibleRestroom,
        formValues.elevatorAvailable,
        formValues.seatingAvailable,
        formValues.captionsSupport,
        formValues.quietFriendly,
      ].filter(Boolean).length,
    [formValues],
  );
  const hasVenueDetails = useMemo(
    () =>
      Boolean(
        formValues.healthRequirements.trim() ||
          formValues.wheelchairAccess ||
          formValues.accessibleRestroom ||
          formValues.elevatorAvailable ||
          formValues.seatingAvailable ||
          formValues.captionsSupport ||
          formValues.quietFriendly,
      ),
    [formValues],
  );
  const isScheduleConfirmed = mode === "edit" || hasConfirmedSchedule;
  const isSettingsConfirmed = mode === "edit" || hasConfirmedSettings;
  const stepCompletion = useMemo(
    () =>
      EVENT_EDITOR_STEPS.map((_, index) =>
        index === 0 || index === 1 || index === 2
          ? index === 1
            ? isScheduleConfirmed &&
              Object.keys(validateStep(index, formValues, images.length)).length === 0
            : Object.keys(validateStep(index, formValues, images.length)).length === 0
          : index === 3
            ? images.length > 0
          : index === 4
              ? hasVenueDetails && Object.keys(validateStep(4, formValues, images.length)).length === 0
            : index === 5
                ? isSettingsConfirmed &&
                  Object.keys(validateStep(5, formValues, images.length)).length === 0
                :
                  getFirstInvalidStep(formValues, images.length) == null &&
                  isScheduleConfirmed &&
                  isSettingsConfirmed,
      ),
    [formValues, hasVenueDetails, images.length, isScheduleConfirmed, isSettingsConfirmed],
  );
  const stepStates = useMemo(
    () =>
      EVENT_EDITOR_STEPS.map((_, index) => ({
        canSelect:
          mode === "edit" ||
          index <= currentStep ||
          stepCompletion.slice(0, index).every(Boolean),
        complete: stepCompletion[index] ?? false,
      })),
    [currentStep, mode, stepCompletion],
  );

  useEffect(() => {
    const hasActiveLocation =
      activeLocationId != null &&
      formValues.locations.some((location) => location.id === activeLocationId);

    if (hasActiveLocation) {
      return;
    }

    setActiveLocationId(formValues.locations[0]?.id ?? null);
  }, [activeLocationId, formValues.locations]);

  useEffect(() => {
    setMobileStepsOpen(false);
  }, [currentStep]);

  useEffect(() => {
    setHasConfirmedSchedule(mode === "edit");
    setHasConfirmedSettings(mode === "edit");
  }, [eventId, mode]);

  function clearValidationFeedback() {
    setFieldErrors({});

    if (feedback?.tone === "error") {
      setFeedback(null);
    }
  }

  function patchFormValues(patch: Partial<EventFormValues>) {
    setFormValues((currentValues) => {
      const next = { ...currentValues, ...patch };

      // Re-validate date/time inline whenever a datetime field changes
      const isDateTimePatch =
        "startDate" in patch ||
        "startTime" in patch ||
        "endDate" in patch ||
        "endTime" in patch;

      if (isDateTimePatch) {
        const dateErrors = validateStep(1, next, 0);
        setFieldErrors((prev) => ({
          ...prev,
          startDateTime: dateErrors.startDateTime,
          endDateTime: dateErrors.endDateTime,
        }));
        // Clear any non-date feedback banner
        if (!dateErrors.startDateTime && !dateErrors.endDateTime) {
          setFeedback(null);
        }
      } else {
        clearValidationFeedback();
      }

      return next;
    });
  }

  function patchLocation(locationId: string, patch: Partial<EventFormValues["locations"][number]>) {
    clearValidationFeedback();
    setFormValues((currentValues) => ({
      ...currentValues,
      locations: currentValues.locations.map((location) =>
        location.id === locationId ? { ...location, ...patch } : location,
      ),
    }));
  }

  function setPrimaryLocation(locationId: string) {
    clearValidationFeedback();
    setFormValues((currentValues) => ({
      ...currentValues,
      locations: currentValues.locations.map((location) => ({
        ...location,
        isPrimary: location.id === locationId,
      })),
    }));
  }

  function addLocation() {
    clearValidationFeedback();
    const newLocation = createEmptyLocation();
    setActiveLocationId(newLocation.id);
    setFormValues((currentValues) => ({
      ...currentValues,
      locations: [...currentValues.locations, newLocation],
    }));
  }

  function removeLocation(locationId: string) {
    clearValidationFeedback();
    setFormValues((currentValues) => {
      if (currentValues.locations.length === 1) {
        return {
          ...currentValues,
          locations: [createEmptyLocation({ isPrimary: true })],
        };
      }

      const nextLocations = currentValues.locations.filter(
        (location) => location.id !== locationId,
      );
      if (!nextLocations.some((location) => location.isPrimary) && nextLocations.length > 0) {
        nextLocations[0] = { ...nextLocations[0], isPrimary: true };
      }

      return {
        ...currentValues,
        locations: nextLocations,
      };
    });
  }

  function reorderLocations(sourceLocationId: string, targetLocationId: string) {
    if (sourceLocationId === targetLocationId) {
      return;
    }

    clearValidationFeedback();
    setFormValues((currentValues) => {
      const sourceIndex = currentValues.locations.findIndex(
        (location) => location.id === sourceLocationId,
      );
      const targetIndex = currentValues.locations.findIndex(
        (location) => location.id === targetLocationId,
      );

      if (sourceIndex === -1 || targetIndex === -1) {
        return currentValues;
      }

      const nextLocations = [...currentValues.locations];
      const [movedLocation] = nextLocations.splice(sourceIndex, 1);
      nextLocations.splice(targetIndex, 0, movedLocation);

      return {
        ...currentValues,
        locations: nextLocations,
      };
    });
    setActiveLocationId(sourceLocationId);
  }

  function showValidation(errors: EventFormErrors, message: string) {
    setFieldErrors(errors);
    setFeedback({ message, tone: "error" });
  }

  function getFirstDraftInvalidStep() {
    const errors = getDraftCreationErrors(formValues);

    if (errors.title || errors.description || errors.categoryIds) {
      return 0;
    }

    if (errors.startDateTime || errors.endDateTime) {
      return 1;
    }

    return 2;
  }

  async function createDraftIfNeeded({
    allowBootstrap = false,
  }: { allowBootstrap?: boolean } = {}) {
    if (persistedEventId) {
      return persistedEventId;
    }

    if (allowBootstrap) {
      const created = await createEvent(buildBootstrapDraftPayload(formValues, categories));
      setPersistedEventId(created.id);
      setEventStatus(created.status);
      setImages(created.images);
      return created.id;
    }

    const draftErrors = getDraftCreationErrors(formValues);
    if (Object.keys(draftErrors).length > 0) {
      const nextStep = getFirstDraftInvalidStep();
      setCurrentStep(nextStep);
      showValidation(
        draftErrors,
        "Finish basics, schedule, and at least one location before the first draft can be created.",
      );
      return null;
    }

    const created = await createEvent(buildEventCreatePayload(formValues));
    setPersistedEventId(created.id);
    setEventStatus(created.status);
    setFormValues(mapEventToFormValues(created));
    setImages(created.images);
    return created.id;
  }

  async function handleSaveProgress() {
    setIsSaving(true);
    clearValidationFeedback();

    try {
      const usedBootstrap = !persistedEventId;
      const ensuredEventId = await createDraftIfNeeded({ allowBootstrap: true });
      if (!ensuredEventId) {
        return;
      }

      const saved = await updateEvent(
        ensuredEventId,
        buildBestEffortEventUpdatePayload(formValues, images.length),
      );
      setPersistedEventId(saved.id);
      setEventStatus(saved.status);
      setImages(saved.images);
      setFeedback({
        message:
          mode === "edit"
            ? "Latest valid changes were saved."
            : usedBootstrap
              ? "Draft saved. You can keep editing from any step."
              : "Draft saved.",
        tone: "success",
      });
    } catch (error) {
      setFeedback({
        message: getErrorMessage(error, "Unable to save the current event state."),
        tone: "error",
      });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleNext() {
    const errors =
      currentStep === EVENT_EDITOR_STEPS.length - 1 ? {} : validateCurrentStep(currentStep);
    if (Object.keys(errors).length > 0) {
      showValidation(errors, "Fix the highlighted fields before moving to the next step.");
      return;
    }

    if (currentStep === 1 && mode === "create" && !hasConfirmedSchedule) {
      setHasConfirmedSchedule(true);
    }

    if (currentStep === 5 && mode === "create" && !hasConfirmedSettings) {
      setHasConfirmedSettings(true);
    }

    if (currentStep === 2 && !persistedEventId) {
      setIsSaving(true);

      try {
        const createdEventId = await createDraftIfNeeded();
        if (!createdEventId) {
          return;
        }

        setFeedback({
          message: "Draft created. You can add media now.",
          tone: "success",
        });
      } catch (error) {
        setFeedback({
          message: getErrorMessage(error, "Unable to create the draft before media upload."),
          tone: "error",
        });
        return;
      } finally {
        setIsSaving(false);
      }
    }

    setCurrentStep((step) => Math.min(step + 1, EVENT_EDITOR_STEPS.length - 1));
  }

  function handleBack() {
    clearValidationFeedback();
    setCurrentStep((step) => Math.max(step - 1, 0));
  }

  function handleStepSelect(stepIndex: number) {
    if (stepIndex === currentStep) {
      return;
    }

    clearValidationFeedback();
    setCurrentStep(stepIndex);
  }

  async function handlePublish() {
    const invalidStep = getFirstInvalidStep(formValues, images.length);
    if (invalidStep != null) {
      const errors = validateCurrentStep(invalidStep);
      setCurrentStep(invalidStep);
      showValidation(errors, "Complete each required step before publishing.");
      return;
    }

    setIsPublishing(true);
    clearValidationFeedback();

    try {
      const savedEvent = persistedEventId
        ? await updateEvent(persistedEventId, buildEventUpdatePayload(formValues))
        : await createEvent(buildEventCreatePayload(formValues));

      const publishedEvent = await changeEventStatus(savedEvent.id, { status: "published" });
      setPersistedEventId(publishedEvent.id);
      setEventStatus(publishedEvent.status);
      setFormValues(mapEventToFormValues(publishedEvent));
      setImages(publishedEvent.images);
      setFeedback({ message: "Event published successfully.", tone: "success" });

      if (mode === "create") {
        router.replace(getEditEventPagePath(publishedEvent.id));
      }
    } catch (error) {
      setFeedback({
        message: getErrorMessage(error, "Unable to publish the event."),
        tone: "error",
      });
    } finally {
      setIsPublishing(false);
    }
  }

  async function handleImageUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";

    if (files.length === 0) {
      return;
    }

    setIsUploadingImages(true);
    clearValidationFeedback();

    try {
      const ensuredEventId = await createDraftIfNeeded();
      if (!ensuredEventId) {
        return;
      }

      const uploadedImages: EventImage[] = [];
      for (const file of files) {
        const uploaded = await uploadEventImage(ensuredEventId, file);
        uploadedImages.push(uploaded);
      }

      setImages((currentImages) => [...currentImages, ...uploadedImages]);
      setFeedback({
        message:
          uploadedImages.length === 1
            ? "Image uploaded."
            : `${uploadedImages.length} images uploaded.`,
        tone: "success",
      });
    } catch (error) {
      setFeedback({
        message: getErrorMessage(error, "Unable to upload the selected images."),
        tone: "error",
      });
    } finally {
      setIsUploadingImages(false);
    }
  }

  async function handleDeleteImage(imageId: string) {
    if (!persistedEventId) {
      return;
    }

    setIsDeletingImageId(imageId);
    clearValidationFeedback();

    try {
      await deleteEventImage(persistedEventId, imageId);
      setImages((currentImages) => currentImages.filter((image) => image.id !== imageId));
      setFeedback({ message: "Image removed.", tone: "success" });
    } catch (error) {
      setFeedback({
        message: getErrorMessage(error, "Unable to delete the image."),
        tone: "error",
      });
    } finally {
      setIsDeletingImageId(null);
    }
  }

  function validateCurrentStep(stepIndex: number) {
    if (stepIndex === 6) {
      return {};
    }

    return getStepErrors(stepIndex);
  }

  function getStepErrors(stepIndex: number) {
    return validateStep(stepIndex, formValues, images.length);
  }

  const reviewLocationSummary = formValues.locations
    .map((location) =>
      location.name.trim()
        ? `${location.name.trim()} (${location.latitude || "?"}, ${location.longitude || "?"})`
        : null,
    )
    .filter(Boolean)
    .join(", ");

  if (isBootstrapping) {
    return (
      <ProtectedRoute>
        <div className="bg-brand-bg flex min-h-dvh flex-col">
          <Navbar showSearch={false} />
          <main className="flex flex-1 items-center justify-center px-4 py-12 sm:px-6 sm:py-16">
            <div className="border-border/80 bg-card/90 shadow-brand-panel w-full max-w-xl rounded-[12px] border p-6 text-center sm:p-10">
              <LoaderCircle className="text-accent mx-auto size-10 animate-spin" />
              <h1 className="mt-5 text-2xl sm:text-3xl">Loading event editor</h1>
              <p className="text-muted-foreground mt-4 text-base leading-7">
                Loading event details, categories, and saved progress.
              </p>
            </div>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

  if (isEditAccessDenied) {
    return (
      <ProtectedRoute>
        <div className="bg-brand-bg flex min-h-dvh flex-col">
          <Navbar showSearch={false} />
          <main className="flex flex-1 items-center justify-center px-4 py-12 sm:px-6 sm:py-16">
            <div className="border-border/80 bg-card/90 shadow-brand-panel w-full max-w-xl rounded-[12px] border p-6 text-center sm:p-10">
              <h1 className="text-2xl sm:text-3xl">Edit access is limited to the host</h1>
              <p className="text-muted-foreground mt-4 text-base leading-7">
                This route is reserved for the event owner. You can still view the event normally, but
                editing needs the original host account.
              </p>
              <div className="mt-6 flex justify-center">
                <Button asChild size="lg">
                  <Link href="/">Back to discovery</Link>
                </Button>
              </div>
            </div>
          </main>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="bg-brand-bg flex min-h-dvh flex-col">
        <Navbar showSearch={false} />
        <main className="flex flex-1 flex-col pb-16">
        <div className="border-brand-mid-alpha bg-brand-surface border-b">
          <div className="mx-auto flex max-w-[1280px] items-center overflow-x-auto px-4 sm:px-6 lg:px-8">
            <Link
              className={cn(
                "border-b-[3px] whitespace-nowrap px-4 py-3 text-xs font-bold tracking-[0.08em] uppercase transition sm:px-5 sm:text-sm",
                mode === "create"
                  ? "border-brand-dark text-foreground"
                  : "text-foreground/60 hover:text-foreground/90 border-transparent",
              )}
              href={CREATE_EVENT_PAGE_PATH}
            >
              Create Event
            </Link>
            <div className="bg-brand-mid-alpha mx-2 h-6 w-px" />
            {editHref ? (
              <Link
                className={cn(
                  "border-b-[3px] whitespace-nowrap px-4 py-3 text-xs font-bold tracking-[0.08em] uppercase transition sm:px-5 sm:text-sm",
                  mode === "edit"
                    ? "border-brand-dark text-foreground"
                    : "text-foreground/60 hover:text-foreground/90 border-transparent",
                )}
                href={editHref}
              >
                Edit &amp; Advanced
              </Link>
            ) : (
              <span className="text-foreground/40 border-b-[3px] border-transparent whitespace-nowrap px-4 py-3 text-xs font-bold tracking-[0.08em] uppercase sm:px-5 sm:text-sm">
                Edit &amp; Advanced
              </span>
            )}
          </div>
        </div>

        <section className="mx-auto w-full max-w-[1280px] px-4 pt-4 sm:px-6 lg:px-8">
          <div>
            <Link
              className="text-brand-mid hover:text-brand-dark inline-flex items-center gap-2 text-sm font-semibold transition"
              href="/"
            >
              <ArrowLeft className="size-4" />
              Back to Discovery
            </Link>
          </div>

          <div className="mt-5 space-y-4">
            {feedback ? <FeedbackBanner feedback={feedback} /> : null}

            {mode === "edit" && eventStatus !== "draft" ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4 text-sm leading-6 text-amber-900">
                Published changes may notify attendees who bookmarked or plan to attend.
              </div>
            ) : null}

            {(currentStep === 1 || currentStep === 2) && startedAtLoad ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-5 py-4 text-sm leading-6 text-amber-900">
                This event has already started, so update the schedule and route carefully.
              </div>
            ) : null}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-8">
            <StepRail
              currentStep={currentStep}
              mobileOpen={mobileStepsOpen}
              onMobileClose={() => setMobileStepsOpen(false)}
              onMobileOpen={() => setMobileStepsOpen(true)}
              onStepSelect={handleStepSelect}
              stepStates={stepStates}
            />

            <div className="max-w-[800px] space-y-6 min-w-0">
              <div className="space-y-2">
                <p className="text-muted-foreground text-xs font-semibold tracking-[0.24em] uppercase">
                  Step {currentStep + 1} of {EVENT_EDITOR_STEPS.length}
                </p>
                <h1 className="text-[1.75rem] leading-tight sm:text-[2rem]">{currentCopy.title}</h1>
                {mode === "edit" ? (
                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <Badge variant={eventStatus === "published" ? "success" : "secondary"}>
                      {eventStatus}
                    </Badge>
                    {persistedEventId ? (
                      <Badge variant="outline">Event ID {persistedEventId.slice(0, 8)}</Badge>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <Card className="border-border/80 bg-card rounded-[12px] shadow-none">
                <CardContent className="space-y-8 px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
                  {currentStep === 0 ? (
                    <div className="space-y-8">
                      <div className="space-y-3">
                        <SectionLabel helper="Keep it short, clear, and easy to scan in discovery cards.">
                          Event title
                        </SectionLabel>
                        <Input
                          maxLength={200}
                          onChange={(event) => patchFormValues({ title: event.target.value })}
                          placeholder="Give your event a memorable name"
                          value={formValues.title}
                        />
                        <div className="flex items-center justify-between gap-3">
                          <FieldError message={fieldErrors.title} />
                          <p className="text-muted-foreground ml-auto text-xs">
                            {formValues.title.length}/200
                          </p>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <SectionLabel helper="A few concrete details go a long way for attendance.">
                          Description
                        </SectionLabel>
                        <Textarea
                          maxLength={2000}
                          onChange={(event) => patchFormValues({ description: event.target.value })}
                          placeholder="Tell people what the event is, who it is for, and what to expect."
                          rows={6}
                          value={formValues.description}
                        />
                        <div className="flex items-center justify-between gap-3">
                          <FieldError message={fieldErrors.description} />
                          <p className="text-muted-foreground ml-auto text-xs">
                            {formValues.description.length}/2000
                          </p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <SectionLabel helper="Choose the categories that best describe the event.">
                          Categories
                        </SectionLabel>
                        <div className="flex flex-wrap gap-3">
                          {categories.map((category) => {
                            const isSelected = formValues.categoryIds.includes(category.id);

                            return (
                              <button
                                className={cn(
                                  "rounded-full border px-4 py-2 text-sm font-semibold transition",
                                  isSelected
                                    ? "border-brand-dark bg-brand-dark text-white"
                                    : "border-border bg-background/80 hover:border-brand-mid hover:bg-background",
                                )}
                                key={category.id}
                                onClick={() =>
                                  patchFormValues({
                                    categoryIds: isSelected
                                      ? formValues.categoryIds.filter((id) => id !== category.id)
                                      : [...formValues.categoryIds, category.id],
                                  })
                                }
                                type="button"
                              >
                                {category.name}
                              </button>
                            );
                          })}
                        </div>
                        <FieldError message={fieldErrors.categoryIds} />
                      </div>
                    </div>
                  ) : null}

                  {currentStep === 1 ? (
                    <div className="space-y-8">
                      {mode === "create" && !hasConfirmedSchedule ? (
                        <div className="border-border/80 bg-brand-surface/40 rounded-lg border px-5 py-4 text-sm leading-6">
                          Suggested times are prefilled for convenience. Review them and press Next
                          to confirm this step.
                        </div>
                      ) : null}

                      <div className="grid gap-6 md:grid-cols-2">
                        <div className="space-y-3">
                          <SectionLabel>Start date</SectionLabel>
                          <Input
                            onChange={(event) => patchFormValues({ startDate: event.target.value })}
                            type="date"
                            value={formValues.startDate}
                          />
                        </div>
                        <div className="space-y-3">
                          <SectionLabel>Start time</SectionLabel>
                          <Input
                            onChange={(event) => patchFormValues({ startTime: event.target.value })}
                            type="time"
                            value={formValues.startTime}
                          />
                        </div>
                      </div>

                      <FieldError message={fieldErrors.startDateTime} />

                      <div className="grid gap-6 md:grid-cols-2">
                        <div className="space-y-3">
                          <SectionLabel>End date</SectionLabel>
                          <Input
                            onChange={(event) => patchFormValues({ endDate: event.target.value })}
                            type="date"
                            min={formValues.startDate || undefined}
                            value={formValues.endDate}
                          />
                        </div>
                        <div className="space-y-3">
                          <SectionLabel>End time</SectionLabel>
                          <Input
                            onChange={(event) => patchFormValues({ endTime: event.target.value })}
                            type="time"
                            min={formValues.endDate === formValues.startDate ? formValues.startTime || undefined : undefined}
                            value={formValues.endTime}
                          />
                        </div>
                      </div>

                      <FieldError message={fieldErrors.endDateTime} />

                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="border-border/80 bg-background/80 rounded-lg border px-5 py-4">
                          <div className="flex items-center gap-3">
                            <CalendarDays className="text-accent size-5" />
                            <p className="text-sm font-semibold">Date range</p>
                          </div>
                          <p className="text-muted-foreground mt-3 text-sm leading-6">
                            {formatEventDateRange(formValues)}
                          </p>
                        </div>

                        <div className="border-border/80 bg-background/80 rounded-lg border px-5 py-4">
                          <div className="flex items-center gap-3">
                            <Clock3 className="text-accent size-5" />
                            <p className="text-sm font-semibold">Duration</p>
                          </div>
                          <p className="text-muted-foreground mt-3 text-sm leading-6">
                            {durationLabel ?? "Set a valid range to see the duration."}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {currentStep === 2 ? (
                    <div className="space-y-6">
                      <div className="border-border/80 bg-background/70 rounded-[12px] border p-5">
                        <div className="flex flex-wrap items-start justify-between gap-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <MapPin className="text-accent size-4" />
                              <p className="text-base font-semibold">Map picker</p>
                            </div>
                            <p className="text-muted-foreground text-sm leading-6">
                              {activeLocation
                                ? `Click anywhere on the map to place ${activeLocation.name.trim() || `Location ${Math.max(activeLocationIndex + 1, 1)}`}.`
                                : "Add a location to start placing pins."}
                            </p>
                          </div>
                          {activeLocation ? (
                            <Badge variant="secondary">
                              Editing{" "}
                              {activeLocation.name.trim() ||
                                `Location ${Math.max(activeLocationIndex + 1, 1)}`}
                            </Badge>
                          ) : null}
                        </div>

                        <EventLocationMap
                          activeLocationId={
                            activeLocation?.id ?? formValues.locations[0]?.id ?? ""
                          }
                          className="mt-5"
                          locations={formValues.locations}
                          onActiveLocationChange={setActiveLocationId}
                          onSelectCoordinates={(locationId, latitude, longitude) => {
                            patchLocation(locationId, {
                              latitude: latitude.toFixed(6),
                              longitude: longitude.toFixed(6),
                            });
                          }}
                        />
                      </div>

                      <div className="space-y-5">
                          <div className="space-y-1">
                            <p className="text-xl font-semibold">Event route</p>
                            <p className="text-muted-foreground text-sm leading-6">
                              Select a stop, rename it if needed, and use the map above to place its pin.
                            </p>
                          </div>

                          <div className="space-y-0">
                            {formValues.locations.map((location, index) => {
                              const locationErrorMessage =
                                fieldErrors[`location-name-${location.id}`] ??
                                fieldErrors[`location-latitude-${location.id}`] ??
                                fieldErrors[`location-longitude-${location.id}`];
                              const hasLocationErrors = Boolean(locationErrorMessage);

                              return (
                                <div key={location.id}>
                                  <div
                                    className={cn(
                                      "bg-background rounded-[12px] border px-4 py-4 transition",
                                      dragLocationId === location.id && "opacity-60",
                                      dragOverLocationId === location.id &&
                                        dragLocationId !== location.id &&
                                        "border-brand-mid ring-2 ring-brand-mid/20",
                                      location.id === activeLocation?.id
                                        ? "border-brand-dark shadow-brand-card"
                                        : hasLocationErrors
                                          ? "border-red-200"
                                          : "border-border/80",
                                    )}
                                    onDragOver={(event) => {
                                      if (!dragLocationId || dragLocationId === location.id) {
                                        return;
                                      }

                                      event.preventDefault();
                                      if (dragOverLocationId !== location.id) {
                                        setDragOverLocationId(location.id);
                                      }
                                    }}
                                    onDrop={(event) => {
                                      event.preventDefault();
                                      if (!dragLocationId) {
                                        return;
                                      }

                                      reorderLocations(dragLocationId, location.id);
                                      setDragLocationId(null);
                                      setDragOverLocationId(null);
                                    }}
                                  >
                                    <div
                                      className="flex items-start gap-3"
                                      onClick={() => {
                                        setActiveLocationId(location.id);
                                      }}
                                  >
                                      <button
                                        aria-label={`Reorder ${location.name.trim() || `Location ${index + 1}`}`}
                                        className="text-brand-dark/35 mt-1.5 flex size-7 shrink-0 cursor-grab items-center justify-center rounded-md transition hover:bg-brand-mid-alpha active:cursor-grabbing"
                                        draggable
                                        onClick={(event) => {
                                          event.stopPropagation();
                                        }}
                                        onDragEnd={() => {
                                          setDragLocationId(null);
                                          setDragOverLocationId(null);
                                        }}
                                        onDragStart={(event) => {
                                          event.stopPropagation();
                                          setDragLocationId(location.id);
                                          setDragOverLocationId(location.id);
                                          event.dataTransfer.effectAllowed = "move";
                                          event.dataTransfer.setData("text/plain", location.id);
                                        }}
                                        type="button"
                                      >
                                        <GripVertical className="size-4 shrink-0" />
                                      </button>
                                      <div className="bg-brand-dark mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white">
                                        {index + 1}
                                      </div>
                                      <div className="min-w-0 flex-1">
                                        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                                          <Input
                                            className="h-9 min-w-0 flex-1"
                                            onChange={(event) =>
                                              patchLocation(location.id, { name: event.target.value })
                                            }
                                            onClick={(event) => {
                                              event.stopPropagation();
                                            }}
                                            onFocus={() => {
                                              setActiveLocationId(location.id);
                                            }}
                                            placeholder={`Location ${index + 1}`}
                                            value={location.name}
                                          />
                                        </div>
                                        <div className="text-muted-foreground mt-1 flex flex-col gap-1 text-xs leading-5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                                          <p className="min-w-0">
                                            {location.id === activeLocation?.id
                                              ? "Click the map above to update this stop."
                                              : "Select this stop to place it on the map."}
                                          </p>
                                          <p className="shrink-0 text-left font-mono sm:text-right">
                                            {location.latitude.trim() && location.longitude.trim()
                                              ? `${location.latitude}, ${location.longitude}`
                                              : "No pin placed yet."}
                                          </p>
                                        </div>
                                        <FieldError message={locationErrorMessage} />
                                      </div>

                                      <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
                                        <Button
                                          className={cn(
                                            "h-9 min-w-[5.75rem]",
                                            location.isPrimary &&
                                              "border-brand-mid bg-brand-mid text-white hover:bg-brand-mid/85 hover:text-white",
                                          )}
                                          onClick={() => {
                                            setActiveLocationId(location.id);
                                            if (!location.isPrimary) {
                                              setPrimaryLocation(location.id);
                                            }
                                          }}
                                          size="sm"
                                          type="button"
                                          variant={location.isPrimary ? "default" : "outline"}
                                        >
                                          Primary
                                        </Button>
                                        {formValues.locations.length > 1 ? (
                                          <Button
                                            className="h-9 w-9 p-0"
                                            onClick={() => removeLocation(location.id)}
                                            size="sm"
                                            type="button"
                                            variant="ghost"
                                          >
                                            <Trash2 />
                                          </Button>
                                        ) : null}
                                      </div>
                                    </div>
                                  </div>

                                  {index < formValues.locations.length - 1 ? (
                                    <div className="border-brand-mid/60 ml-10 h-5 border-l-2 border-dashed" />
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>

                          <FieldError message={fieldErrors.locations} />

                          <Button onClick={addLocation} type="button" variant="outline">
                            <Plus />
                            Add location
                          </Button>

                          <div className="border-border/80 bg-background/60 rounded-lg border px-5 py-4 text-sm leading-6">
                            The primary location is used as the main venue in the event summary.
                          </div>
                      </div>
                    </div>
                  ) : null}

                  {currentStep === 3 ? (
                    <div className="space-y-6">
                      <label
                        className={cn(
                          "border-border/90 bg-background/60 hover:border-brand-mid flex cursor-pointer flex-col items-center justify-center rounded-[12px] border border-dashed px-6 py-12 text-center transition",
                          isUploadingImages && "cursor-wait opacity-70",
                        )}
                      >
                        <input
                          accept="image/jpeg,image/png,image/webp"
                          className="hidden"
                          disabled={isUploadingImages}
                          multiple
                          onChange={(event) => {
                            void handleImageUpload(event);
                          }}
                          type="file"
                        />
                        <div className="bg-background/90 mb-4 rounded-full p-4">
                          {isUploadingImages ? (
                            <LoaderCircle className="text-accent size-8 animate-spin" />
                          ) : (
                            <Upload className="text-accent size-8" />
                          )}
                        </div>
                        <p className="text-lg font-semibold">
                          {isUploadingImages ? "Uploading images..." : "Drag images here or browse"}
                        </p>
                        <p className="text-muted-foreground mt-2 max-w-lg text-sm leading-6">
                          JPEG, PNG, and WebP are supported.
                        </p>
                      </label>

                      <FieldError message={fieldErrors.images} />

                      {images.length > 0 ? (
                        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                          {images.map((image, index) => (
                            <div
                              className="border-border/80 bg-background/70 overflow-hidden rounded-[12px] border"
                              key={image.id}
                            >
                              <div className="bg-brand-surface/45 relative aspect-[4/3]">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  alt={`Uploaded event image ${index + 1}`}
                                  className="size-full object-cover"
                                  src={image.image_url}
                                />
                                <div className="absolute top-3 left-3 flex items-center gap-2">
                                  {index === 0 ? <Badge variant="success">Cover</Badge> : null}
                                </div>
                                <Button
                                  className="absolute top-3 right-3"
                                  disabled={isDeletingImageId === image.id}
                                  onClick={() => {
                                    void handleDeleteImage(image.id);
                                  }}
                                  size="icon-sm"
                                  type="button"
                                  variant="secondary"
                                >
                                  {isDeletingImageId === image.id ? (
                                    <LoaderCircle className="animate-spin" />
                                  ) : (
                                    <Trash2 />
                                  )}
                                </Button>
                              </div>
                              <div className="px-4 py-4">
                                <p className="text-sm font-semibold">Image {index + 1}</p>
                                <p className="text-muted-foreground mt-1 text-sm">
                                  Uploaded {new Date(image.upload_date).toLocaleString()}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="border-border/80 bg-background/60 rounded-[12px] border px-5 py-4 text-sm leading-6">
                          The first uploaded image becomes the cover.
                        </div>
                      )}
                    </div>
                  ) : null}

                  {currentStep === 4 ? (
                    <div className="space-y-8">
                      <div className="space-y-3">
                        <SectionLabel helper="Share any health, safety, or attendee notes people should know in advance.">
                          Special requirements
                        </SectionLabel>
                        <Textarea
                          onChange={(event) =>
                            patchFormValues({ healthRequirements: event.target.value })
                          }
                          placeholder="Mask policy, allergens, dress code, or other important notes."
                          rows={4}
                          value={formValues.healthRequirements}
                        />
                      </div>

                      <div className="space-y-4">
                        <SectionLabel helper="Help attendees understand accessibility and comfort at the venue.">
                          Accessibility
                        </SectionLabel>

                        <div className="grid gap-3 sm:grid-cols-2">
                          {[
                            {
                              checked: formValues.wheelchairAccess,
                              key: "wheelchairAccess",
                              label: "Wheelchair accessible",
                            },
                            {
                              checked: formValues.accessibleRestroom,
                              key: "accessibleRestroom",
                              label: "Accessible restroom",
                            },
                            {
                              checked: formValues.elevatorAvailable,
                              key: "elevatorAvailable",
                              label: "Elevator available",
                            },
                            {
                              checked: formValues.seatingAvailable,
                              key: "seatingAvailable",
                              label: "Seating available",
                            },
                            {
                              checked: formValues.captionsSupport,
                              key: "captionsSupport",
                              label: "Captions or sign support",
                            },
                            {
                              checked: formValues.quietFriendly,
                              key: "quietFriendly",
                              label: "Quiet-friendly environment",
                            },
                          ].map((item) => (
                            <label
                              className="border-border/80 bg-background/70 flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-4"
                              key={item.key}
                            >
                              <Checkbox
                                checked={item.checked}
                                onCheckedChange={(checked) =>
                                  patchFormValues({
                                    [item.key]: toBoolean(checked),
                                  } as Partial<EventFormValues>)
                                }
                              />
                              <span className="text-sm font-medium">{item.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {currentStep === 5 ? (
                    <div className="space-y-6">
                      {mode === "create" && !hasConfirmedSettings ? (
                        <div className="border-border/80 bg-brand-surface/40 rounded-lg border px-5 py-4 text-sm leading-6">
                          Review the visibility and demo capacity settings, then press Next to
                          confirm this step.
                        </div>
                      ) : null}

                      <div className="grid gap-4 md:grid-cols-2">
                        <ToggleCard
                          active={formValues.visibility === "public"}
                          description="Anyone can discover the event and open the full detail page."
                          icon={<Globe className="size-6" />}
                          onClick={() => patchFormValues({ visibility: "public" })}
                          title="Public"
                        />
                        <ToggleCard
                          active={formValues.visibility === "private"}
                          description="It can still appear in discovery, but only approved users can open the full details."
                          icon={<Lock className="size-6" />}
                          onClick={() => patchFormValues({ visibility: "private" })}
                          title="Private"
                        />
                      </div>

                      <div className="border-border/80 bg-background/70 rounded-lg border p-5">
                        <div className="space-y-4">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={formValues.hasAttendeeLimit}
                              onCheckedChange={(checked) =>
                                patchFormValues({ hasAttendeeLimit: toBoolean(checked) })
                              }
                            />
                            <div>
                              <p className="text-base font-semibold">Set attendee limit</p>
                              <p className="text-muted-foreground text-sm leading-6">
                                Enable this for the demo if you want to show limited capacity.
                              </p>
                            </div>
                          </div>

                          {formValues.hasAttendeeLimit ? (
                            <div className="max-w-xs space-y-3">
                              <SectionLabel>Maximum attendees</SectionLabel>
                              <Input
                                min={1}
                                onChange={(event) =>
                                  patchFormValues({ attendeeLimit: event.target.value })
                                }
                                type="number"
                                value={formValues.attendeeLimit}
                              />
                              <FieldError message={fieldErrors.attendeeLimit} />
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div className="border-border/80 bg-background/70 rounded-lg border p-5">
                        <div className="flex items-center gap-3">
                          <Checkbox
                            checked={formValues.isAgeRestricted}
                            onCheckedChange={(checked) =>
                              patchFormValues({ isAgeRestricted: toBoolean(checked) })
                            }
                          />
                          <div>
                            <p className="text-base font-semibold">18+ event</p>
                            <p className="text-muted-foreground text-sm leading-6">
                              Only adults aged 18 and over can view and attend this event.
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="border-border/80 bg-background/70 rounded-lg border p-5">
                        <p className="text-muted-foreground text-sm leading-6">
                          Private events can still appear in discovery previews, but only the host
                          and accepted users can access the full event page.
                        </p>
                      </div>
                    </div>
                  ) : null}

                  {currentStep === 6 ? (
                    <div className="space-y-5">
                      <SummaryCard onEdit={() => setCurrentStep(0)} title="Basics">
                        <p className="text-lg font-semibold">
                          {formValues.title || "Untitled event"}
                        </p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {selectedCategories.length > 0 ? (
                            selectedCategories.map((category) => (
                              <Badge key={category.id} variant="secondary">
                                {category.name}
                              </Badge>
                            ))
                          ) : (
                            <Badge variant="outline">No categories selected</Badge>
                          )}
                        </div>
                        <p className="text-muted-foreground mt-4 text-sm leading-6">
                          {formValues.description || "No description added yet."}
                        </p>
                      </SummaryCard>

                      <SummaryCard onEdit={() => setCurrentStep(1)} title="Schedule">
                        <p className="text-base font-semibold">
                          {formatEventDateRange(formValues)}
                        </p>
                        <p className="text-muted-foreground mt-2 text-sm">
                          Duration: {durationLabel ?? "Not available"}
                        </p>
                      </SummaryCard>

                      <SummaryCard onEdit={() => setCurrentStep(2)} title="Location">
                        <p className="text-base font-semibold">
                          {reviewLocationSummary || "No locations added"}
                        </p>
                      </SummaryCard>

                      <SummaryCard onEdit={() => setCurrentStep(3)} title="Media">
                        <p className="text-base font-semibold">
                          {images.length > 0
                            ? `${images.length} image${images.length === 1 ? "" : "s"} uploaded`
                            : "No images uploaded"}
                        </p>
                        {images.length > 0 ? (
                          <div className="mt-4 grid gap-3 sm:grid-cols-3">
                            {images.slice(0, 3).map((image) => (
                              <div
                                className="border-border/80 bg-background/60 overflow-hidden rounded-lg border"
                                key={image.id}
                              >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  alt="Review event upload"
                                  className="aspect-[4/3] w-full object-cover"
                                  src={image.image_url}
                                />
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </SummaryCard>

                      <SummaryCard onEdit={() => setCurrentStep(4)} title="Venue metadata">
                        <p className="text-base font-semibold">
                          {selectedAccessibilityCount > 0
                            ? `${selectedAccessibilityCount} accessibility feature${selectedAccessibilityCount === 1 ? "" : "s"} selected`
                            : "No accessibility features selected"}
                        </p>
                        <p className="text-muted-foreground mt-2 text-sm leading-6">
                          {formValues.healthRequirements || "No additional venue notes"}
                        </p>
                      </SummaryCard>

                      <SummaryCard onEdit={() => setCurrentStep(5)} title="Settings">
                        <p className="text-base font-semibold">
                          {formValues.visibility === "public" ? "Public" : "Private"} ·{" "}
                          {formValues.hasAttendeeLimit
                            ? `Capacity ${formValues.attendeeLimit || "unset"}`
                            : "Unlimited capacity"}
                        </p>
                      </SummaryCard>
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex w-full sm:w-auto">
                  {currentStep > 0 ? (
                    <Button className="w-full sm:w-auto" onClick={handleBack} size="lg" type="button" variant="outline">
                      <ArrowLeft />
                      Back
                    </Button>
                  ) : null}
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-end">
                  <Button
                    className="rounded-lg px-6 w-full sm:w-auto"
                    onClick={() => {
                      void handleSaveProgress();
                    }}
                    size="lg"
                    type="button"
                    variant="outline"
                  >
                    {isSaving ? (
                      <>
                        <LoaderCircle className="animate-spin" />
                        Saving...
                      </>
                    ) : mode === "create" ? (
                      "Save draft"
                    ) : (
                      "Save changes"
                    )}
                  </Button>

                  {currentStep < EVENT_EDITOR_STEPS.length - 1 ? (
                    <Button className="w-full sm:w-auto" onClick={() => void handleNext()} size="lg" type="button">
                      Next
                      <ArrowRight />
                    </Button>
                  ) : null}

                  {currentStep === EVENT_EDITOR_STEPS.length - 1 && eventStatus === "draft" ? (
                    <Button
                      disabled={isPublishing}
                      onClick={() => {
                        void handlePublish();
                      }}
                      className="w-full sm:w-auto"
                      size="lg"
                      type="button"
                    >
                      {isPublishing ? (
                        <>
                          <LoaderCircle className="animate-spin" />
                          Publishing...
                        </>
                      ) : (
                        <>
                          Publish event
                          <Sparkles />
                        </>
                      )}
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </section>
        </main>
      </div>
    </ProtectedRoute>
  );
}
