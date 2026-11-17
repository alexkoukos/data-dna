// The laptop drawing lives in an 812 x 480 space, but the visible laptop only spans x 31..760.
// The view box starts at ORIGIN_X so the laptop is centred with equal margins on both sides.
export const ORIGIN_X = 10;
export const VIEW_W = 771;
export const VIEW_H = 480;
// The display hole, in drawing coordinates.
export const HOLE = { x: 106, y: 30, w: 579, h: 383 };
