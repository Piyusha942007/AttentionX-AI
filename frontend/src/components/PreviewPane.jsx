import React, { useState, useEffect, useRef } from 'react'
import { Play, Maximize2, Scissors, Type, Loader2, Copy, Download, Sparkles } from 'lucide-react'

const COLORS = [
    { name: 'Yellow', hex: '#FFE234', ass: '&H0034E2FF' },
    { name: 'Green', hex: '#00FF00', ass: '&H0000FF00' },
    { name: 'Cyan', hex: '#00FFFF', ass: '&H00FFFF00' },
    { name: 'Pink', hex: '#FF00FF', ass: '&H00FF00FF' },
]

const PreviewPane = ({ selectedPeak, jobId }) => {
    const [activeWordIndex, setActiveWordIndex] = useState(-1)
    const [currentTime, setCurrentTime] = useState(0)
    const [selectedColor, setSelectedColor] = useState(COLORS[0])
    const [isExporting, setIsExporting] = useState(false)
    const [exportUrl, setExportUrl] = useState(null)
    const videoRef = useRef(null)

    // Sync simulation with video playback if it exists
    const handleTimeUpdate = () => {
        if (videoRef.current) {
            const time = videoRef.current.currentTime
            setCurrentTime(time)
            
            if (selectedPeak?.words) {
                const absoluteTime = selectedPeak.start + time
                const wordIdx = selectedPeak.words.findIndex(w => absoluteTime >= w.start && absoluteTime <= w.end)
                if (wordIdx !== activeWordIndex) {
                    setActiveWordIndex(wordIdx)
                }
            }
        }
    }

    const handleExport = async () => {
        if (!jobId || !selectedPeak?.clip_id) return
        
        setIsExporting(true)
        setExportUrl(null)
        
        try {
            const res = await fetch(`/api/clips/${jobId}/${selectedPeak.clip_id}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caption_color: selectedColor.name })
            })
            
            if (res.ok) {
                const data = await res.json()
                setExportUrl(data.download_url)
                // Auto-open download in new tab
                window.open(data.download_url, '_blank')
            }
        } catch (error) {
            console.error('Export error:', error)
        } finally {
            setIsExporting(false)
        }
    }

    // Fallback simulation if no video is playing
    useEffect(() => {
        let timer
        if (selectedPeak && !selectedPeak.clip_url) {
            setCurrentTime(0)
            setActiveWordIndex(-1)
            
            timer = setInterval(() => {
                setCurrentTime(prev => {
                    const nextTime = prev + 0.1
                    const absoluteTime = selectedPeak.start + nextTime
                    const wordIdx = selectedPeak.words?.findIndex(w => absoluteTime >= w.start && absoluteTime <= w.end)
                    if (wordIdx !== activeWordIndex) setActiveWordIndex(wordIdx)
                    
                    if (nextTime > (selectedPeak.end - selectedPeak.start)) return 0
                    return nextTime
                })
            }, 100)
        }
        return () => clearInterval(timer)
    }, [selectedPeak, selectedPeak?.clip_url])

    if (!selectedPeak) {
        return (
            <div className="h-full flex items-center justify-center border-2 border-dashed border-white/5 rounded-2xl bg-white/2 text-muted">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                        <Play className="w-8 h-8 opacity-20" />
                    </div>
                    <div>
                        <p className="text-sm font-bold uppercase tracking-widest opacity-40">Insight Selection Required</p>
                        <p className="text-[10px] text-center mt-1 opacity-20 uppercase font-black">Select a nugget to generate preview</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="h-full flex gap-10 animate-fade-in px-2 items-center">
            {/* Left: Original 16:9 / Main Context */}
            <div className="flex-1 flex flex-col h-full">
                <div className="flex items-center justify-between mb-4">
                    <span className="text-xxs uppercase font-black text-muted flex items-center gap-2">
                        <Scissors className="w-3.5 h-3.5" /> Source Context
                    </span>
                    <span className="text-xxs font-black text-emerald-400 uppercase tracking-[0.2em] bg-emerald-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                        <Sparkles className="w-3 h-3" /> Dynamic Smart Tracking [ON]
                    </span>
                </div>
                <div className="flex-1 bg-black rounded-3xl relative overflow-hidden border border-white-10 shadow-2xl group ring-1 ring-white/5">
                    {/* Simulated 16:9 Frame */}
                    <div className="absolute inset-0 bg-slate-900/40 flex items-center justify-center">
                         <p className="text-xxs text-white/5 font-black uppercase tracking-[1em]">Source_Input_Active</p>
                    </div>
                    
                    {/* Face Detection Indicator (Mock for Ref) */}
                    <div 
                        className="face-box transition-all duration-300"
                        style={{ 
                            top: '25%', left: '44%', width: '12%', height: '22%'
                        }}
                    >
                         <div className="absolute -top-6 left-0 text-[8px] font-black text-teal-400 bg-black/60 px-1 rounded">FACE_LOCKED: 0.98</div>
                    </div>

                    {/* Crop Overlay */}
                    <div 
                        className="absolute h-full w-[31.6%] bg-teal-500/5 border-x border-teal-500/30 shadow-[0_0_60px_rgba(45,212,191,0.15)] transition-all duration-700 ease-smooth"
                        style={{ left: '34.2%' }}
                    >
                        <div className="absolute top-4 left-4 flex items-center gap-2 bg-teal-500 text-xxs text-dark px-3 py-1 font-black tracking-widest rounded shadow-lg uppercase">
                            Vertical Segment
                        </div>
                    </div>
                </div>

                {/* Bottom Tools */}
                <div className="mt-6 flex items-center justify-between bg-white/2 p-4 rounded-2xl border border-white/5">
                    <div className="flex flex-col gap-2">
                        <span className="text-[9px] font-black text-muted uppercase tracking-widest">Caption Style</span>
                        <div className="flex gap-2">
                            {COLORS.map(color => (
                                <button
                                    key={color.name}
                                    onClick={() => setSelectedColor(color)}
                                    className={`w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 ${selectedColor.name === color.name ? 'border-white scale-110' : 'border-transparent opacity-40 hover:opacity-100'}`}
                                    style={{ backgroundColor: color.hex }}
                                />
                            ))}
                        </div>
                    </div>

                    <button 
                        onClick={handleExport}
                        disabled={isExporting || !selectedPeak.clip_url}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all ${isExporting ? 'bg-white/5 text-muted' : 'bg-grad-premium text-dark shadow-lg shadow-amber-500/20 active:scale-95'}`}
                    >
                        {isExporting ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" /> Rendering...
                            </>
                        ) : (
                            <>
                                <Download className="w-4 h-4" /> Export Video
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Right: Vertical 9:16 Output (iPhone Frame) */}
            <div className="flex flex-col items-center h-full">
                <div className="flex items-center justify-between w-full mb-4 px-2">
                    <span className="text-xxs uppercase font-black text-muted flex items-center gap-2">
                         Smart Crop Preview
                    </span>
                    <div className="flex gap-2">
                        <Type className="w-3.5 h-3.5 text-muted" />
                        <Copy className="w-3.5 h-3.5 text-muted hover:text-white cursor-pointer" />
                    </div>
                </div>
                
                <div className="phone-frame animate-fade-in-up">
                    <div className="phone-notch" />
                    
                    {selectedPeak.clip_url ? (
                        <video 
                            ref={videoRef}
                            key={selectedPeak.clip_url}
                            src={selectedPeak.clip_url}
                            onTimeUpdate={handleTimeUpdate}
                            className="w-full h-full object-cover"
                            autoPlay
                            loop
                            muted
                        />
                    ) : (
                        <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center p-8 text-center">
                            <Loader2 className="w-6 h-6 text-amber animate-spin mb-4" />
                            <p className="text-[7px] font-black uppercase tracking-[0.3em] text-muted">Mining Nuggets</p>
                        </div>
                    )}

                    {/* Captions */}
                    <div className="absolute bottom-[25%] inset-x-0 px-5 flex flex-wrap justify-center gap-x-1.5 gap-y-1 z-10 pointer-events-none">
                        {selectedPeak.words?.map((word, idx) => {
                            if (activeWordIndex === -1) return null
                            const isVisible = Math.abs(idx - activeWordIndex) < 3
                            if (!isVisible) return null
                            
                            return (
                                <span 
                                    key={idx}
                                    style={{ color: idx === activeWordIndex ? selectedColor.hex : 'rgba(255,255,255,0.6)' }}
                                    className={`
                                        text-[11px] font-black uppercase tracking-tight transition-all duration-200 drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]
                                        ${idx === activeWordIndex ? 'scale-110' : ''}
                                    `}
                                >
                                    {word.word}
                                </span>
                            )
                        })}
                    </div>

                    {/* Playback Progress */}
                    <div className="absolute bottom-0 inset-x-0 h-1 bg-white/5">
                        <div 
                            className="h-full bg-grad-premium shadow-lg transition-all duration-100"
                            style={{ width: `${(currentTime / (selectedPeak.end - selectedPeak.start)) * 100}%` }}
                        />
                    </div>
                </div>
            </div>
        </div>
    )
}

export default PreviewPane
