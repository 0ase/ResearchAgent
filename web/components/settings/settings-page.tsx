"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useForm, useWatch, type UseFormRegisterReturn } from "react-hook-form";
import { z } from "zod";

import { ResearchShell } from "@/components/shell/research-shell";
import { DeepSeekSettingsSection } from "@/components/settings/deepseek-settings-section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ACADEMIC_SOURCES,
  DEFAULT_APP_PREFERENCES,
  usePreferencesStore,
} from "@/features/preferences/preferences-store";
import { Link } from "@/i18n/navigation";

const settingsSchema = z.object({
  maxPapers: z.number().int().min(1).max(50),
  sources: z.array(z.enum(ACADEMIC_SOURCES)).min(1),
  visible: z.boolean(),
  size: z.enum(["small", "medium", "large"]),
  motion: z.enum(["system", "full", "reduced", "static"]),
  dragLocked: z.boolean(),
});

type SettingsValues = z.infer<typeof settingsSchema>;

function valuesFromStore(
  research: (typeof DEFAULT_APP_PREFERENCES)["research"],
  pet: (typeof DEFAULT_APP_PREFERENCES)["pet"],
): SettingsValues {
  return {
    maxPapers: research.maxPapers,
    sources: research.sources,
    visible: pet.visible,
    size: pet.size,
    motion: pet.motion,
    dragLocked: pet.dragLocked,
  };
}

export function SettingsPage() {
  const t = useTranslations("settings");
  const research = usePreferencesStore((state) => state.research);
  const pet = usePreferencesStore((state) => state.pet);
  const hasHydrated = usePreferencesStore((state) => state.hasHydrated);
  const setResearchPreferences = usePreferencesStore(
    (state) => state.setResearchPreferences,
  );
  const setPetPreferences = usePreferencesStore(
    (state) => state.setPetPreferences,
  );
  const resetPetPosition = usePreferencesStore(
    (state) => state.resetPetPosition,
  );
  const resetPreferences = usePreferencesStore(
    (state) => state.resetPreferences,
  );
  const [saved, setSaved] = useState(false);
  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: valuesFromStore(research, pet),
  });

  useEffect(() => {
    if (hasHydrated && !form.formState.isDirty) {
      form.reset(valuesFromStore(research, pet));
    }
  }, [form, form.formState.isDirty, hasHydrated, pet, research]);

  const values = useWatch({ control: form.control });

  function save(next: SettingsValues) {
    setResearchPreferences({
      maxPapers: next.maxPapers,
      sources: next.sources,
    });
    setPetPreferences({
      visible: next.visible,
      size: next.size,
      motion: next.motion,
      dragLocked: next.dragLocked,
    });
    form.reset(next);
    setSaved(true);
  }

  function restoreDefaults() {
    resetPreferences();
    const defaults = valuesFromStore(
      DEFAULT_APP_PREFERENCES.research,
      DEFAULT_APP_PREFERENCES.pet,
    );
    form.reset(defaults);
    setSaved(true);
  }

  return (
    <ResearchShell>
      <div className="mx-auto w-full max-w-3xl px-8 py-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-primary)]"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          {t("back")}
        </Link>
        <div className="mt-5">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-text)]">
            {t("title")}
          </h1>
          <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
            {t("description")}
          </p>
        </div>

        <div className="mt-8">
          <DeepSeekSettingsSection />
        </div>

        <form
          className="mt-6 space-y-6"
          onSubmit={(event) => void form.handleSubmit(save)(event)}
        >
          <SettingsSection
            title={t("research.title")}
            description={t("research.description")}
          >
            <label className="block text-sm font-medium text-[var(--color-text)]">
              {t("research.maxPapers")}
              <Input
                className="mt-2 max-w-48"
                type="number"
                min={1}
                max={50}
                aria-invalid={Boolean(form.formState.errors.maxPapers)}
                {...form.register("maxPapers", { valueAsNumber: true })}
              />
            </label>
            {form.formState.errors.maxPapers ? (
              <p className="mt-2 text-xs text-[var(--color-error)]">
                {t("research.maxPapersError")}
              </p>
            ) : null}
            <fieldset className="mt-5">
              <legend className="text-sm font-medium text-[var(--color-text)]">
                {t("research.sources")}
              </legend>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {ACADEMIC_SOURCES.map((source) => (
                  <label
                    key={source}
                    className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]"
                  >
                    <input
                      type="checkbox"
                      value={source}
                      {...form.register("sources")}
                    />
                    {t(`research.source.${source}`)}
                  </label>
                ))}
              </div>
              {form.formState.errors.sources ? (
                <p className="mt-2 text-xs text-[var(--color-error)]">
                  {t("research.sourcesError")}
                </p>
              ) : null}
            </fieldset>
          </SettingsSection>

          <SettingsSection
            title={t("pet.title")}
            description={t("pet.description")}
          >
            <ToggleField
              label={t("pet.visible")}
              registration={form.register("visible")}
            />
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <SelectField
                label={t("pet.size")}
                registration={form.register("size")}
              >
                <option value="small">{t("pet.sizes.small")}</option>
                <option value="medium">{t("pet.sizes.medium")}</option>
                <option value="large">{t("pet.sizes.large")}</option>
              </SelectField>
              <SelectField
                label={t("pet.motion")}
                registration={form.register("motion")}
              >
                <option value="system">{t("pet.motions.system")}</option>
                <option value="full">{t("pet.motions.full")}</option>
                <option value="reduced">{t("pet.motions.reduced")}</option>
                <option value="static">{t("pet.motions.static")}</option>
              </SelectField>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-4">
              <ToggleField
                label={t("pet.dragLocked")}
                registration={form.register("dragLocked")}
              />
              <Button
                type="button"
                variant="secondary"
                onClick={resetPetPosition}
              >
                <RotateCcw aria-hidden="true" className="h-4 w-4" />
                {t("pet.resetPosition")}
              </Button>
            </div>
            <p className="mt-5 rounded-[var(--radius-panel)] bg-[var(--color-surface-subtle)] p-3 text-xs leading-5 text-[var(--color-text-muted)]">
              {t("pet.preview", {
                visibility: t(
                  (values.visible ?? pet.visible) ? "pet.shown" : "pet.hidden",
                ),
                size: t(`pet.sizes.${values.size ?? pet.size}`),
                motion: t(`pet.motions.${values.motion ?? pet.motion}`),
              })}
            </p>
          </SettingsSection>

          <div className="flex items-center justify-between gap-4">
            <div className="flex gap-3">
              <Button type="submit">{t("save")}</Button>
              <Button
                type="button"
                variant="secondary"
                onClick={restoreDefaults}
              >
                {t("restoreDefaults")}
              </Button>
            </div>
            {saved ? (
              <p role="status" className="text-sm text-[var(--color-success)]">
                {t("saved")}
              </p>
            ) : null}
          </div>
        </form>
      </div>
    </ResearchShell>
  );
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <h2 className="text-lg font-semibold text-[var(--color-text)]">
        {title}
      </h2>
      <p className="mt-1 text-sm text-[var(--color-text-muted)]">
        {description}
      </p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function ToggleField({
  label,
  registration,
}: {
  label: string;
  registration: UseFormRegisterReturn;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-[var(--color-text)]">
      <input type="checkbox" {...registration} />
      {label}
    </label>
  );
}

function SelectField({
  label,
  registration,
  children,
}: {
  label: string;
  registration: UseFormRegisterReturn;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm font-medium text-[var(--color-text)]">
      {label}
      <select
        className="mt-2 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
        {...registration}
      >
        {children}
      </select>
    </label>
  );
}
