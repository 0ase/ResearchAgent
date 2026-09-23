"use client";

import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import { Square } from "lucide-react";
import { useTranslations } from "next-intl";

import { CancelTaskDialog } from "@/components/research/cancel-task-dialog";
import { Button } from "@/components/ui/button";
import { useCancelTask } from "@/features/tasks/hooks/use-cancel-task";
import { useTask } from "@/features/tasks/hooks/use-task";

const CancellationContext = createContext<{
  visible: boolean;
  pending: boolean;
  open: (trigger: HTMLButtonElement) => void;
} | null>(null);

export function TaskCancellationProvider({ taskId, children }: { taskId: string; children: ReactNode }) {
  const { data: task } = useTask(taskId);
  const cancellation = useCancelTask(taskId);
  const [open, setOpen] = useState(false);
  const submitting = useRef(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const active = task?.status === "queued" || task?.status === "running";
  const stopping = task?.status === "cancelling";
  const pending = cancellation.isPending || stopping;
  const canCancel = active && Boolean(task?.available_actions?.includes("cancel"));

  return (
    <CancellationContext.Provider value={{ visible: canCancel || stopping, pending, open: (trigger) => { triggerRef.current = trigger; setOpen(true); } }}>
      {children}
      <CancelTaskDialog
        key={String(open)}
        open={open && (canCancel || stopping)}
        onOpenChange={setOpen}
        pending={pending}
        onCloseAutoFocus={(event) => {
          if (triggerRef.current?.isConnected && !triggerRef.current.disabled) {
            event.preventDefault();
            triggerRef.current.focus();
          }
        }}
        onConfirm={async () => {
          if (submitting.current || pending || !canCancel) return;
          submitting.current = true;
          try {
            await cancellation.mutateAsync();
          } finally {
            submitting.current = false;
          }
        }}
      />
    </CancellationContext.Provider>
  );
}

export function StopResearchButton({ prominent = false }: { prominent?: boolean }) {
  const cancellation = useContext(CancellationContext);
  const t = useTranslations();
  if (!cancellation?.visible) return null;

  return (
    <Button
      type="button"
      variant={prominent ? "destructive" : "ghost"}
      onClick={(event) => cancellation.open(event.currentTarget)}
      disabled={cancellation.pending}
      aria-busy={cancellation.pending}
    >
      <Square aria-hidden="true" className="h-3.5 w-3.5" />
      {t(cancellation.pending ? "task.cancelling" : "common.cancelTask")}
    </Button>
  );
}
