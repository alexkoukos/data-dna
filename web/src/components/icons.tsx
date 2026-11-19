import { Ban, Check, EyeOff, House, TriangleAlert } from "lucide-react";

/** Outcome icons (lucide). Decorative: always paired with text, so hidden from screen readers. */
export const CheckIcon = () => <Check aria-hidden="true" size={16} />;
export const EyeOffIcon = () => <EyeOff aria-hidden="true" size={16} />;
export const HomeIcon = () => <House aria-hidden="true" size={16} />;
export const AlertIcon = () => <TriangleAlert aria-hidden="true" size={16} />;
export const BanIcon = () => <Ban aria-hidden="true" size={16} />;
