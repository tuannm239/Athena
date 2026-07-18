import { afterEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { PwaRegister } from "@/components/pwa-register";

describe("PwaRegister", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders nothing and does not throw without serviceWorker support", () => {
    const { container } = render(<PwaRegister />);
    expect(container.firstChild).toBeNull();
  });

  it("registers the service worker on load in production", () => {
    const register = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { serviceWorker: { register } });
    vi.stubEnv("NODE_ENV", "production");
    const listeners: Record<string, () => void> = {};
    vi.stubGlobal("window", {
      addEventListener: (e: string, cb: () => void) => { listeners[e] = cb; },
      removeEventListener: () => {},
    });
    render(<PwaRegister />);
    listeners["load"]?.();
    expect(register).toHaveBeenCalledWith("/sw.js");
  });
});
