import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import { DeepSeekSettingsSection } from "@/components/settings/deepseek-settings-section";

function configuredResponse() {
  return new Response(
    JSON.stringify({
      provider: "deepseek",
      default_model: "deepseek-v4-flash",
      api_key_required: true,
      api_key_configured: true,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

function renderSection() {
  render(
    <Providers locale="en">
      <DeepSeekSettingsSection />
    </Providers>,
  );
}

function isSettingsRequest(input: RequestInfo | URL) {
  return String(input).endsWith("/api/v1/settings/deepseek");
}

describe("DeepSeekSettingsSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows only configuration status and replaces the key independently", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) =>
        isSettingsRequest(input)
          ? configuredResponse()
          : new Response(null, { status: 204 }),
      );
    renderSection();

    expect(await screen.findByText("Configured")).toBeInTheDocument();
    expect(screen.getByText("deepseek-v4-flash")).toBeInTheDocument();
    const input = screen.getByLabelText("Replace API key");
    expect(input).toHaveValue("");

    const user = userEvent.setup();
    await user.type(input, "sk-replacement");
    await user.click(screen.getByRole("button", { name: "Update API key" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "API key updated",
    );
    expect(input).toHaveValue("");
    const updateCall = fetchMock.mock.calls.find(
      ([, init]) => init?.method === "PUT",
    );
    expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual({
      api_key: "sk-replacement",
    });
  });

  it("keeps the replacement field available after a save failure", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (!isSettingsRequest(input)) return new Response(null, { status: 204 });
      if (init?.method === "PUT") {
        return new Response(
          JSON.stringify({
            error: {
              code: "DEEPSEEK_SETTINGS_WRITE_FAILED",
              message: "Unable to save",
              retryable: true,
              request_id: "request-1",
            },
          }),
          { status: 500, headers: { "Content-Type": "application/json" } },
        );
      }
      return configuredResponse();
    });
    renderSection();
    await screen.findByText("Configured");

    const user = userEvent.setup();
    const input = screen.getByLabelText("Replace API key");
    await user.type(input, "sk-still-visible");
    await user.click(screen.getByRole("button", { name: "Update API key" }));

    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();
    await waitFor(() => expect(input).toHaveValue("sk-still-visible"));
  });
});
