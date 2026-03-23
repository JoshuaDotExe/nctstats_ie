import ReactECharts from 'echarts-for-react'

export interface ChassisEntry {
  label: string
  chassis_rate: number
  chassis: number
  total: number
  years: number[]
  yearly_rates: (number | null)[]
}

interface ChassisFailureChartProps {
  data: ChassisEntry[]
  selectedLabel?: string
  onSelect?: (label: string) => void
  height?: string
}

// Colour gradient from amber → red as rate increases
const BAR_COLORS = [
  '#e63946', '#e84d59', '#ea606b', '#ec737e', '#ee8690',
  '#f09aa3', '#f2adb5', '#f4c0c8', '#f6d3da', '#f8e6ec',
]

function ChassisFailureChart({ data, selectedLabel, onSelect, height = '420px' }: ChassisFailureChartProps) {
  // Sort ascending so highest rate appears at the top of the horizontal bar chart
  const sorted = [...data].sort((a, b) => a.chassis_rate - b.chassis_rate)

  const option = {
    title: {
      text: 'Most Rust-Prone Cars in Ireland',
      subtext: 'By chassis & body failure rate across all NCT test years',
      left: 'center',
      textStyle: { color: '#ccc', fontSize: 16 },
      subtextStyle: { color: '#888', fontSize: 12 },
      padding: [0, 0, 16, 0],
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number; dataIndex: number }[]) => {
        const p = params[0]
        const entry = sorted[p.dataIndex]
        return [
          `<strong>${entry.label}</strong>`,
          `Chassis fail rate: <strong>${entry.chassis_rate.toFixed(2)}%</strong>`,
          `Chassis failures: ${entry.chassis.toLocaleString()}`,
          `Total tests: ${entry.total.toLocaleString()}`,
        ].join('<br/>')
      },
    },
    grid: {
      left: '2%',
      right: '8%',
      top: '15%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'value' as const,
      axisLabel: {
        formatter: '{value}%',
        color: '#aaa',
      },
      splitLine: { lineStyle: { color: '#333' } },
    },
    yAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.label),
      axisLabel: { color: '#ccc', fontSize: 12 },
      axisLine: { lineStyle: { color: '#555' } },
    },
    series: [
      {
        name: 'Chassis fail rate',
        type: 'bar',
        data: sorted.map((d, i) => ({
          value: d.chassis_rate,
          itemStyle: {
            color: d.label === selectedLabel
              ? '#facc15'
              : BAR_COLORS[BAR_COLORS.length - 1 - i] ?? BAR_COLORS[0],
            borderColor: d.label === selectedLabel ? '#facc15' : 'transparent',
            borderWidth: 2,
          },
        })),
        label: {
          show: true,
          position: 'right' as const,
          formatter: '{c}%',
          color: '#ccc',
          fontSize: 11,
        },
        barMaxWidth: 32,
      },
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      theme="dark"
      onEvents={{
        click: (params: { dataIndex: number }) => {
          onSelect?.(sorted[params.dataIndex].label)
        },
      }}
    />
  )
}

export default ChassisFailureChart
