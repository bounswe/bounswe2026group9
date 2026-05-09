"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Download, Loader2, Maximize2, X } from "lucide-react";

import { fetchMyAttendeeQr } from "@/lib/events-api";

interface AttendeeQrModalProps {
  eventId: string;
  eventTitle: string;
  open: boolean;
  onClose: () => void;
}

/**
 * Mirrors mobile's AttendeeQrSheet (PR #302):
 * — fetches the signed token from /attendances/me/{eventId}/qr only when opened
 * — renders the token as a black-on-white QR with M-level error correction
 * — provides a fullscreen view (boosted contrast) and a save-to-device action
 */
export function AttendeeQrModal({ eventId, eventTitle, open, onClose }: AttendeeQrModalProps) {
  // Conditionally mount the body so closing → reopening fetches fresh state.
  if (!open) return null;
  return <AttendeeQrModalBody eventId={eventId} eventTitle={eventTitle} onClose={onClose} />;
}

interface AttendeeQrModalBodyProps {
  eventId: string;
  eventTitle: string;
  onClose: () => void;
}

function AttendeeQrModalBody({ eventId, eventTitle, onClose }: AttendeeQrModalBodyProps) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMyAttendeeQr(eventId)
      .then((res) => {
        if (cancelled) return;
        setToken(res.token);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Could not load QR";
        setError(message);
        setToken(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [eventId]);

  // ESC closes the modal — match the rest of the app's dialog UX.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (fullscreen) setFullscreen(false);
        else onClose();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [fullscreen, onClose]);

  return (
    <div
      aria-labelledby="qr-modal-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
    >
      <div
        className="border-brand-mid-alpha relative w-full max-w-md overflow-hidden rounded-2xl border bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          aria-label="Close"
          className="text-brand-dark/60 hover:text-brand-dark hover:bg-brand-mid-alpha absolute top-3 right-3 z-10 flex size-8 items-center justify-center rounded-full transition-colors"
          onClick={onClose}
          type="button"
        >
          <X className="size-4" />
        </button>

        <div className="flex flex-col items-center px-6 py-7">
          <h2 className="font-heading text-brand-dark text-xl font-semibold" id="qr-modal-title">
            Your check-in QR
          </h2>
          <p className="text-brand-mid mt-1 text-center text-sm">{eventTitle}</p>

          <div className="mt-6 flex aspect-square w-[80%] items-center justify-center rounded-xl bg-white">
            <QrCanvasArea error={error} loading={loading} size={280} token={token} />
          </div>

          <p className="text-brand-mid mt-4 text-center text-xs">
            Show this code to the host at the door.
          </p>

          <div className="mt-5 flex w-full flex-col gap-2">
            {token ? (
              <>
                <button
                  className="bg-brand-dark hover:bg-brand-dark/85 flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-bold text-white transition-colors"
                  onClick={() => setFullscreen(true)}
                  type="button"
                >
                  <Maximize2 className="size-4" />
                  Show fullscreen
                </button>
                <button
                  className="border-brand-dark text-brand-dark hover:bg-brand-mid-alpha flex items-center justify-center gap-2 rounded-lg border-2 py-2.5 text-sm font-bold transition-colors"
                  onClick={() => downloadQr(token, eventTitle)}
                  type="button"
                >
                  <Download className="size-4" />
                  Save image
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {fullscreen && token ? (
        <FullscreenQr onClose={() => setFullscreen(false)} token={token} />
      ) : null}
    </div>
  );
}

interface QrCanvasAreaProps {
  error: string | null;
  loading: boolean;
  size: number;
  token: string | null;
}

function QrCanvasArea({ error, loading, size, token }: QrCanvasAreaProps) {
  if (loading) {
    return <Loader2 className="text-brand-mid size-8 animate-spin" aria-hidden />;
  }
  if (token) {
    return (
      <QRCodeCanvas
        bgColor="#ffffff"
        fgColor="#000000"
        id="attendee-qr-canvas"
        level="M"
        marginSize={2}
        size={size}
        value={token}
      />
    );
  }
  if (error) {
    return (
      <p className="text-brand-dark px-6 text-center text-sm" role="alert">
        {error}
      </p>
    );
  }
  return <p className="text-brand-mid text-sm">No QR available</p>;
}

function FullscreenQr({ onClose, token }: { onClose: () => void; token: string }) {
  // Capture the current scroll position so closing the dialog returns the user
  // to where they were instead of jumping to the top.
  const previousOverflow = useRef<string | null>(null);
  useEffect(() => {
    previousOverflow.current = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow.current ?? "";
    };
  }, []);

  return (
    <div
      aria-label="Check-in QR — fullscreen"
      className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-white"
      onClick={onClose}
      role="dialog"
    >
      <button
        aria-label="Close fullscreen"
        className="text-brand-dark hover:bg-brand-mid-alpha absolute top-4 right-4 flex size-10 items-center justify-center rounded-full transition-colors"
        onClick={(event) => {
          event.stopPropagation();
          onClose();
        }}
        type="button"
      >
        <X className="size-5" />
      </button>
      <QRCodeCanvas
        bgColor="#ffffff"
        fgColor="#000000"
        level="M"
        marginSize={2}
        size={Math.min(
          800,
          typeof window === "undefined" ? 800 : Math.floor(window.innerWidth * 0.85),
        )}
        value={token}
      />
      <p className="text-brand-mid mt-6 text-xs">Tap × to close</p>
    </div>
  );
}

/** Save the rendered QR canvas as a PNG. Uses the canvas DOM element directly so the saved image always matches what the user sees. */
function downloadQr(token: string, eventTitle: string) {
  const canvas = document.getElementById("attendee-qr-canvas") as HTMLCanvasElement | null;
  if (!canvas) return;
  const dataUrl = canvas.toDataURL("image/png");
  const link = document.createElement("a");
  link.href = dataUrl;
  const safeTitle = eventTitle
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase()
    .slice(0, 40);
  link.download = `qr-${safeTitle || "event"}-${token.slice(-6)}.png`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
