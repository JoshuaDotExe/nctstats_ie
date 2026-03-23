import ReactECharts from 'echarts-for-react'
import type { ChassisEntry } from './ChassisFailureChart'

const LINE_COLOR = '#e63946'
const AVG_COLOR  = '#6b7280'

interface ChassisDetailChartProps {
  allData: ChassisEntry[]
  selectedLabels: string[]
  avgYears?: number[]
  avgYearlyRates?: (number | null)[]
  height?: string
}

function ChassisDetailChart({ allData, selectedLabels, avgYears, avgYearlyRates, height = '380px' }: ChassisDetailChartProps) {
  const entry = allData.find((d) => selectedLabels.includes(d.label))

  if (!entry) {
    return (
      <p style={{ textAlign: 'center', color: '#888', padding: '3rem 0' }}>
        No model selected
      </p>
    )
  }

  const years = entry.years.map(String)

  const option = {
    title: {
      text: `${entry.label}`,
      subtext: `Chassis & body failure rate by NCT test year  •  ${entry.chassis_rate.toFixed(1)}% overall`,
      left: 'center',
      textStyle: { color: '#ccc', fontSize: 16 },
      subtextStyle: { color: '#888', fontSize: 12 },
      padding: [0, 0, 12, 0],
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: { seriesName: string; value: number | null; name: string }[]) => {
        const year = params[0]?.name ?? ''
        const lines = params
          .filter((p) => p.value !== null && p.value !== undefined)
          .map((p) => `${p.seriesName}: <strong>${p.value}%</strong>`)
        return `<strong>${year}</strong><br/>${lines.join('<br/>')}`
      },
    },
    legend: {
      top: 40,
      textStyle: { color: '#aaa' },
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '24%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: years,
      axisLabel: { color: '#aaa' },
      axisLine: { lineStyle: { color: '#555' } },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { formatter: '{value}%', color: '#aaa' },
      splitLine: { lineStyle: { color: '#333' } },
    },
    series: [
      {
        name: entry.label,
        type: 'line' as const,
        smooth: true,
        connectNulls: false,
        data: entry.yearly_rates,
        lineStyle: { width: 3, color: LINE_COLOR },
        itemStyle: { color: LINE_COLOR },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(230,57,70,0.35)' },
              { offset: 1, color: 'rgba(230,57,70,0.02)' },
            ],
          },
        },
        symbolSize: 7,
      },
      ...(avgYears && avgYearlyRates ? [{
        name: 'National average',
        type: 'line' as const,
        smooth: true,
        connectNulls: false,
        data: avgYearlyRates,
        lineStyle: { width: 2, color: AVG_COLOR, type: 'dashed' as const },
        itemStyle: { color: AVG_COLOR },
        symbolSize: 5,
        areaStyle: undefined,
      }] : []),
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      theme="dark"
    />
  )
}

export default ChassisDetailChart
