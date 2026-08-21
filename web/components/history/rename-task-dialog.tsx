"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { TaskSnapshotResponse } from "@/lib/api/client";
import { useTranslations } from "next-intl";

export function RenameTaskDialog({
  task,
  open,
  onOpenChange,
  onConfirm,
}: {
  task: TaskSnapshotResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (title: string) => Promise<void> | void;
}) {
  if (!task) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <RenameTaskForm
        key={task.id}
        task={task}
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
      />
    </Dialog>
  );
}

function RenameTaskForm({
  task,
  onOpenChange,
  onConfirm,
}: {
  task: TaskSnapshotResponse;
  onOpenChange: (open: boolean) => void;
  onConfirm: (title: string) => Promise<void> | void;
}) {
  const [title, setTitle] = useState(task.title);
  const t = useTranslations();

  return (
    <DialogContent closeLabel={t("common.close")}>
      <DialogTitle>{t("history.renameTitle")}</DialogTitle>
      <DialogDescription>{t("history.renameDescription")}</DialogDescription>
      <label className="mt-4 block text-sm font-medium">
        {t("history.newTitle")}
        <Input
          aria-label={t("history.newTitle")}
          className="mt-1"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>
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
          disabled={!title.trim()}
          onClick={() =>
            void Promise.resolve(onConfirm(title.trim())).then(() =>
              onOpenChange(false),
            )
          }
        >
          {t("history.saveTitle")}
        </Button>
      </div>
    </DialogContent>
  );
}
