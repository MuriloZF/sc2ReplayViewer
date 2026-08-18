import { describe, expect, it, vi } from "vitest";

import { ApiError, listReplays } from "./api";

describe("API client", () => {
  it("returns replay summaries", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [{ replay_id: "one" }] }) }),
    );

    await expect(listReplays()).resolves.toEqual([{ replay_id: "one" }]);
  });

  it("uses the API error detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Invalid replay" }),
      }),
    );

    await expect(listReplays()).rejects.toEqual(new ApiError("Invalid replay", 400));
  });
});
