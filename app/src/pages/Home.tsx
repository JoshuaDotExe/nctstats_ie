import PassRatesChart from '../components/PassRatesChart'
import './Home.css'

const labels = ['2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']

const series = [
  {
    name: 'Overall',
    data: [51.5, 52.3, 53.1, 49.8, 51.2, 52.7, 53.5, 54.1],
    color: '#667eea',
    areaFill: true,
  },
  {
    name: 'First Test',
    data: [48.2, 49.0, 50.5, 46.3, 47.8, 49.5, 50.8, 51.3],
    color: '#764ba2',
  },
  {
    name: 'Retest',
    data: [82.1, 83.5, 84.0, 80.2, 82.8, 84.1, 85.0, 85.7],
    color: '#43b581',
  },
]

function Home() {
  return (
    <div className="home">
      <h2>Welcome to NCT Stats Ireland</h2>
      <p>Use the navigation above to explore the statistics of the Irish National Car Test</p>

      <div className="home-chart-container">
        <PassRatesChart labels={labels} series={series} />
      </div>
    </div>
  )
}

export default Home
