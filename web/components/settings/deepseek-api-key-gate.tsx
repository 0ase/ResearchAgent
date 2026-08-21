"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Input } from "@/components/ui/input";
import {
  useDeepSeekSettings,
  useUpdateDeepSeekSettings,
} from "@/features/settings/use-deepseek-settings";

const DEEPSEEK_PLATFORM_URL = "https://platform.deepseek.com/";

export function DeepSeekApiKeyGate({ children }: { children: ReactNode }) {
  const t = useTranslations("settings.deepseek");
  const settingsQuery = useDeepSeekSettings();
  const updateSettings = useUpdateDeepSeekSettings();
  const [apiKey, setApiKey] = useState("");

  if (settingsQuery.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-page)] px-6">
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          {t("checking")}
        </p>
      </div>
    );
  }

  if (settingsQuery.isError) {
    return (
      <BlockingDialog>
        <DialogTitle>{t("unavailableTitle")}</DialogTitle>
        <DialogDescription>{t("unavailableDescription")}</DialogDescription>
        <InlineAlert tone="error" className="mt-4">
          {t("unavailableError")}
        </InlineAlert>
        <div className="mt-5 flex justify-end">
          <Button
            type="button"
            disabled={settingsQuery.isFetching}
            onClick={() => void settingsQuery.refetch()}
          >
            {settingsQuery.isFetching ? t("retrying") : t("retry")}
          </Button>
        </div>
      </BlockingDialog>
    );
  }

  if (
    !settingsQuery.data.api_key_required ||
    settingsQuery.data.api_key_configured
  ) {
    return children;
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await updateSettings.mutateAsync({ api_key: apiKey });
      setApiKey("");
    } catch {
      // The mutation state renders a safe, localized error below.
    }
  }

  return (
    <BlockingDialog>
      <DialogTitle>{t("setupTitle")}</DialogTitle>
      <DialogDescription>{t("setupDescription")}</DialogDescription>
      <div className="mt-4 grid gap-3 rounded-[var(--radius-panel)] bg-[var(--color-surface-subtle)] p-3 text-sm sm:grid-cols-2">
        <MetadataItem label={t("providerLabel")} value="DeepSeek" />
        <MetadataItem
          label={t("defaultModelLabel")}
          value={settingsQuery.data.default_model}
        />
      </div>
      <form className="mt-5" onSubmit={(event) => void save(event)}>
        <label
          htmlFor="deepseek-api-key-setup"
          className="block text-sm font-medium text-[var(--color-text)]"
        >
          {t("apiKeyLabel")}
        </label>
        <Input
          id="deepseek-api-key-setup"
          className="mt-2"
          type="password"
          autoComplete="off"
          autoFocus
          maxLength={1000}
          required
          spellCheck={false}
          value={apiKey}
          placeholder={t("setupPlaceholder")}
          onChange={(event) => {
            setApiKey(event.target.value);
            updateSettings.reset();
          }}
        />
        <p className="mt-2 text-xs leading-5 text-[var(--color-text-muted)]">
          {t("deepSeekOnly")}
        </p>
        {updateSettings.isError ? (
          <InlineAlert tone="error" className="mt-3">
            {t("saveError")}
          </InlineAlert>
        ) : null}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button
            type="submit"
            disabled={!apiKey.trim() || updateSettings.isPending}
          >
            {updateSettings.isPending ? t("saving") : t("saveAndContinue")}
          </Button>
          <a
            href={DEEPSEEK_PLATFORM_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-[var(--color-primary)] hover:underline"
          >
            {t("openPlatform")}
          </a>
        </div>
      </form>
    </BlockingDialog>
  );
}

function BlockingDialog({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--color-page)]">
      <Dialog open onOpenChange={() => undefined}>
        <DialogContent
          showCloseButton={false}
          onEscapeKeyDown={(event) => event.preventDefault()}
          onInteractOutside={(event) => event.preventDefault()}
          onPointerDownOutside={(event) => event.preventDefault()}
        >
          {children}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-[var(--color-text-subtle)]">{label}</p>
      <p className="mt-1 font-medium text-[var(--color-text)]">{value}</p>
    </div>
  );
}
