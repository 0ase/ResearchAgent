"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function CancelTaskDialog({
  open,
  onOpenChange,
  onConfirm,
  pending = false,
  onCloseAutoFocus,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void> | void;
  pending?: boolean;
  onCloseAutoFocus?: (event: Event) => void;
}) {
  const t = useTranslations();
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setError(null);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      setError(t("task.cancelError"));
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!pending) onOpenChange(next); }}>
      <DialogContent closeLabel={t("common.close")} onCloseAutoFocus={onCloseAutoFocus}>
        <DialogTitle>{t("task.cancelConfirmTitle")}</DialogTitle>
        <DialogDescription>
          {t("task.cancelConfirmDescription")}
        </DialogDescription>
        {error ? (
          <p role="alert" className="mt-3 text-sm text-[var(--color-error)]">{error}</p>
        ) : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            {t("task.keepRunning")}
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => void confirm()}
            disabled={pending}
          >
            {pending ? t("task.cancelling") : t("common.cancelTask")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
