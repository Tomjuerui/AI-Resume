export function bytesToMB(bytes: number): string {
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

export function formatScore(score: number): string {
  return score.toFixed(0)
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString('zh-CN')
}
