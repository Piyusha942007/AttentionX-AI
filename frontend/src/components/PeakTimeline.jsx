import React from 'react'
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
    Cell
} from 'recharts'

const PeakTimeline = ({ rmsArray, peaks, onPeakSelect, selectedPeak, duration }) => {
    const data = rmsArray.map((value, index) => ({
        time: (index / rmsArray.length) * duration,
        value: value
    }))

    const handleChartClick = (state) => {
        if (state && state.activePayload) {
            const time = state.activePayload[0].payload.time
            const closest = peaks.reduce((prev, curr) => {
                return (Math.abs(curr.time - time) < Math.abs(prev.time - time) ? curr : prev)
            }, peaks[0])
            
            if (closest && Math.abs(closest.time - time) < (duration * 0.05)) {
                onPeakSelect(closest)
            }
        }
    }

    if (!rmsArray || rmsArray.length === 0) {
        return (
            <div className="h-full flex items-center justify-center border-2 border-dashed border-white/5 rounded-xl bg-white/2 p-12 text-center text-muted">
                 <p className="text-[10px] font-black uppercase tracking-[0.3em] opacity-20">Analyzing Audio Waveform...</p>
            </div>
        )
    }

    const getBarColor = (value) => {
        if (value > 0.8) return '#EF4444' // Intense Red
        if (value > 0.6) return '#F97316' // Vibrant Orange
        if (value > 0.4) return '#FBBF24' // Highlight Amber
        if (value > 0.2) return '#3B82F6' // Cool Blue
        return 'rgba(255, 255, 255, 0.05)'
    }

    return (
        <div className="h-full w-full relative group p-4 bg-dark-40 rounded-2xl border border-white-10">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} onClick={handleChartClick} margin={{ top: 40, right: 10, left: 10, bottom: 20 }}>
                    <XAxis dataKey="time" hide />
                    <YAxis hide domain={[0, 1]} />
                    <Tooltip 
                        content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                                return (
                                    <div className="bg-elevated border border-white/10 p-2 rounded shadow-lg text-[10px] font-black uppercase tracking-widest text-amber">
                                        {payload[0].payload.time.toFixed(1)}S | ENERGY: {(payload[0].payload.value * 100).toFixed(0)}%
                                    </div>
                                )
                            }
                            return null
                        }}
                        cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                    />
                    <Bar dataKey="value" radius={[1, 1, 0, 0]}>
                        {data.map((entry, index) => (
                            <Cell 
                                key={`cell-${index}`} 
                                className="heatmap-bar"
                                fill={getBarColor(entry.value)}
                            />
                        ))}
                    </Bar>

                    {/* Viral Peak Markers with Labels */}
                    {peaks.map((peak, idx) => (
                        <ReferenceLine
                            key={idx}
                            x={peak.time}
                            stroke={selectedPeak?.time === peak.time ? "#FFF" : "rgba(255, 255, 255, 0.1)"}
                            strokeWidth={selectedPeak?.time === peak.time ? 2 : 1}
                            isFront={true}
                            label={({ viewBox }) => (
                                <g transform={`translate(${viewBox.x}, ${viewBox.y - 25})`}>
                                    <rect 
                                        x="-40" y="-8" width="80" height="16" rx="4" 
                                        fill={selectedPeak?.time === peak.time ? "#EF4444" : "rgba(15, 23, 42, 0.8)"} 
                                        stroke={selectedPeak?.time === peak.time ? "white" : "rgba(255,255,255,0.1)"}
                                        strokeWidth="0.5"
                                    />
                                    <text 
                                        x="0" y="3" textAnchor="middle" 
                                        fill="white" fontSize="7" fontWeight="900" 
                                        style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                                    >
                                        Viral Nugget #{idx + 1}
                                    </text>
                                    <circle cx="0" cy="18" r="3" fill="#EF4444" stroke="white" strokeWidth="1" />
                                </g>
                            )}
                        />
                    ))}
                </BarChart>
            </ResponsiveContainer>
            
            {/* Timeline Labels */}
            <div className="absolute inset-x-0 bottom-4 flex justify-between px-6 text-[8px] font-black text-muted uppercase tracking-[0.2em] opacity-40">
                <span>00:00:00</span>
                <span>AUDIENCE ATTENTION HEATMAP</span>
                <span>{new Date(duration * 1000).toISOString().substr(11, 8)}</span>
            </div>
        </div>
    )
}

export default PeakTimeline
