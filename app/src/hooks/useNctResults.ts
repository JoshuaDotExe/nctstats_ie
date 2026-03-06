import { useState, useCallback } from 'react'

// Key mapping from short keys to display names
const KEY_LABELS: Record<string, string> = {
  T: 'Total',
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

export interface NctResult {
  pk: string
  sk: string
  make: string
  model: string
  test_year: number
  car_year: number
  T: number
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

interface QueryResponse {
  count: number
  items: NctResult[]
}

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
      setResults(data.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  return { results, loading, error, query }
}
