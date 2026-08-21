import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";

function settingsResponse(apiKeyConfigured: boolean, apiKeyRequired = true) {
  return new Response(
    JSON.stringify({
      provider: "deepseek",
      default_model: "deepseek-v4-flash",
      api_key_required: apiKeyRequired,
      api_key_configured: apiKeyConfigured,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

function renderGate() {
  render(
    <Providers locale="en" enforceDeepSeekSetup>
      <main>Research workspace ready</main>
    </Providers>,
  );
}

function isSettingsRequest(input: RequestInfo | URL) {
  return String(input).endsWith("/api/v1/settings/deepseek");
}

describe("DeepSeekApiKeyGate", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("blocks first use until a DeepSeek key is saved", async () => {
    let configured = false;
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input, init) => {
        if (!isSettingsRequest(input))
          return new Response(null, { status: 204 });
        if (init?.method === "PUT") {
          configured = true;
          return settingsResponse(true);
        }
        return settingsResponse(configured);
      });

    renderGate();

    expect(
      await screen.findByRole("heading", {
        name: "Configure a DeepSeek API key",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Research workspace ready"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Close dialog" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open the DeepSeek API platform" }),
    ).toHaveAttribute("href", "https://platform.deepseek.com/");

    const user = userEvent.setup();
    await user.keyboard("{Escape}");
    expect(
      screen.getByRole("heading", { name: "Configure a DeepSeek API key" }),
    ).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("DeepSeek API key"),
      "sk-local-deepseek",
    );
    await user.click(screen.getByRole("button", { name: "Save and continue" }));

    await waitFor(() =>
      expect(screen.getByText("Research workspace ready")).toBeInTheDocument(),
    );
    const updateCall = fetchMock.mock.calls.find(
      ([, init]) => init?.method === "PUT",
    );
    expect(updateCall).toBeDefined();
    expect(JSON.parse(String(updateCall?.[1]?.body))).toEqual({
      api_key: "sk-local-deepseek",
    });
  });

  it("enters immediately when configured or when the demo runner needs no key", async () => {
    let configured = true;
    let required = true;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) =>
      isSettingsRequest(input)
        ? settingsResponse(configured, required)
        : new Response(null, { status: 204 }),
    );
    renderGate();
    expect(
      await screen.findByText("Research workspace ready"),
    ).toBeInTheDocument();

    configured = false;
    required = false;
    renderGate();
    await waitFor(() =>
      expect(screen.getAllByText("Research workspace ready")).toHaveLength(2),
    );
  });

  it("keeps the app blocked and retries when the backend is unavailable", async () => {
    let settingsAttempts = 0;
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        if (!isSettingsRequest(input))
          return new Response(null, { status: 204 });
        settingsAttempts += 1;
        if (settingsAttempts === 1) throw new Error("offline");
        return settingsResponse(true);
      });

    renderGate();
    expect(
      await screen.findByRole("heading", {
        name: "Model configuration unavailable",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Research workspace ready"),
    ).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(screen.getByText("Research workspace ready")).toBeInTheDocument(),
    );
    expect(settingsAttempts).toBe(2);
    expect(fetchMock).toHaveBeenCalled();
  });
});
