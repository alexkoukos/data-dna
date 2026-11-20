import { describe, expect, it } from "vitest";
import { fitWithin, MAX_IMAGE_SIDE } from "./imageFiles";

describe("image sizing for the model", () => {
  it("shrinks large pictures to the longest side and keeps the shape", () => {
    expect(fitWithin(4096, 3072)).toEqual({ width: MAX_IMAGE_SIDE, height: 1536 });
    expect(fitWithin(1000, 6000)).toEqual({ width: 341, height: MAX_IMAGE_SIDE });
  });

  it("leaves small pictures as they are", () => {
    expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 });
  });
});
