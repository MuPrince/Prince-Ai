export function parseSseBlock(raw: string): {
  type: string
  content?: string
  name?: string
} | null {
  const lines = raw.split('\n')
  const dataLine = lines.find((line) => line.startsWith('data:'))
  if (!dataLine) return null
  try {
    return JSON.parse(dataLine.slice(5).trim())
  } catch {
    return null
  }
}
