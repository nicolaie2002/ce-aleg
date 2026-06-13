"use client";

import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";

export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = "Confirma",
  cancelLabel = "Anuleaza",
  onCancel,
  onConfirm,
}) {
  useEffect(() => {
    if (!isOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === "Escape") onCancel();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 px-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        className="w-full max-w-md rounded-lg border border-white/12 bg-[#111820] p-6 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        aria-describedby="confirm-modal-message"
      >
        <div className="flex items-start justify-between gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-red-400/12 text-red-300">
            <AlertTriangle size={21} />
          </span>
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-gray-300 hover:bg-white/10 hover:text-white"
            aria-label={cancelLabel}
            title={cancelLabel}
          >
            <X size={18} />
          </button>
        </div>

        <h2 id="confirm-modal-title" className="mt-5 text-2xl font-bold text-white">
          {title}
        </h2>
        <p id="confirm-modal-message" className="mt-3 leading-7 text-gray-300">
          {message}
        </p>

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-white/10 px-5 py-3 font-semibold text-white hover:bg-white/10"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg border border-red-400/30 bg-red-400/12 px-5 py-3 font-semibold text-red-200 hover:bg-red-400/20"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
