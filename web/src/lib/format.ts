const dateTime = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const nf = new Intl.NumberFormat("en-GB");

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));
export const formatNumber = (n: number) => nf.format(n);
export const formatPercent = (share: number | null) =>
  share === null ? "No data yet" : `${Math.round(share * 100)}%`;
