import { Suspense } from "react";

import { EventEditor } from "@/components/events/event-editor";

export default function CreateEventPage() {
  return (
    <Suspense>
      <EventEditor mode="create" />
    </Suspense>
  );
}
