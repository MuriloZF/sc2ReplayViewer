import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FrameSnapshot } from "../types";
import { Minimap } from "./Minimap";

const frame: FrameSnapshot = {
  game_loop: 0,
  game_time_seconds: 0,
  players: [],
};

describe("Minimap", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("draws the replay map image after it loads", async () => {
    const drawImage = vi.fn();
    const gradient = { addColorStop: vi.fn() };
    const context = {
      clearRect: vi.fn(),
      createLinearGradient: vi.fn(() => gradient),
      fillRect: vi.fn(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
      drawImage,
    } as unknown as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context);

    class LoadedImage {
      decoding = "";
      naturalWidth = 256;
      naturalHeight = 256;
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;

      set src(_value: string) {
        queueMicrotask(() => this.onload?.());
      }
    }

    vi.stubGlobal("Image", LoadedImage);

    render(
      <Minimap
        frame={frame}
        samples={[frame]}
        imageUrl="/minimap.png"
        mapBounds={{
          width: 168,
          height: 168,
          playable_left: 12,
          playable_bottom: 17,
          playable_right: 156,
          playable_top: 147,
        }}
      />,
    );

    await waitFor(() => expect(drawImage).toHaveBeenCalledOnce());
    expect(drawImage).toHaveBeenCalledWith(
      expect.any(LoadedImage),
      56,
      65,
      144,
      130,
      0,
      0,
      600,
      600,
    );
  });
});
