import { useState, useCallback } from 'react'

type CarYearAverages = Record<string, Record<string, number>>
type AveragesData = Record<string, CarYearAverages>

let cache: AveragesData | null = null
let fetchPromise: Promise<AveragesData> | null = null

export function useAverages() {
  const [averages, setAverages] = useState<AveragesData | null>(cache)

  const load = useCallback(() => {
    if (cache) {
      setAverages(cache)
      return
    }
    if (!fetchPromise) {
      fetchPromise = fetch('/averages.json')
        .then((r) => r.json())
        .then((data: AveragesData) => {
          cache = data
          return data
        })
    }
    fetchPromise.then(setAverages).catch(console.error)
  }, [])

  /** Get the fleet-wide average row for a specific test year + car year */
  function getAvg(testYear: string | number, carYear: string | number): Record<string, number> | null {
    return averages?.[String(testYear)]?.[String(carYear)] ?? null
  }

  return { averages, load, getAvg }
}
