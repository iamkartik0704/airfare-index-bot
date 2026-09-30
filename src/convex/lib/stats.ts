/**
 * Small, dependency-free statistics used by the SAFAR index, the driver
 * regression and the back-test validator. Everything is plain arithmetic so
 * the same numbers can be reproduced in the Python reference implementation
 * that ships in `scraper/`.
 */

export function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  let s = 0;
  for (const x of xs) s += x;
  return s / xs.length;
}

export function median(xs: number[]): number {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Median absolute deviation, scaled to be a consistent estimator of σ. */
export function mad(xs: number[]): number {
  if (xs.length === 0) return 0;
  const m = median(xs);
  return 1.4826 * median(xs.map((x) => Math.abs(x - m)));
}

export function weightedMean(xs: number[], ws: number[]): number {
  let num = 0;
  let den = 0;
  for (let i = 0; i < xs.length; i++) {
    num += xs[i] * ws[i];
    den += ws[i];
  }
  return den === 0 ? 0 : num / den;
}

export function weightedGeometricMean(xs: number[], ws: number[]): number {
  let logSum = 0;
  let wSum = 0;
  for (let i = 0; i < xs.length; i++) {
    if (xs[i] <= 0) continue;
    logSum += ws[i] * Math.log(xs[i]);
    wSum += ws[i];
  }
  return wSum === 0 ? 0 : Math.exp(logSum / wSum);
}

export function stdev(xs: number[]): number {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  let s = 0;
  for (const x of xs) s += (x - m) * (x - m);
  return Math.sqrt(s / (xs.length - 1));
}

export function pearson(xs: number[], ys: number[]): number {
  const n = Math.min(xs.length, ys.length);
  if (n < 3) return 0;
  const mx = mean(xs.slice(0, n));
  const my = mean(ys.slice(0, n));
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx;
    const dy = ys[i] - my;
    sxy += dx * dy;
    sxx += dx * dx;
    syy += dy * dy;
  }
  if (sxx === 0 || syy === 0) return 0;
  return sxy / Math.sqrt(sxx * syy);
}

/** Rank correlation — robust against the outliers real fare data always has. */
export function spearman(xs: number[], ys: number[]): number {
  return pearson(rank(xs), rank(ys));
}

export function rank(xs: number[]): number[] {
  const idx = xs.map((v, i) => [v, i] as [number, number]).sort((a, b) => a[0] - b[0]);
  const out = new Array<number>(xs.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
    const avg = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) out[idx[k][1]] = avg;
    i = j + 1;
  }
  return out;
}

export function ols(y: number[], xs: number[][]): { beta: number[]; r2: number; t: number[] } {
  const n = y.length;
  const k = xs[0]?.length ?? 0;
  if (n <= k) return { beta: new Array(k).fill(0), r2: 0, t: new Array(k).fill(0) };

  // Normal equations with Tikhonov ridge (lambda = 1e-8) so collinear
  // seasonal dummies never blow up the solve.
  const lambda = 1e-8;
  const XtX: number[][] = Array.from({ length: k }, () => new Array(k).fill(0));
  const Xty: number[] = new Array(k).fill(0);
  for (let i = 0; i < n; i++) {
    for (let a = 0; a < k; a++) {
      Xty[a] += xs[i][a] * y[i];
      for (let b = 0; b < k; b++) XtX[a][b] += xs[i][a] * xs[i][b];
    }
  }
  for (let a = 0; a < k; a++) XtX[a][a] += lambda;

  const inv = invert(XtX);
  const beta = new Array(k).fill(0);
  if (!inv) return { beta, r2: 0, t: new Array(k).fill(0) };
  for (let a = 0; a < k; a++) for (let b = 0; b < k; b++) beta[a] += inv[a][b] * Xty[b];

  // R²
  const ybar = mean(y);
  let ssTot = 0;
  let ssRes = 0;
  for (let i = 0; i < n; i++) {
    let fit = 0;
    for (let a = 0; a < k; a++) fit += beta[a] * xs[i][a];
    ssRes += (y[i] - fit) ** 2;
    ssTot += (y[i] - ybar) ** 2;
  }
  const r2 = ssTot === 0 ? 0 : 1 - ssRes / ssTot;

  // t-stats via residual variance and the diagonal of (XᵀX)⁻¹
  const dof = Math.max(1, n - k);
  const s2 = ssRes / dof;
  const t = beta.map((b, a) => (inv && s2 > 0 ? b / Math.sqrt(s2 * inv[a][a]) : 0));

  return { beta, r2, t };
}

function invert(m: number[][]): number[][] | null {
  const n = m.length;
  const a: number[][] = m.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(a[r][col]) > Math.abs(a[pivot][col])) pivot = r;
    if (Math.abs(a[pivot][col]) < 1e-12) return null;
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const p = a[col][col];
    for (let j = 0; j < 2 * n; j++) a[col][j] /= p;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = a[r][col];
      if (f === 0) continue;
      for (let j = 0; j < 2 * n; j++) a[r][j] -= f * a[col][j];
    }
  }
  return a.map((row) => row.slice(n));
}

export function quantile(xs: number[], q: number): number {
  if (xs.length === 0) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const pos = (s.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return s[lo];
  return s[lo] + (s[hi] - s[lo]) * (pos - lo);
}

export function clamp(x: number, lo: number, hi: number): number {
  return x < lo ? lo : x > hi ? hi : x;
}

export function pctChange(a: number, b: number): number {
  if (a === 0) return 0;
  return ((b - a) / a) * 100;
}

export function round(x: number, dp = 2): number {
  const f = 10 ** dp;
  return Math.round(x * f) / f;
}
