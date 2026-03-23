import { useState, useMemo, useEffect, type FormEvent } from 'react'
import { useNctResults, KEY_LABELS, type NctResult } from '../hooks/useNctResults'
import { useSearchIndex } from '../hooks/useSearchIndex'
import { useAverages } from '../hooks/useAverages'
import PassRatesChart from '../components/PassRatesChart'
import Combobox from '../components/Combobox'
import './Search.css'

// Palette for test-year comparison lines (12 distinct colours for 2013-2024)
const TEST_YEAR_COLORS = [
  '#f44336', '#e91e63', '#9c27b0', '#673ab7',
  '#3f51b5', '#2196f3', '#00bcd4', '#009688',
  '#4caf50', '#8bc34a', '#ff9800', '#ff5722',
]

function Search() {
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [year, setYear] = useState('')
  const [selectedCarYears, setSelectedCarYears] = useState<[number, number] | null>(null)
  const [selectedMetrics, setSelectedMetrics] = useState<Set<string>>(new Set(['P', 'F']))
  const [displayMode, setDisplayMode] = useState<'pct-total' | 'pct-fail' | 'count'>('pct-total')
  const [viewMode, setViewMode] = useState<'single' | 'compare'>('single')
  const [compareMetric, setCompareMetric] = useState<string>('P')
  const [selectedTestYears, setSelectedTestYears] = useState<Set<number>>(new Set())
  const [showAverage, setShowAverage] = useState(false)
  const { results, loading, error, query } = useNctResults()
  const { makes, modelsFor } = useSearchIndex()
  const { load: loadAverages, getAvg } = useAverages()
  const modelOptions = useMemo(() => modelsFor(make), [make, modelsFor])

  // Pre-load averages file as soon as the component mounts
  useEffect(() => { loadAverages() }, [loadAverages])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (make && model) {
      if (viewMode === 'compare') {
        // Compare mode always fetches all test years
        query(make, model)
      } else {
        // Single mode requires a year — enforced by required attr but guard here too
        if (!year) return
        query(make, model, year)
      }
      setSelectedCarYears(null) // reset range on new search
      setSelectedTestYears(new Set()) // reset test year selection
    }
  }

  // Metrics that can be shown on the chart (as % of Total)
  const METRIC_COLORS: Record<string, string> = {
    P: '#43b581',
    F: '#f04747',
    Sa: '#e67e22',
    Li: '#f1c40f',
    St: '#9b59b6',
    Br: '#e74c3c',
    Wh: '#1abc9c',
    En: '#3498db',
    Ch: '#e91e63',
    Ss: '#00bcd4',
    Su: '#ff9800',
    Lt: '#cddc39',
    Bk: '#ff5722',
    Em: '#8bc34a',
    Ot: '#607d8b',
    In: '#795548',
  }

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  // All car years available in results
  const allCarYears = results
    .filter((r) => r.T > 0)
    .map((r) => r.car_year)
    .sort((a, b) => a - b)

  const minYear = allCarYears.length > 0 ? allCarYears[0] : 0
  const maxYear = allCarYears.length > 0 ? allCarYears[allCarYears.length - 1] : 0
  const rangeMin = selectedCarYears ? selectedCarYears[0] : minYear
  const rangeMax = selectedCarYears ? selectedCarYears[1] : maxYear

  // ── Compare mode: group results by test_year ──────────────────────────
  const availableTestYears = useMemo(() => {
    const years = new Set(results.map((r) => r.test_year))
    return Array.from(years).sort((a, b) => a - b)
  }, [results])

  // Default to all test years when results change and none are selected
  const activeTestYears = useMemo(() => {
    if (selectedTestYears.size > 0) return selectedTestYears
    return new Set(availableTestYears)
  }, [selectedTestYears, availableTestYears])

  const toggleTestYear = (y: number) => {
    setSelectedTestYears((prev) => {
      const next = new Set(prev.size > 0 ? prev : availableTestYears)
      if (next.has(y)) {
        next.delete(y)
      } else {
        next.add(y)
      }
      return next
    })
  }

  // The failure category count keys (excludes T, P, F)
  const FAILURE_COUNT_KEYS = ['Sa', 'Li', 'St', 'Br', 'Wh', 'En', 'Ch', 'Ss', 'Su', 'Lt', 'Bk', 'Em', 'Ot', 'In']

  // Build compare chart: one line per test year for the selected metric
  const compareChartData = useMemo(() => {
    if (viewMode !== 'compare') return { labels: [] as string[], series: [] as { name: string; data: number[]; color: string }[] }

    // Get union of all car years across active test years, filtered by range
    const byTestYear = new Map<number, NctResult[]>()
    for (const r of results) {
      if (!activeTestYears.has(r.test_year)) continue
      if (r.T <= 0) continue
      if (r.car_year < rangeMin || r.car_year > rangeMax) continue
      if (!byTestYear.has(r.test_year)) byTestYear.set(r.test_year, [])
      byTestYear.get(r.test_year)!.push(r)
    }

    // Union of car years for labels
    const carYearSet = new Set<number>()
    for (const rows of byTestYear.values()) {
      for (const r of rows) carYearSet.add(r.car_year)
    }
    const labels = Array.from(carYearSet).sort((a, b) => a - b).map(String)
    const carYearsArr = Array.from(carYearSet).sort((a, b) => a - b)

    // One series per test year
    const sortedTestYears = Array.from(byTestYear.keys()).sort((a, b) => a - b)
    const series = sortedTestYears.map((testYear, idx) => {
      const rows = byTestYear.get(testYear)!
      const rowMap = new Map(rows.map((r) => [r.car_year, r]))
      const key = compareMetric
      return {
        name: `NCT ${testYear}`,
        data: carYearsArr.map((cy) => {
          const r = rowMap.get(cy)
          if (!r) return null as unknown as number // gap in data
          const val = r[key as keyof NctResult] as number
          if (displayMode === 'count') return val
          const denom = (key === 'P' || key === 'F' || displayMode === 'pct-total') ? r.T : r.F
          return denom > 0 ? Math.round((val / denom) * 1000) / 10 : 0
        }),
        color: TEST_YEAR_COLORS[idx % TEST_YEAR_COLORS.length],
      }
    })

    return { labels, series }
  }, [results, viewMode, activeTestYears, rangeMin, rangeMax, compareMetric, displayMode])

  // ── Single mode chart data ────────────────────────────────────────────
  const chartData = results
    .sort((a, b) => a.car_year - b.car_year)
    .filter((r) => r.T > 0 && r.car_year >= rangeMin && r.car_year <= rangeMax)

  const chartLabels = chartData.map((r) => String(r.car_year))

  // In count mode show all failure categories; otherwise use selected metrics
  const activeMetricKeys = displayMode === 'count' ? FAILURE_COUNT_KEYS : Array.from(selectedMetrics)

  const chartSeries = activeMetricKeys.map((key) => ({
    name: displayMode === 'count' ? KEY_LABELS[key] : `${KEY_LABELS[key]} %`,
    data: chartData.map((r) => {
      const val = r[key as keyof typeof r] as number
      if (displayMode === 'count') return val
      const denom = (key === 'P' || key === 'F' || displayMode === 'pct-total') ? r.T : r.F
      return denom > 0 ? Math.round((val / denom) * 1000) / 10 : 0
    }),
    color: METRIC_COLORS[key] || '#667eea',
  }))

  // Average overlay series for single mode
  const avgSeries = useMemo(() => {
    if (!showAverage || viewMode !== 'single' || !year) return []
    return activeMetricKeys.map((key) => ({
      name: `Avg ${KEY_LABELS[key]}${displayMode === 'count' ? '' : ' %'}`,
      data: chartData.map((r) => {
        const avg = getAvg(year, r.car_year)
        if (!avg) return null as unknown as number
        if (displayMode === 'count') return avg[key] ?? 0
        const avgVal = avg[key] ?? 0
        const denom = (key === 'P' || key === 'F' || displayMode === 'pct-total')
          ? avg['T'] : avg['F']
        return denom > 0 ? Math.round((avgVal / denom) * 1000) / 10 : 0
      }),
      color: METRIC_COLORS[key] ? METRIC_COLORS[key] + '88' : '#aaaaaa',
      dashed: true,
    }))
  }, [showAverage, viewMode, year, activeMetricKeys, chartData, getAvg, displayMode])

  return (
    <div className="search">
      <h2>Search NCT Results</h2>

      <form className="search-form" onSubmit={handleSubmit}>
        <Combobox
          id="make"
          label="Make"
          value={make}
          onChange={(v) => { setMake(v); setModel('') }}
          options={makes}
          placeholder="e.g. FORD"
          required
        />
        <Combobox
          id="model"
          label="Model"
          value={model}
          onChange={setModel}
          options={modelOptions}
          placeholder="e.g. FOCUS"
          required
        />
        {viewMode === 'single' && (
          <div className="search-field">
            <label htmlFor="year">Test Year</label>
            <input
              id="year"
              type="text"
              placeholder="e.g. 2016"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              required
            />
          </div>
        )}
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* View mode toggle */}
      <div className="view-mode-toggle">
        <span className="view-mode-label">View:</span>
        <div className="view-mode-options">
          <button
            type="button"
            className={`view-mode-btn ${viewMode === 'single' ? 'active' : ''}`}
            onClick={() => { setViewMode('single') }}
          >
            Single Test Year
          </button>
          <button
            type="button"
            className={`view-mode-btn ${viewMode === 'compare' ? 'active' : ''}`}
            onClick={() => { setViewMode('compare'); setYear('') }}
          >
            Compare Across Years
          </button>
        </div>
      </div>

      {error && <p className="search-error">{error}</p>}

      {results.length > 0 && (
        <>
          <div className="car-year-filter">
            <span className="car-year-filter-label">Car year range:</span>
            <div className="car-year-range">
              <span className="car-year-range-value">{rangeMin}</span>
              <div className="car-year-sliders">
                <input
                  type="range"
                  min={minYear}
                  max={maxYear}
                  value={rangeMin}
                  onChange={(e) => {
                    const val = Number(e.target.value)
                    setSelectedCarYears([Math.min(val, rangeMax), rangeMax])
                  }}
                  className="range-slider range-slider-min"
                />
                <input
                  type="range"
                  min={minYear}
                  max={maxYear}
                  value={rangeMax}
                  onChange={(e) => {
                    const val = Number(e.target.value)
                    setSelectedCarYears([rangeMin, Math.max(val, rangeMin)])
                  }}
                  className="range-slider range-slider-max"
                />
              </div>
              <span className="car-year-range-value">{rangeMax}</span>
            </div>
          </div>

          {/* ── Single mode controls ─────────────────────────────────── */}
          {viewMode === 'single' && (
            <>
              <div className="metric-selector">
                <span className="metric-selector-label">Show on chart:</span>
                <div className="metric-selector-options">
                  {Object.entries(METRIC_COLORS).map(([key, color]) => (
                    <button
                      key={key}
                      type="button"
                      disabled={displayMode === 'count'}
                      className={`metric-btn ${selectedMetrics.has(key) ? 'active' : ''} ${displayMode === 'count' ? 'disabled' : ''}`}
                      style={selectedMetrics.has(key) && displayMode !== 'count' ? { backgroundColor: color, borderColor: color } : {}}
                      onClick={() => toggleMetric(key)}
                      title={displayMode === 'count' ? 'Metric selection disabled in Count mode' : KEY_LABELS[key]}
                    >
                      {KEY_LABELS[key]}
                    </button>
                  ))}
                </div>
              </div>

              <div className="percent-base-toggle">
                <span className="percent-base-label">Show values as:</span>
                <div className="percent-base-options">
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'pct-total' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('pct-total')}
                  >
                    % of Total Tests
                  </button>
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'pct-fail' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('pct-fail')}
                  >
                    % of Fails
                  </button>
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'count' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('count')}
                  >
                    Count
                  </button>
                </div>
              </div>

              <div className="percent-base-toggle">
                <span className="percent-base-label">Fleet average:</span>
                <div className="percent-base-options">
                  <button
                    type="button"
                    className={`percent-base-btn ${showAverage ? 'active' : ''}`}
                    onClick={() => setShowAverage((v) => !v)}
                    title="Show the national fleet average for the same test year alongside the selected model"
                  >
                    {showAverage ? 'Hide average' : 'Show average'}
                  </button>
                </div>
              </div>

              <div className="search-chart-container">
                <PassRatesChart
                  title={`${make.toUpperCase()} ${model.toUpperCase()} — ${displayMode === 'count' ? 'Failure Counts' : 'Stat Rates'} by Car Year`}
                  labels={chartLabels}
                  series={[...chartSeries, ...avgSeries]}
                  yUnit={displayMode === 'count' ? 'count' : 'pct'}
                  yMin={displayMode === 'count' ? undefined : 0}
                  yMax={displayMode === 'count' ? undefined : 100}
                />
              </div>
            </>
          )}

          {/* ── Compare mode controls ────────────────────────────────── */}
          {viewMode === 'compare' && (
            <>
              <div className="metric-selector">
                <span className="metric-selector-label">Metric to compare:</span>
                <div className="metric-selector-options">
                  {Object.entries(METRIC_COLORS).map(([key, color]) => (
                    <button
                      key={key}
                      type="button"
                      className={`metric-btn ${compareMetric === key ? 'active' : ''}`}
                      style={compareMetric === key ? { backgroundColor: color, borderColor: color } : {}}
                      onClick={() => setCompareMetric(key)}
                      title={KEY_LABELS[key]}
                    >
                      {KEY_LABELS[key]}
                    </button>
                  ))}
                </div>
              </div>

              <div className="percent-base-toggle">
                <span className="percent-base-label">Show values as:</span>
                <div className="percent-base-options">
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'pct-total' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('pct-total')}
                  >
                    % of Total Tests
                  </button>
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'pct-fail' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('pct-fail')}
                  >
                    % of Fails
                  </button>
                  <button
                    type="button"
                    className={`percent-base-btn ${displayMode === 'count' ? 'active' : ''}`}
                    onClick={() => setDisplayMode('count')}
                  >
                    Count
                  </button>
                </div>
              </div>

              <div className="test-year-selector">
                <span className="metric-selector-label">Test years:</span>
                <div className="metric-selector-options">
                  {availableTestYears.map((ty, idx) => (
                    <button
                      key={ty}
                      type="button"
                      className={`metric-btn ${activeTestYears.has(ty) ? 'active' : ''}`}
                      style={activeTestYears.has(ty) ? { backgroundColor: TEST_YEAR_COLORS[idx % TEST_YEAR_COLORS.length], borderColor: TEST_YEAR_COLORS[idx % TEST_YEAR_COLORS.length] } : {}}
                      onClick={() => toggleTestYear(ty)}
                    >
                      {ty}
                    </button>
                  ))}
                </div>
              </div>

              <div className="search-chart-container">
                <PassRatesChart
                  title={`${make.toUpperCase()} ${model.toUpperCase()} — ${KEY_LABELS[compareMetric]} ${displayMode === 'count' ? 'Count' : '%'} Across Test Years`}
                  labels={compareChartData.labels}
                  series={compareChartData.series}
                  yUnit={displayMode === 'count' ? 'count' : 'pct'}
                  yMin={displayMode === 'count' ? undefined : 0}
                  yMax={displayMode === 'count' ? undefined : 100}
                />
              </div>
            </>
          )}

          <div className="search-table-wrapper">
            <table className="search-table">
              <thead>
                <tr>
                  {viewMode === 'compare' && <th>Test Year</th>}
                  <th>Car Year</th>
                  {displayMode === 'count' ? (
                    // Count mode: Total + all count fields (no _pct columns)
                    <>
                      <th title="Total">Total</th>
                      {FAILURE_COUNT_KEYS.map((key) => (
                        <th key={key} title={KEY_LABELS[key]}>{KEY_LABELS[key]}</th>
                      ))}
                    </>
                  ) : (
                    Object.entries(KEY_LABELS).map(([key, label]) => (
                      <th key={key} title={label}>{key}</th>
                    ))
                  )}
                </tr>
              </thead>
              <tbody>
                {(viewMode === 'compare'
                  ? results
                      .filter((r) => r.T > 0 && activeTestYears.has(r.test_year) && r.car_year >= rangeMin && r.car_year <= rangeMax)
                      .sort((a, b) => a.test_year - b.test_year || a.car_year - b.car_year)
                  : chartData
                ).map((r) => (
                  <tr key={r.sk}>
                    {viewMode === 'compare' && <td>{r.test_year}</td>}
                    <td>{r.car_year}</td>
                    {displayMode === 'count' ? (
                      <>
                        <td>{r.T}</td>
                        {FAILURE_COUNT_KEYS.map((key) => (
                          <td key={key}>{r[key as keyof typeof r] ?? 0}</td>
                        ))}
                      </>
                    ) : (
                      Object.keys(KEY_LABELS).map((key) => (
                        <td key={key}>{r[key as keyof typeof r] ?? 0}</td>
                      ))
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && !error && results.length === 0 && make && model && (
        <p className="search-empty">No results found.</p>
      )}
    </div>
  )
}

export default Search
