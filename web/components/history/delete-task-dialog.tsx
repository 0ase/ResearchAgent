"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import type { TaskSnapshotResponse } from "@/lib/api/client";
import { useTranslations } from "next-intl";

export function DeleteTaskDialog({
  task,
  open,
  onOpenChange,
  onConfirm,
}: {
  task: TaskSnapshotResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void> | void;
}) {
  const t = useTranslations();
  if (!task) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent closeLabel={t("common.close")}>
        <DialogTitle>{t("history.deleteTitle")}</DialogTitle>
        <DialogDescription>
          {t("history.deleteDescription", { title: task.title })}
        </DialogDescription>
        <div className="mt-5 flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => onOpenChange(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() =>
              void Promise.resolve(onConfirm()).then(() => onOpenChange(false))
            }
          >
            {t("common.delete")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
