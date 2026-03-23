import ReactECharts from 'echarts-for-react'

interface ChartSeries {
  name: string
  data: number[]
  color: string
  areaFill?: boolean
  dashed?: boolean
}

interface PassRatesChartProps {
  title?: string
  labels: string[]
  series: ChartSeries[]
  height?: string
  yMin?: number
  yMax?: number
  /** 'pct' shows % suffix; 'count' shows raw numbers with no suffix */
  yUnit?: 'pct' | 'count'
}

function PassRatesChart({
  title = 'NCT Pass Rates by Year',
  labels,
  series,
  height = '450px',
  yMin,
  yMax,
  yUnit = 'pct',
}: PassRatesChartProps) {
  const chartOptions = {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        color: '#ccc',
      },
      padding: [0, 0, 10, 0],
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: { name: string; value: number; seriesName: string }[]) => {
        const lines = params.map(
          (p) => `${p.seriesName}: <strong>${p.value}${yUnit === 'pct' ? '%' : ''}</strong>`
        )
        return `<strong>${params[0].name}</strong><br/>${lines.join('<br/>')}`
      },
    },
    legend: {
      top: 40,
      textStyle: {
        color: '#aaa',
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: labels,
      axisLabel: { color: '#aaa' },
      axisLine: { lineStyle: { color: '#555' } },
    },
    yAxis: {
      type: 'value' as const,
      ...(yMin !== undefined ? { min: yMin } : {}),
      ...(yMax !== undefined ? { max: yMax } : {}),
      axisLabel: {
        formatter: yUnit === 'pct' ? '{value}%' : '{value}',
        color: '#aaa',
      },
      splitLine: { lineStyle: { color: '#333' } },
    },
    series: series.map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      data: s.data,
      lineStyle: { width: s.dashed ? 2 : 3, type: s.dashed ? 'dashed' : 'solid' },
      itemStyle: { color: s.color },
      symbolSize: s.dashed ? 0 : 4,
      areaStyle: s.areaFill
        ? {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: s.color.replace(')', ', 0.3)').replace('rgb', 'rgba') },
                { offset: 1, color: s.color.replace(')', ', 0.02)').replace('rgb', 'rgba') },
              ],
            },
          }
        : undefined,
    })),
  }

  return (
    <ReactECharts
      option={chartOptions}
      notMerge={true}
      style={{ height, width: '100%' }}
    />
  )
}

export default PassRatesChart
