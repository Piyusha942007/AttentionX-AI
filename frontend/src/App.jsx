import React, { useState, useEffect, useRef } from 'react'
import { 
  Grid, History, Radio, User, Upload, Youtube, 
  Link as LinkIcon, Sparkles, Scissors, Play, 
  CheckCircle2, Loader2, DownloadCloud, X 
} from 'lucide-react'
import './index.css'

// ─── Example Data ───
const MOCK_NUGGETS = [
  { id: 1, score: 91, headline: "The only metric that actually predicts startup success", category: "Profound insight", time: "14:22–15:08", peakX: 22, color: "var(--brand-purple)" },
  { id: 2, score: 78, headline: "I was rejected by 47 investors. Here's what changed everything", category: "Personal story", time: "30:41–31:29", peakX: 51, color: "var(--accent-amber)" },
  { id: 3, score: 64, headline: "Most founders skip this step and lose 6 months", category: "Actionable tip", time: "47:03–47:55", peakX: 78, color: "var(--accent-teal)" }
]

const PROCESSING_STEPS = [
  { id: 1, name: "Transcribing audio", engine: "Whisper" },
  { id: 2, name: "Detecting emotion peaks", engine: "Librosa" },
  { id: 3, name: "Analyzing with Gemini", engine: "AI Analysis" },
  { id: 4, name: "Rendering vertical clips", engine: "MoviePy" }
]

const App = () => {
  const [isDemoMode, setIsDemoMode] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [selectedNugget, setSelectedNugget] = useState(null)
  const [currentTime, setCurrentTime] = useState("14:22")
  const [uploadMode, setUploadMode] = useState('file') // 'file' | 'url'
  const [file, setFile] = useState(null)

  // Simulation logic for Demo Mode
  useEffect(() => {
    if (isDemoMode) {
      setIsProcessing(true)
      setCurrentStep(0)
      setProgress(0)
      setSelectedNugget(null)

      let p = 0
      const interval = setInterval(() => {
        p += 2
        setProgress(p)
        
        if (p < 25) setCurrentStep(1)
        else if (p < 50) setCurrentStep(2)
        else if (p < 75) setCurrentStep(3)
        else if (p < 100) setCurrentStep(4)

        if (p >= 100) {
          clearInterval(interval)
          setTimeout(() => {
            setIsProcessing(false)
            setSelectedNugget(MOCK_NUGGETS[0])
          }, 500)
        }
      }, 60)
      return () => clearInterval(interval)
    }
  }, [isDemoMode])

  // ─── Waveform Generator ───
  const renderWaveform = () => {
    const bars = []
    for (let i = 0; i < 80; i++) {
        let height = Math.floor(Math.random() * 15) + 15
        let color = '#27272a'
        
        // Peak Clusters
        const isPeak1 = i >= 15 && i <= 22
        const isPeak2 = i >= 38 && i <= 45
        const isPeak3 = i >= 60 && i <= 67

        if (isPeak1) { height = Math.floor(Math.random() * 30) + 70; color = 'var(--brand-purple)' }
        if (isPeak2) { height = Math.floor(Math.random() * 30) + 70; color = 'var(--accent-amber)' }
        if (isPeak3) { height = Math.floor(Math.random() * 30) + 70; color = 'var(--accent-teal)' }

        bars.push(
          <div 
            key={i} 
            className="waveform-bar"
            style={{ 
              height: `${height}%`, 
              backgroundColor: color,
              opacity: 0.5 + ((height / 100) * 0.5)
            }}
            onClick={() => {
                if (!isProcessing) {
                    if (isPeak1) setSelectedNugget(MOCK_NUGGETS[0])
                    else if (isPeak2) setSelectedNugget(MOCK_NUGGETS[1])
                    else if (isPeak3) setSelectedNugget(MOCK_NUGGETS[2])
                }
            }}
          />
        )
    }
    return bars
  }

  return (
    <div className="obsidian-shell">
      {/* ─── Top Bar ─── */}
      <header className="top-bar">
        <div className="flex items-center gap-3">
          <div style={{ width: 26, height: 26, background: 'var(--brand-purple)', borderRadius: 6 }} className="flex">
            <Sparkles size={16} color="white" strokeWidth={2} />
          </div>
          <span style={{ fontSize: 14, fontWeight: 500 }}>AttentionX</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>MVP 1.0</span>
        </div>
        <button 
          className="btn" 
          style={{ background: '#534AB7', color: 'white', fontSize: 12, padding: '0 12px', height: 32, borderRadius: 6 }}
          onClick={() => setIsDemoMode(true)}
        >
          <Play size={12} fill="white" className="mr-2" /> Try demo mode
        </button>
      </header>

      {/* ─── Sidebar ─── */}
      <aside className="sidebar">
        {[Grid, History, Radio, User].map((Icon, i) => (
          <div 
            key={i} 
            style={{ 
               width: 36, height: 36, borderRadius: 8, marginTop: Icon === User ? 'auto' : 8,
               background: i === 0 ? 'var(--bg-active)' : 'transparent'
            }}
            className="flex items-center justify-center cursor-pointer"
          >
            <Icon size={18} stroke={i === 0 ? '#a1a1aa' : '#52525b'} strokeWidth={1.5} />
          </div>
        ))}
      </aside>

      {/* ─── Left Panel: Source & Settings ─── */}
      <main className="panel" style={{ width: 320 }}>
        <div className="section-label">Source material</div>
        
        <div className="px-4 pb-4">
          <div className="flex gap-1 p-1 bg-surface border-std rounded-xl mb-4" style={{ background: '#0d0d0f' }}>
            {['Local file', 'YouTube link'].map((t, i) => (
                <button 
                  key={t}
                  className="flex-1 py-1.5 rounded-lg text-[11px] font-medium"
                  style={{ 
                    background: (i === 0 && uploadMode === 'file') || (i === 1 && uploadMode === 'url') ? '#1c1c1f' : 'transparent',
                    border: (i === 0 && uploadMode === 'file') || (i === 1 && uploadMode === 'url') ? '0.5px solid #3f3f46' : '0.5px solid transparent',
                    color: (i === 0 && uploadMode === 'file') || (i === 1 && uploadMode === 'url') ? '#a1a1aa' : '#71717a'
                  }}
                  onClick={() => setUploadMode(i === 0 ? 'file' : 'url')}
                >
                  {t}
                </button>
            ))}
          </div>

          {!file && !isDemoMode ? (
            <div className="flex flex-col items-center justify-center p-6 border-std rounded-xl" style={{ borderStyle: 'dashed', borderColor: '#3f3f46' }}>
                <div style={{ width: 32, height: 32, background: '#1c1c1f', borderRadius: 8 }} className="flex mb-3">
                    <Upload size={16} color="#a1a1aa" />
                </div>
                <span style={{ fontSize: 13, fontWeight: 500, color: '#a1a1aa' }}>Drop your video here</span>
                <span style={{ fontSize: 11, color: '#52525b', marginTop: 4 }}>MP4, MOV, WebM up to 4GB</span>
            </div>
          ) : (
            <div className="flex items-center justify-between p-3 bg-active border-std rounded-lg">
                <div className="flex items-center gap-3 overflow-hidden">
                    <Sparkles size={14} color="var(--brand-purple)" />
                    <span className="text-[12px] font-medium truncate">{file?.name || "viral_marketing_workshop.mp4"}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="badge" style={{ background: '#27272a', color: '#a1a1aa' }}>08:14</span>
                    <button onClick={() => {setFile(null); setIsDemoMode(false); setIsProcessing(false)}}><X size={14} color="#52525b" /></button>
                </div>
            </div>
          )}
        </div>

        <div className="section-label">Analysis settings</div>
        <div className="px-4">
            {[
                { l: "Clip duration", v: "45–60 sec", color: "var(--brand-purple)" },
                { l: "Peak detection", v: "Gemini + Librosa", color: "var(--accent-green)" },
                { l: "Face tracking", v: "toggle", on: true },
                { l: "Karaoke captions", v: "toggle", on: true },
                { l: "Hook headline", v: "toggle", on: true },
                { l: "Output format", v: "9:16 TikTok", color: "var(--accent-amber)" }
            ].map((s, i) => (
                <div key={i} className="flex items-center justify-between h-9 border-b border-dim" style={{ borderColor: '#18181b' }}>
                    <span style={{ fontSize: 12, color: '#71717a' }}>{s.l}</span>
                    {s.v === 'toggle' ? (
                        <div className={`toggle-track ${s.on ? 'toggle-on' : ''}`} style={{ width: 28, height: 16, borderRadius: 99, background: s.on ? 'var(--brand-purple)' : '#161618', position: 'relative' }}>
                            <div style={{ width: 12, height: 12, background: 'white', borderRadius: 99, position: 'absolute', top: 2, left: s.on ? 14 : 2, transition: 'all 150ms ease' }} />
                        </div>
                    ) : (
                        <span className="badge" style={{ 
                            background: s.l === "Clip duration" ? 'var(--brand-purple-bg)' : 
                                        s.l === "Peak detection" ? 'var(--accent-green-bg)' : 'var(--accent-amber-bg)',
                            color:      s.l === "Clip duration" ? 'var(--brand-purple-text)' : 
                                        s.l === "Peak detection" ? 'var(--accent-green-text)' : 'var(--accent-amber-text)'
                        }}>
                            {s.v}
                        </span>
                    )}
                </div>
            ))}
        </div>
      </main>

      {/* ─── Center Panel: Timeline & Nuggets ─── */}
      <main className="panel flex-1">
        <div className="flex items-center justify-between h-[44px] px-4 border-b border-dim" style={{ borderColor: '#18181b' }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: '#a1a1aa' }}>Emotional peak timeline</span>
            {isDemoMode && !isProcessing && (
                <div className="flex items-center gap-2">
                    <div className="pulse-dot" />
                    <span style={{ fontSize: 10, color: '#71717a' }}>3 golden nuggets detected</span>
                </div>
            )}
        </div>

        <div className="p-4">
            {isProcessing ? (
                <div className="flex flex-col gap-3 py-6 animate-fade-in">
                    {PROCESSING_STEPS.map((step, i) => {
                        const isDone = i + 1 < currentStep || (currentStep === 4 && progress === 100)
                        const isActive = i + 1 === currentStep
                        return (
                            <div key={i} className="flex items-center justify-between px-3 h-10 card" style={{ borderLeft: isActive ? '2px solid var(--brand-purple)' : '0.5px solid #27272a' }}>
                                <div className="flex items-center gap-3">
                                    {isDone ? <CheckCircle2 size={14} color="var(--accent-green)" /> : <Loader2 size={14} color={isActive ? "var(--accent-amber)" : "#52525b"} className={isActive ? "animate-spin" : ""} />}
                                    <span style={{ fontSize: 12, color: isDone ? '#fafafa' : '#a1a1aa' }}>{step.name}</span>
                                </div>
                                <span className="badge" style={{ background: isDone ? 'var(--accent-green-bg)' : isActive ? 'var(--accent-amber-bg)' : '#161618', color: isDone ? 'var(--accent-green-text)' : isActive ? 'var(--accent-amber-text)' : '#52525b' }}>
                                    {isDone ? "Done" : isActive ? step.engine : "Queued"}
                                </span>
                            </div>
                        )
                    })}
                    <div style={{ height: 4, background: '#1c1c1f', borderRadius: 4, marginTop: 12, overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: 'var(--brand-purple)', width: `${progress}%`, transition: 'width 150ms ease' }} />
                    </div>
                </div>
            ) : (
                <>
                    <div className="waveform-container relative mb-2">
                        {renderWaveform()}
                        {/* Peak Overlays */}
                        {isDemoMode && MOCK_NUGGETS.map(n => (
                            <div 
                              key={n.id}
                              style={{ 
                                position: 'absolute', left: `${n.peakX}%`, top: 0, bottom: 0, width: selectedNugget?.id === n.id ? 4 : 2, 
                                backgroundColor: n.id === 1 ? '#7F77DD' : n.id === 2 ? '#EF9F27' : '#5DCAA5',
                                transition: 'width 150ms ease'
                              }}
                            >
                                <span style={{ position: 'absolute', top: -16, left: -10, fontSize: 9, color: n.id === 1 ? '#7F77DD' : n.id === 2 ? '#EF9F27' : '#5DCAA5', fontWeight: 500 }}>Peak {n.id}</span>
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between mb-6">
                        {["0:00", "15:00", "30:00", "45:00", "60:00"].map(t => <span key={t} style={{ fontSize: 9, color: '#3f3f46' }}>{t}</span>)}
                    </div>

                    <div className="grid grid-cols-3 gap-1.5 mb-6">
                        {[
                          { l: "Nuggets found", v: isDemoMode ? "3" : "0" },
                          { l: "Top virality score", v: isDemoMode ? "91%" : "-" },
                          { l: "Total clip time", v: isDemoMode ? "2:47" : "-" }
                        ].map((s, i) => (
                          <div key={i} className="card p-3">
                            <div style={{ fontSize: 18, fontWeight: 500, color: '#fafafa' }}>{s.v}</div>
                            <div style={{ fontSize: 10, color: '#52525b', marginTop: 2 }}>{s.l}</div>
                          </div>
                        ))}
                    </div>

                    <div className="flex flex-col gap-2">
                        {isDemoMode ? MOCK_NUGGETS.map(n => (
                            <div 
                                key={n.id} 
                                className="card flex gap-4 p-3 cursor-pointer"
                                style={{ borderColor: selectedNugget?.id === n.id ? 'var(--brand-purple)' : 'var(--border-std)' }}
                                onClick={() => setSelectedNugget(n)}
                            >
                                <div style={{ width: 48 }} className="flex flex-col items-center">
                                    <span style={{ fontSize: 18, fontWeight: 500, color: n.color }}>{n.score}%</span>
                                    <span style={{ fontSize: 9, color: '#52525b', textAlign: 'center' }}>Virality score</span>
                                </div>
                                <div className="flex-1">
                                    <h4 style={{ fontSize: 13, fontWeight: 500, color: '#d4d4d8', lineHeight: 1.4 }}>{n.headline}</h4>
                                    <div className="flex items-center gap-3 mt-2">
                                        <span className="badge" style={{ 
                                            background: n.id === 1 ? 'var(--brand-purple-bg)' : n.id === 2 ? 'var(--accent-amber-bg)' : 'var(--accent-green-bg)',
                                            color:      n.id === 1 ? 'var(--brand-purple-text)' : n.id === 2 ? 'var(--accent-amber-text)' : 'var(--accent-green-text)'
                                        }}>
                                            {n.category}
                                        </span>
                                        <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#52525b' }}>{n.time}</span>
                                    </div>
                                </div>
                            </div>
                        )) : (
                           <div className="flex flex-col items-center justify-center py-12 border-std rounded-xl bg-surface border-dashed">
                               <Radio size={24} color="#1c1c1f" />
                               <span style={{ fontSize: 11, color: '#3f3f46', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Process video to find nuggets</span>
                           </div>
                        )}
                    </div>
                </>
            )}
        </div>
      </main>

      {/* ─── Right Panel: Preview & Export ─── */}
      <main className="panel" style={{ width: 280, borderRight: 'none' }}>
        <div className="section-label">Clip preview</div>
        <div className="px-4 flex flex-col gap-4">
            <div className="flex gap-2">
                <div className="flex-1 bg-surface border-std rounded-lg relative overflow-hidden" style={{ aspectRatio: '16/9' }}>
                    <div style={{ position: 'absolute', left: '25%', top: 0, bottom: 0, width: '38%', background: 'rgba(127, 119, 221, 0.12)', borderLeft: '1px solid var(--brand-purple)', borderRight: '1px solid var(--brand-purple)' }} />
                    <div className="badge" style={{ position: 'absolute', bottom: 4, left: 4, background: '#18181b', color: '#71717a', fontSize: 9 }}>Original 16:9</div>
                </div>
                <div style={{ width: 68, height: 120, background: '#0d0d0f', border: '0.5px solid #1c1c1f' }} className="rounded-lg relative overflow-hidden">
                    <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', background: 'rgba(0,0,0,0.7)', color: 'white', padding: '2px 4px', borderRadius: 4, fontSize: 8, whiteSpace: 'nowrap' }}>
                        the only metric that
                    </div>
                    <div className="badge" style={{ position: 'absolute', bottom: 4, left: 4, background: '#18181b', color: '#71717a', fontSize: 8 }}>9:16 Output</div>
                </div>
            </div>

            <div className="mt-4">
                {[
                    { l: "Burn captions", on: true },
                    { l: "Add hook title card", on: true }
                ].map((s, i) => (
                    <div key={i} className="flex items-center justify-between h-9 border-b border-dim" style={{ borderColor: '#18181b' }}>
                        <span style={{ fontSize: 12, color: '#71717a' }}>{s.l}</span>
                        <div className={`toggle-track ${s.on ? 'toggle-on' : ''}`} style={{ width: 28, height: 16, borderRadius: 99, background: s.on ? 'var(--brand-purple)' : '#161618', position: 'relative' }}>
                            <div style={{ width: 12, height: 12, background: 'white', borderRadius: 99, position: 'absolute', top: 2, left: s.on ? 14 : 2, transition: 'all 150ms ease' }} />
                        </div>
                    </div>
                ))}
            </div>

            <button 
              className="btn mt-2 w-full active:scale-[0.98]" 
              style={{ background: '#534AB7', color: 'white', height: 40, borderRadius: 8, fontSize: 13 }}
            >
                <DownloadCloud size={16} color="white" className="mr-2" /> Export clip
            </button>
        </div>
      </main>

      {/* ─── Bottom Bar ─── */}
      <footer className="bottom-bar">
        <div className="flex items-center gap-5">
            {[
                { l: "GPU Acceleration", v: "ENABLED", color: "#639922" },
                { l: "Librosa Audio Analysis", v: isDemoMode ? "READY" : "IDLE", color: isDemoMode ? "#639922" : "#52525b" },
                { l: "Whisper Transcription", v: isDemoMode ? "COMPLETE" : "IN PROGRESS", color: isDemoMode ? "#639922" : "#EF9F27" }
            ].map((s, i) => (
                <div key={i} className="flex items-center gap-2" style={{ fontSize: 10, color: '#52525b' }}>
                    <div style={{ width: 5, height: 5, borderRadius: 99, background: s.color }} />
                    <span>{s.l}: <span style={{ color: '#71717a' }}>{s.v}</span></span>
                </div>
            ))}
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 10, color: '#3f3f46' }}>{new Date().toLocaleTimeString()}</div>
      </footer>
    </div>
  )
}

export default App
