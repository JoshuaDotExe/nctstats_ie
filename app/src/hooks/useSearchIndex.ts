import { useState, useEffect, useMemo } from 'react'

interface SearchIndex {
  makes: string[]
  models: Record<string, string[]>
}

const INDEX_URL = '/search_index.json'

export function useSearchIndex() {
  const [index, setIndex] = useState<SearchIndex | null>(null)

  useEffect(() => {
    fetch(INDEX_URL)
      .then((r) => r.json())
      .then(setIndex)
      .catch(() => {/* silently fail — inputs still work without suggestions */})
  }, [])

  const makes = useMemo(() => index?.makes ?? [], [index])

  const modelsFor = useMemo(
    () => (make: string) => index?.models[make.trim().toUpperCase()] ?? [],
    [index],
  )

  return { makes, modelsFor }
}
