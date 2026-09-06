export function applyRatio(ratio: number, total: number, minRatio: number): number {
  const value = ratio * total
  return Math.min(total * (1 - minRatio), Math.max(total * minRatio, value))
}
