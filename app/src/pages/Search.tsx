import { useState, type FormEvent } from 'react'
import { useNctResults, KEY_LABELS } from '../hooks/useNctResults'
import PassRatesChart from '../components/PassRatesChart'
import './Search.css'

function Search() {
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [year, setYear] = useState('')
  const [selectedCarYears, setSelectedCarYears] = useState<[number, number] | null>(null)
  const [selectedMetrics, setSelectedMetrics] = useState<Set<string>>(new Set(['P', 'F']))
  const [percentBase, setPercentBase] = useState<'total' | 'fail'>('total')
  const { results, loading, error, query } = useNctResults()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (make && model) {
      query(make, model, year || undefined)
      setSelectedCarYears(null) // reset range on new search
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

  // Build chart data: group results by car_year, show pass rate per car year
  const chartData = results
    .sort((a, b) => a.car_year - b.car_year)
    .filter((r) => r.T > 0 && r.car_year >= rangeMin && r.car_year <= rangeMax)

  const chartLabels = chartData.map((r) => String(r.car_year))
  const metricsArray = Array.from(selectedMetrics)
  const chartSeries = metricsArray.map((key) => ({
    name: `${KEY_LABELS[key]} %`,
    data: chartData.map((r) => {
      const val = r[key as keyof typeof r] as number
      // Pass & Fail always as % of Total; others depend on toggle
      const denom = (key === 'P' || key === 'F' || percentBase === 'total') ? r.T : r.F
      return denom > 0 ? Math.round((val / denom) * 1000) / 10 : 0
    }),
    color: METRIC_COLORS[key] || '#667eea',
  }))

  return (
    <div className="search">
      <h2>Search NCT Results</h2>

      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-field">
          <label htmlFor="make">Make</label>
          <input
            id="make"
            type="text"
            placeholder="e.g. FORD"
            value={make}
            onChange={(e) => setMake(e.target.value)}
            required
          />
        </div>
        <div className="search-field">
          <label htmlFor="model">Model</label>
          <input
            id="model"
            type="text"
            placeholder="e.g. FOCUS"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            required
          />
        </div>
        <div className="search-field">
          <label htmlFor="year">Test Year (optional)</label>
          <input
            id="year"
            type="text"
            placeholder="e.g. 2016"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

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

          <div className="metric-selector">
            <span className="metric-selector-label">Show on chart:</span>
            <div className="metric-selector-options">
              {Object.entries(METRIC_COLORS).map(([key, color]) => (
                <button
                  key={key}
                  type="button"
                  className={`metric-btn ${selectedMetrics.has(key) ? 'active' : ''}`}
                  style={selectedMetrics.has(key) ? { backgroundColor: color, borderColor: color } : {}}
                  onClick={() => toggleMetric(key)}
                  title={KEY_LABELS[key]}
                >
                  {KEY_LABELS[key]}
                </button>
              ))}
            </div>
          </div>

          <div className="percent-base-toggle">
            <span className="percent-base-label">Failure categories as:</span>
            <div className="percent-base-options">
              <button
                type="button"
                className={`percent-base-btn ${percentBase === 'total' ? 'active' : ''}`}
                onClick={() => setPercentBase('total')}
              >
                % of Total Tests
              </button>
              <button
                type="button"
                className={`percent-base-btn ${percentBase === 'fail' ? 'active' : ''}`}
                onClick={() => setPercentBase('fail')}
              >
                % of Fails
              </button>
            </div>
          </div>

          <div className="search-chart-container">
            <PassRatesChart
              title={`${make.toUpperCase()} ${model.toUpperCase()} Stat Rates by Car Year`}
              labels={chartLabels}
              series={chartSeries}
              yMin={0}
              yMax={100}
            />
          </div>

          <div className="search-table-wrapper">
            <table className="search-table">
              <thead>
                <tr>
                  <th>Car Year</th>
                  {Object.entries(KEY_LABELS).map(([key, label]) => (
                    <th key={key} title={label}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chartData.map((r) => (
                  <tr key={r.sk}>
                    <td>{r.car_year}</td>
                    {Object.keys(KEY_LABELS).map((key) => (
                      <td key={key}>{r[key as keyof typeof r] ?? 0}</td>
                    ))}
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
