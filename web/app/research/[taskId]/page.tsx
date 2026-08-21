import { ResearchShell } from "@/components/shell/research-shell";
import { LiveTaskView } from "@/components/research/live-task-view";

export default async function ResearchTaskPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;

  return (
    <ResearchShell taskId={taskId}>
      <LiveTaskView taskId={taskId} />
    </ResearchShell>
  );
}
