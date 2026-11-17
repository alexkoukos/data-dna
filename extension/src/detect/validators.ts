/** Checksum validators. Same maths as services/brain/src/brain/detection/validators.py. */

export function luhnOk(digits: string): boolean {
  if (!/^\d{2,}$/.test(digits)) return false;
  let total = 0;
  [...digits].reverse().forEach((ch, i) => {
    let n = Number(ch);
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    total += n;
  });
  return total % 10 === 0;
}

export function afmOk(afm: string): boolean {
  if (!/^\d{9}$/.test(afm) || afm === "000000000") return false;
  let s = 0;
  for (let i = 0; i < 8; i++) s += Number(afm[i]) * 2 ** (8 - i);
  return (s % 11) % 10 === Number(afm[8]);
}

function isDate(dd: number, mm: number, yy: number): boolean {
  return [1900, 2000].some((century) => {
    const d = new Date(Date.UTC(century + yy, mm - 1, dd));
    return (
      d.getUTCFullYear() === century + yy && d.getUTCMonth() === mm - 1 && d.getUTCDate() === dd
    );
  });
}

export function amkaOk(amka: string): boolean {
  if (!/^\d{11}$/.test(amka)) return false;
  const dd = Number(amka.slice(0, 2));
  const mm = Number(amka.slice(2, 4));
  const yy = Number(amka.slice(4, 6));
  return isDate(dd, mm, yy) && luhnOk(amka);
}

/** ISO 13616: known length for the country and mod-97 equals 1 (done in chunks, no BigInt needed). */
export function ibanOk(raw: string, lengths: Record<string, number>): boolean {
  const iban = raw.replace(/ /g, "").toUpperCase();
  if (iban.length < 15 || !/^[A-Z]{2}\d{2}/.test(iban)) return false;
  const expected = lengths[iban.slice(0, 2)];
  if (expected !== undefined && iban.length !== expected) return false;
  const rearranged = iban.slice(4) + iban.slice(0, 4);
  let remainder = 0;
  for (const ch of rearranged) {
    const n = parseInt(ch, 36);
    for (const digit of String(n)) remainder = (remainder * 10 + Number(digit)) % 97;
  }
  return remainder === 1;
}
