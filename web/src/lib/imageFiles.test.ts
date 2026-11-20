import { describe, expect, it } from "vitest";
import { dataUrlToFile, fitWithin, MAX_IMAGE_SIDE } from "./imageFiles";

describe("image sizing for the model", () => {
  it("shrinks large pictures to the longest side and keeps the shape", () => {
    expect(fitWithin(4096, 3072)).toEqual({ width: MAX_IMAGE_SIDE, height: 1536 });
    expect(fitWithin(1000, 6000)).toEqual({ width: 341, height: MAX_IMAGE_SIDE });
  });

  it("leaves small pictures as they are", () => {
    expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 });
  });
});

describe("redrawn picture as a file", () => {
  it("keeps the name, says JPEG and holds the bytes", async () => {
    const file = dataUrlToFile("data:image/jpeg;base64,/9j/AA==", "chart.png");
    expect(file.name).toBe("chart.jpg");
    expect(file.type).toBe("image/jpeg");
    expect(new Uint8Array(await file.arrayBuffer())).toEqual(new Uint8Array([0xff, 0xd8, 0xff, 0]));
  });
});
