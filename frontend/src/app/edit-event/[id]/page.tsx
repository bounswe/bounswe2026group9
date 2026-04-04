import { Suspense } from "react";

import { EventEditor } from "@/components/events/event-editor";

export default async function EditEventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <Suspense>
      <EventEditor eventId={id} mode="edit" />
    </Suspense>
  );
}
