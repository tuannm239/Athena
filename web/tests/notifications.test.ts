import { beforeEach, describe, expect, it } from "vitest";
import { useNotificationStore, type NotificationInput } from "@/stores/notification-store";

const review: NotificationInput = {
  id: "review-pending",
  kind: "review",
  severity: "info",
  title: "Reviews",
  body: "3 pending",
};

describe("notification-store", () => {
  beforeEach(() => useNotificationStore.setState({ items: [], dismissed: [] }));

  it("upserts by key without duplicating and preserves read/at", () => {
    const { upsert } = useNotificationStore.getState();
    upsert(review);
    const first = useNotificationStore.getState().items[0];
    useNotificationStore.getState().markRead("review-pending");
    upsert({ ...review, body: "5 pending" });
    const items = useNotificationStore.getState().items;
    expect(items).toHaveLength(1);
    expect(items[0].body).toBe("5 pending");
    expect(items[0].read).toBe(true); // preserved
    expect(items[0].at).toBe(first.at); // not bumped
  });

  it("reconcile clears items of a kind whose condition no longer holds", () => {
    const { reconcile } = useNotificationStore.getState();
    reconcile("review", [review]);
    expect(useNotificationStore.getState().items).toHaveLength(1);
    reconcile("review", []); // condition resolved
    expect(useNotificationStore.getState().items).toHaveLength(0);
  });

  it("dismiss removes and suppresses re-adding the same key", () => {
    const { upsert, dismiss } = useNotificationStore.getState();
    upsert(review);
    dismiss("review-pending");
    expect(useNotificationStore.getState().items).toHaveLength(0);
    upsert(review); // dismissed keys stay dismissed
    expect(useNotificationStore.getState().items).toHaveLength(0);
  });

  it("counts unread", () => {
    const { upsert } = useNotificationStore.getState();
    upsert(review);
    upsert({ ...review, id: "system-database", kind: "system", severity: "error" });
    expect(useNotificationStore.getState().unreadCount()).toBe(2);
    useNotificationStore.getState().markAllRead();
    expect(useNotificationStore.getState().unreadCount()).toBe(0);
  });
});
