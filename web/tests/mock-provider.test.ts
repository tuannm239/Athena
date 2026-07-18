import { describe, expect, it } from "vitest";
import { withMockFallback } from "@/services/mock-provider";
import { ApiRequestError } from "@/lib/api-client";

describe("MockProvider", () => {
  it("returns real data when the endpoint succeeds (mocked:false)", async () => {
    const res = await withMockFallback(async () => ({ v: 1 }), () => ({ v: 99 }));
    expect(res).toEqual({ data: { v: 1 }, mocked: false });
  });

  it("falls back to mock on 501 NotImplemented (mocked:true)", async () => {
    const res = await withMockFallback(
      async () => { throw new ApiRequestError(501, "NotImplemented", "not yet"); },
      () => ({ v: 99 }),
    );
    expect(res).toEqual({ data: { v: 99 }, mocked: true });
  });

  it("re-throws non-501 errors (does not mask real failures)", async () => {
    await expect(
      withMockFallback(
        async () => { throw new ApiRequestError(500, "InternalError", "boom"); },
        () => ({ v: 99 }),
      ),
    ).rejects.toBeInstanceOf(ApiRequestError);
  });
});
