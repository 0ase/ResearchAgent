"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ReportDocument } from "@/components/report/report-document";
import { useTask } from "@/features/tasks/hooks/use-task";
import { useTaskResult } from "@/features/tasks/hooks/use-task-result";
import { useConversation } from "@/features/followup/conversation";
import { StopResearchButton } from "@/components/research/task-cancellation";

export function TaskConversation({taskId, children}: {taskId: string; children: ReactNode}) {
  const t = useTranslations("followup");
  const task = useTask(taskId);
  const status = task.data?.status;
  const {query, submit, cancel} = useConversation(taskId, status);
  const result = useTaskResult(taskId, status === "completed");
  const [draft, setDraft] = useState("");
  const pendingRequest = useRef<{message_id: string; message: string} | null>(null);
  const scrollRegion = useRef<HTMLDivElement>(null);
  const previousMessageCount = useRef<number | null>(null);
  const messageCount = query.data?.messages.length;
  useEffect(() => {
    if (messageCount !== undefined) {
      if (previousMessageCount.current !== null && messageCount > previousMessageCount.current) {
        scrollRegion.current?.scrollTo({top: scrollRegion.current.scrollHeight, behavior: "instant"});
      }
      previousMessageCount.current = messageCount;
    }
  }, [messageCount]);
  const pending = query.data?.pending;
  const unavailable = !status || ["failed", "cancelled", "interrupted", "cancelling"].includes(status);
  const busy = pending?.status === "processing" || submit.isPending || cancel.isPending;
  const value = unavailable ? "" : draft;
  const send = async (message: string) => {
    const normalized = message.trim();
    if (pendingRequest.current?.message !== normalized) {
      pendingRequest.current = {message_id: crypto.randomUUID(), message: normalized};
    }
    try {
      await submit.mutateAsync(pendingRequest.current);
      pendingRequest.current = null;
      setDraft("");
    } catch { /* The mutation owns the visible error; preserve the typed question. */ }
  };
  return <>
    <div ref={scrollRegion} className="min-h-0 flex-1 overflow-y-auto" data-testid="task-scroll-region">
      {children}
      <section aria-label={t("history")} className="mx-auto max-w-[840px] space-y-6 px-8 pb-8">
        {query.data?.messages.map((message) => <article key={`${message.message_id}:${message.role}`} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <p className="mb-3 text-xs text-[var(--color-text-muted)]">{t(message.role)}</p>
          {message.role === "assistant" ? <ReportDocument markdown={message.content} result={result.data} variant="message" /> : <p className="whitespace-pre-wrap break-words">{message.content}</p>}
        </article>)}
      </section>
    </div>
    <section aria-label={t("composer")} data-testid="followup-composer" className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-chrome)] px-6 py-4">
      <div className="mx-auto max-w-[780px]">
        {pending && !unavailable ? <div className="mb-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3">
          <p role="status" className="text-xs text-[var(--color-text-muted)]">{t(pending.status)}</p>
          <p className="my-2 max-h-20 overflow-y-auto whitespace-pre-wrap break-words text-sm">{pending.content}</p>
          {pending.status !== "processing" ? <div className="flex gap-2">
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => setDraft(pending.content)}>{t("edit")}</Button>
            {pending.status === "failed" ? <Button size="sm" disabled={busy} onClick={() => void send(pending.content)}>{t("retry")}</Button> : null}
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => cancel.mutate()}>{t("cancel")}</Button>
          </div> : null}
        </div> : null}
        <form onSubmit={(event) => {event.preventDefault(); if (value.trim() && !busy && !unavailable) void send(value);}}>
          <label htmlFor={`followup-${taskId}`} className="sr-only">{t("composer")}</label>
          <textarea id={`followup-${taskId}`} rows={2} maxLength={4000} value={value} disabled={unavailable || busy} onChange={(event) => setDraft(event.target.value)} placeholder={t(unavailable ? "unavailable" : "placeholder")} className="w-full resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-sm text-[var(--color-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus)] disabled:opacity-60" />
          <div className="mt-2 flex items-center justify-between gap-4">
            <p className="text-xs text-[var(--color-text-muted)]">{t(unavailable ? "unavailable" : status === "completed" ? "contextOnly" : "queueHint")}</p>
            <div className="flex shrink-0 items-center gap-2">
              <StopResearchButton prominent />
              <Button type="submit" size="sm" disabled={!value.trim() || busy || unavailable}>{t(pending?.status === "queued" ? "replace" : "send")}</Button>
            </div>
          </div>
        </form>
        {query.isError || submit.isError || cancel.isError ? <p role="alert" className="mt-2 text-sm text-[var(--color-error)]">{t("error")} <button className="underline" onClick={() => void query.refetch()}>{t("refresh")}</button></p> : null}
      </div>
    </section>
  </>;
}
