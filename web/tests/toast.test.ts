import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast, useToastStore } from "@/stores/toast-store";
import { confirm, useConfirmStore } from "@/stores/confirm-store";

describe("toast-store", () => {
  beforeEach(() => useToastStore.setState({ toasts: [] }));

  it("pushes and dismisses toasts", () => {
    toast.success("done");
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].kind).toBe("success");
    const id = useToastStore.getState().toasts[0].id;
    useToastStore.getState().dismiss(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("auto-dismisses after the timeout", () => {
    vi.useFakeTimers();
    toast.error("oops");
    expect(useToastStore.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(4100);
    expect(useToastStore.getState().toasts).toHaveLength(0);
    vi.useRealTimers();
  });
});

describe("confirm-store", () => {
  beforeEach(() => useConfirmStore.setState({ pending: null }));

  it("resolves true when settled positively", async () => {
    const p = confirm({ title: "Sure?" });
    expect(useConfirmStore.getState().pending?.title).toBe("Sure?");
    useConfirmStore.getState().settle(true);
    await expect(p).resolves.toBe(true);
    expect(useConfirmStore.getState().pending).toBeNull();
  });

  it("resolves false when cancelled", async () => {
    const p = confirm({ title: "Delete?" });
    useConfirmStore.getState().settle(false);
    await expect(p).resolves.toBe(false);
  });
});
