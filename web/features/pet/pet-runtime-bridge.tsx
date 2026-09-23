"use client";

import { useEffect } from "react";

import { useActiveTask } from "@/features/tasks/hooks/use-active-task";
import { useTask } from "@/features/tasks/hooks/use-task";
import { usePetRuntimeStore } from "@/features/pet/pet-runtime-store";
import { usePathname } from "@/i18n/navigation";

export function PetRuntimeBridge() {
  const pathname = usePathname();
  const isResearchPage = pathname.includes("/research/");
  const activeTask = useActiveTask({ enabled: !isResearchPage });
  const syncTaskSnapshot = usePetRuntimeStore(
    (state) => state.syncTaskSnapshot,
  );
  const clearRuntime = usePetRuntimeStore((state) => state.clearRuntime);
  const runtimeTaskId = usePetRuntimeStore((state) => state.taskId);
  const runtimeStatus = usePetRuntimeStore((state) => state.taskStatus);
  const shouldResolveTerminal =
    !isResearchPage &&
    activeTask.isSuccess &&
    !activeTask.data &&
    Boolean(runtimeTaskId) &&
    (runtimeStatus === "queued" ||
      runtimeStatus === "running" ||
      runtimeStatus === "cancelling");
  const terminalTask = useTask(runtimeTaskId ?? "", {
    enabled: shouldResolveTerminal,
  });

  useEffect(() => {
    if (activeTask.data) {
      syncTaskSnapshot(activeTask.data);
      return;
    }
    if (shouldResolveTerminal && terminalTask.data) {
      syncTaskSnapshot(terminalTask.data);
      return;
    }
    if (activeTask.isSuccess && !isResearchPage && !runtimeTaskId) {
      clearRuntime();
    }
  }, [
    activeTask.data,
    activeTask.isSuccess,
    clearRuntime,
    isResearchPage,
    runtimeTaskId,
    shouldResolveTerminal,
    syncTaskSnapshot,
    terminalTask.data,
  ]);

  return null;
}
