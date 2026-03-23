import { useEffect, useRef, useState } from 'react'
import type { ChassisEntry } from '../components/ChassisFailureChart'
import ChassisDetailChart from '../components/ChassisDetailChart'
import './Home.css'

const ROTATE_MS = 3000

interface ChassisPayload {
  avg_years: number[]
  avg_yearly_rates: (number | null)[]
  models: ChassisEntry[]
}

function Home() {
  const [payload, setPayload] = useState<ChassisPayload | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetch('/top_chassis_failures.json')
      .then((r) => r.json())
      .then((data: ChassisPayload) => setPayload(data))
      .catch(console.error)
  }, [])

  // Auto-rotate unless paused
  useEffect(() => {
    if (!payload || paused) return
    timerRef.current = setInterval(() => {
      setActiveIndex((i) => (i + 1) % payload.models.length)
    }, ROTATE_MS)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [payload, paused])

  function handleButtonClick(index: number) {
    setActiveIndex(index)
    setPaused(true)
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const active = payload?.models[activeIndex] ?? null

  return (
    <div className="home">
      <h2>Welcome to NCT Stats Ireland</h2>
      <p>Use the navigation above to explore the statistics of the Irish National Car Test</p>

      <div className="home-chart-container">
        {payload && active ? (
          <>
            <h3 className="home-chart-title">Possibly the Rustiest Cars in Ireland</h3>
            <ChassisDetailChart
              allData={payload.models}
              selectedLabels={[active.label]}
              avgYears={payload.avg_years}
              avgYearlyRates={payload.avg_yearly_rates}
            />

            <div className="home-model-selector">
              {payload.models.map((entry, i) => (
                <button
                  key={entry.label}
                  className={`home-model-btn${i === activeIndex ? ' active' : ''}${!paused && i === activeIndex ? ' animating' : ''}`}
                  onClick={() => handleButtonClick(i)}
                  style={
                    (!paused && i === activeIndex)
                      ? { '--rotate-ms': `${ROTATE_MS}ms` } as React.CSSProperties
                      : undefined
                  }
                >
                  {entry.label}
                </button>
              ))}
            </div>

            {paused && (
              <button
                className="home-resume-btn"
                onClick={() => setPaused(false)}
              >
                ▶ Resume auto-rotate
              </button>
            )}
          </>
        ) : (
          <p className="home-loading">Loading…</p>
        )}
      </div>
    </div>
  )
}

export default Home
