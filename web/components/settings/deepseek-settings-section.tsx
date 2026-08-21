"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Input } from "@/components/ui/input";
import {
  useDeepSeekSettings,
  useUpdateDeepSeekSettings,
} from "@/features/settings/use-deepseek-settings";

export function DeepSeekSettingsSection() {
  const t = useTranslations("settings.deepseek");
  const settingsQuery = useDeepSeekSettings();
  const updateSettings = useUpdateDeepSeekSettings();
  const [apiKey, setApiKey] = useState("");

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
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            {t("sectionTitle")}
          </h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            {t("sectionDescription")}
          </p>
        </div>
        {settingsQuery.data ? (
          <Badge
            variant={
              settingsQuery.data.api_key_configured ? "success" : "warning"
            }
          >
            {settingsQuery.data.api_key_configured
              ? t("configured")
              : t("notConfigured")}
          </Badge>
        ) : null}
      </div>

      {settingsQuery.isPending ? (
        <p
          role="status"
          className="mt-5 text-sm text-[var(--color-text-muted)]"
        >
          {t("checking")}
        </p>
      ) : settingsQuery.isError ? (
        <div className="mt-5">
          <InlineAlert tone="error">{t("unavailableError")}</InlineAlert>
          <Button
            className="mt-3"
            type="button"
            variant="secondary"
            disabled={settingsQuery.isFetching}
            onClick={() => void settingsQuery.refetch()}
          >
            {settingsQuery.isFetching ? t("retrying") : t("retry")}
          </Button>
        </div>
      ) : (
        <>
          <dl className="mt-5 grid gap-4 rounded-[var(--radius-panel)] bg-[var(--color-surface-subtle)] p-4 sm:grid-cols-2">
            <MetadataItem label={t("providerLabel")} value="DeepSeek" />
            <MetadataItem
              label={t("defaultModelLabel")}
              value={settingsQuery.data.default_model}
            />
          </dl>
          <form className="mt-5" onSubmit={(event) => void save(event)}>
            <label
              htmlFor="deepseek-api-key-settings"
              className="block text-sm font-medium text-[var(--color-text)]"
            >
              {t("replaceKeyLabel")}
            </label>
            <Input
              id="deepseek-api-key-settings"
              className="mt-2"
              type="password"
              autoComplete="off"
              maxLength={1000}
              required
              spellCheck={false}
              value={apiKey}
              placeholder={t("replaceKeyPlaceholder")}
              onChange={(event) => {
                setApiKey(event.target.value);
                updateSettings.reset();
              }}
            />
            <p className="mt-2 text-xs leading-5 text-[var(--color-text-muted)]">
              {t("keyNotReturned")}
            </p>
            {updateSettings.isError ? (
              <InlineAlert tone="error" className="mt-3">
                {t("saveError")}
              </InlineAlert>
            ) : null}
            <div className="mt-4 flex items-center gap-4">
              <Button
                type="submit"
                disabled={!apiKey.trim() || updateSettings.isPending}
              >
                {updateSettings.isPending ? t("updating") : t("updateKey")}
              </Button>
              {updateSettings.isSuccess ? (
                <p
                  role="status"
                  className="text-sm text-[var(--color-success)]"
                >
                  {t("updated")}
                </p>
              ) : null}
            </div>
          </form>
        </>
      )}
    </section>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-[var(--color-text-subtle)]">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[var(--color-text)]">
        {value}
      </dd>
    </div>
  );
}
