import { useState, useCallback } from 'react'

// Key mapping from short keys to display names
const KEY_LABELS: Record<string, string> = {
  P: 'Pass',
  F: 'Fail',
  Sa: 'Safety',
  Li: 'Lighting',
  St: 'Steering',
  Br: 'Braking',
  Wh: 'Wheels',
  En: 'Engine',
  Ch: 'Chassis',
  Ss: 'SideSlip',
  Su: 'Suspension',
  Lt: 'Light',
  Bk: 'Brake',
  Em: 'Emissions',
  Ot: 'Other',
  In: 'Incomplete',
}

export { KEY_LABELS }

/**
 * Decoded percentage fields — each value is 0–100 (0.5% precision).
 * These map to the byte-index order in the base64 payload.
 */
const PCT_KEYS = [
  'P', 'F', 'Sa', 'Li', 'St', 'Br', 'Wh', 'En',
  'Ch', 'Ss', 'Su', 'Lt', 'Bk', 'Em', 'Ot', 'In',
] as const

export type PctKey = (typeof PCT_KEYS)[number]

export interface NctResult {
  pk: string
  sk: string
  make: string
  model: string
  test_year: number
  car_year: number
  /** Percentage values (0–100, 0.5 step) */
  P: number
  F: number
  Sa: number
  Li: number
  St: number
  Br: number
  Wh: number
  En: number
  Ch: number
  Ss: number
  Su: number
  Lt: number
  Bk: number
  Em: number
  Ot: number
  In: number
}

/** Raw shape returned by the API (new compact format) */
interface CompactItem {
  pk: string
  sk: string
  d: string[]
}

interface QueryResponse {
  count: number
  items: CompactItem[]
}

// ── Base64 decoding ──────────────────────────────────────────────────────────

/** Decode a standard base64 string to a Uint8Array. */
function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes
}

/**
 * Expand a compact DynamoDB item into one NctResult per car-year entry.
 *
 * Each entry in `d` is: "<4-char car year><base64(16 bytes)>"
 * Each byte is a percentage × 2 (0–200 → 0.0–100.0 in 0.5 steps).
 */
function expandItem(item: CompactItem): NctResult[] {
  const pk = item.pk
  // pk = "MODEL#MAKE#MODEL"
  const pkParts = pk.split('#')
  const make = pkParts[1] ?? ''
  const model = pkParts.slice(2).join('#')

  // sk = "TEST_YEAR#2016"
  const testYear = parseInt(item.sk.split('#')[1] ?? '0', 10)

  return item.d.map((entry) => {
    const carYear = parseInt(entry.slice(0, 4), 10)
    const bytes = b64ToBytes(entry.slice(4))

    const result: Record<string, unknown> = {
      pk,
      sk: `${item.sk}#CAR_YEAR#${carYear}`,
      make,
      model,
      test_year: testYear,
      car_year: carYear,
    }

    for (let i = 0; i < PCT_KEYS.length; i++) {
      result[PCT_KEYS[i]] = (bytes[i] ?? 0) / 2
    }

    return result as unknown as NctResult
  })
}

// ── Hook ─────────────────────────────────────────────────────────────────────

const API_URL = import.meta.env.VITE_API_URL || ''

export function useNctResults() {
  const [results, setResults] = useState<NctResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const query = useCallback(async (make: string, model: string, year?: string) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ make, model })
      if (year) params.set('year', year)

      const res = await fetch(`${API_URL}/results?${params}`)
      if (!res.ok) throw new Error(`API error: ${res.status}`)

      const data: QueryResponse = await res.json()

      // Expand compact items into flat NctResult rows
      const expanded = data.items.flatMap(expandItem)
      setResults(expanded)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    setResults([])
    setError(null)
  }, [])

  return { results, loading, error, query, clear }
}
