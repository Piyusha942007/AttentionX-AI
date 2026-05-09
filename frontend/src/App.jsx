import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Sparkles, Play, Grid, Clock, Radio, User, Upload, CheckCircle2, Loader2, DownloadCloud, X, AlertCircle } from 'lucide-react'
import './index.css'

/* ─── Static Data ────────────────────────────────────────────────────────── */
const STEPS = [
  { name:"Transcribing audio", engine:"Whisper" },
  { name:"Detecting emotion peaks", engine:"Librosa" },
  { name:"Analyzing with Gemini", engine:"AI Analysis" },
  { name:"Rendering vertical clips", engine:"FFmpeg" },
]

const COLORS = [
    { name: 'Yellow', hex: '#FFE234' },
    { name: 'Green', hex: '#00FF00' },
    { name: 'Cyan', hex: '#00FFFF' },
    { name: 'Pink', hex: '#FF00FF' },
]

/* ─── Styles ─────────────────────────────────────────────────────────────── */
const S = {
  shell: { display:'grid', gridTemplateColumns:'64px 340px 1fr 300px', gridTemplateRows:'60px 1fr 48px', height:'100vh', width:'100vw' },
  topBar: { gridColumn:'1/-1', gridRow:'1', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 24px', borderBottom:'1px solid var(--border-light)', background:'rgba(5, 5, 5, 0.8)', backdropFilter:'blur(12px)', zIndex:10 },
  sidebar: { gridColumn:'1', gridRow:'2', display:'flex', flexDirection:'column', alignItems:'center', padding:'20px 0', borderRight:'1px solid var(--border-light)', background:'var(--bg-base)' },
  bottomBar: { gridColumn:'1/-1', gridRow:'3', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 24px', background:'var(--bg-surface)', borderTop:'1px solid var(--border-light)', zIndex:10 },
  panel: (extra) => ({ gridRow:'2', display:'flex', flexDirection:'column', overflow:'hidden', borderRight:'1px solid var(--border-light)', background:'rgba(10, 10, 12, 0.4)', backdropFilter:'blur(8px)', ...extra }),

  row: { display:'flex', flexDirection:'row', alignItems:'center' },
  col: { display:'flex', flexDirection:'column' },
  badge: (bg, color) => ({ fontSize:11, fontWeight:600, padding:'4px 10px', borderRadius:99, background:bg, color, whiteSpace:'nowrap', letterSpacing:'0.02em' }),
  sectionLabel: { fontSize:11, fontWeight:700, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--text-muted)', padding:'24px 20px 12px', fontFamily:'"Outfit", sans-serif' },
  settingRow: { display:'flex', alignItems:'center', justifyContent:'space-between', height:44, padding:'0 20px', transition:'background 0.2s ease' },
}

/* ─── Toggle ─────────────────────────────────────────────────────────────── */
const Toggle = ({ on }) => (
  <div style={{ width:32, height:18, borderRadius:99, background: on ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)', position:'relative', flexShrink:0, transition:'background 0.2s ease', boxShadow: on ? '0 0 10px var(--accent-glow)' : 'none' }}>
    <div style={{ width:14, height:14, borderRadius:99, background:'#fff', position:'absolute', top:2, left: on ? 16 : 2, transition:'left 0.2s cubic-bezier(0.16, 1, 0.3, 1)' }} />
  </div>
)

/* ─── App ────────────────────────────────────────────────────────────────── */
export default function App() {
  const [job, setJob] = useState(null)
  const [sel, setSel] = useState(null)
  const [tab, setTab] = useState('file')
  const [file, setFile] = useState(null)
  const [ytUrl, setYtUrl] = useState('')
  const [captionColor, setCaptionColor] = useState('Yellow')
  const [selectedColor, setSelectedColor] = useState(COLORS[0])
  const [uploading, setUploading] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState(null)
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

  // Polling logic
  useEffect(() => {
    let timer
    const isProcessing = job && !['done', 'failed'].includes(job.status)
    if (isProcessing) {
      timer = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/jobs/${job.job_id}`)
          if (res.ok) {
            const data = await res.json()
            setJob(data)
            if (data.status === 'done') {
                if (data.peaks && data.peaks.length > 0) {
                    setSel(data.peaks[0])
                }
            }
          }
        } catch (err) { console.error('Polling error:', err) }
      }, 3000)
    }
    return () => clearInterval(timer)
  }, [job])

  // Dropzone setup
  const onDrop = useCallback((acceptedFiles) => {
    setFile(acceptedFiles[0])
    setError(null)
  }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ['.mp4', '.mov', '.mkv'] },
    multiple: false,
    disabled: uploading || (job && !['done', 'failed'].includes(job.status))
  })

  /* ─── Actions ──────────────────────────────────────────────────────────── */
  const handleUpload = async () => {
    if (!file) return
    setUploading(true); setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('caption_color', captionColor)
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: formData })
      if (res.ok) { setJob(await res.json()) } else { setError('Upload failed') }
    } catch { setError('Connection error') } finally { setUploading(false) }
  }

  const handleUrlSubmit = async () => {
    if (!ytUrl) return
    setUploading(true); setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/jobs/youtube`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: ytUrl, caption_color: captionColor }) })
      if (res.ok) { setJob(await res.json()) } else { setError('URL processing failed') }
    } catch { setError('Connection error') } finally { setUploading(false) }
  }

  const loadMockDemo = async () => {
    setUploading(true); setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/jobs/mock/demo`)
      if (res.ok) { 
        const data = await res.json()
        setJob(data)
        if (data.peaks?.length > 0) setSel(data.peaks[0])
      }
    } catch { setError('Failed to load demo setup') } finally { setUploading(false) }
  }

  const handleExport = async () => {
    if (!job?.job_id || !sel?.clip_id) return
    setIsExporting(true)
    try {
      const res = await fetch(`${API_BASE}/api/clips/${job.job_id}/${sel.clip_id}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caption_color: selectedColor.name })
      })
      if (res.ok) {
        const data = await res.json()
        window.open(data.download_url, '_blank')
      } else {
        setError('Export failed')
      }
    } catch {
      setError('Connection error')
    } finally {
      setIsExporting(false)
    }
  }

  const resetAll = () => { setJob(null); setSel(null); setFile(null); setYtUrl(''); setError(null) }

  /* ─── Derived State / Helpers ────────────────────────────────────────────── */
  const isProcessing = uploading || (job && !['done', 'failed'].includes(job.status))
  const isDone = job && job.status === 'done'
  const NUGGETS = job?.peaks || []

  const getJobProgress = () => {
      if (uploading || job?.status === 'downloading') return { step: 1, prog: 20 }
      if (job?.status === 'transcribing') return { step: 1, prog: 50 }
      if (job?.status === 'analyzing') return { step: 2, prog: 70 }
      if (job?.status === 'cropping') return { step: 3, prog: 90 }
      if (job?.status === 'done') return { step: 4, prog: 100 }
      return { step: 0, prog: 0 }
  }
  const { step, prog } = getJobProgress()

  const generateBars = () => {
    // If real demo or job is done and has peaks, map them
    const bars = []
    const totalDuration = job?.duration || 3600 // fallback
    for (let i = 0; i < 80; i++) {
        const pct = (i / 80) * 100
        let h = 12 + Math.random() * 18
        let c = '#27272a'
        let matchedPeak = null

        if (NUGGETS.length > 0) {
            NUGGETS.forEach((n, idx) => {
                const peakPct = (n.time / totalDuration) * 100
                // Match bar to peak if within 4% distance
                if (Math.abs(pct - peakPct) < 4) {
                    h = 55 + Math.random() * 45
                    c = idx === 0 ? '#7F77DD' : idx === 1 ? '#EF9F27' : '#5DCAA5'
                    matchedPeak = n
                }
            })
        }
        bars.push({ h, c, matchedPeak })
    }
    return bars
  }
  const bars = useMemo(generateBars, [job])

  const getPeakColor = (idx) => idx === 0 ? '#7F77DD' : idx === 1 ? '#EF9F27' : '#5DCAA5'
  const getCatPill = (idx) => {
      if (idx===0) return { bg: '#26215C', c: '#AFA9EC' }
      if (idx===1) return { bg: '#412402', c: '#FAC775' }
      return { bg: '#173404', c: '#97C459' }
  }

  return (
    <div style={S.shell}>
      {/* ═══ TOP BAR ═══ */}
      <header style={S.topBar}>
        <div style={{ ...S.row, gap:10 }}>
          <div style={{ width:26, height:26, background:'#534AB7', borderRadius:6, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <Sparkles size={14} color="#fff" />
          </div>
          <span style={{ fontSize:14, fontWeight:500 }}>AttentionX</span>
          <span style={{ fontSize:11, color:'#52525b' }}>MVP 1.0</span>
        </div>
        {!job ? (
          <button onClick={loadMockDemo} disabled={uploading} style={{ ...S.row, gap:6, background:'#534AB7', color:'#fff', fontSize:12, fontWeight:500, padding:'0 14px', height:32, borderRadius:6, opacity: uploading ? 0.5 : 1 }}>
            {uploading ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} fill="#fff" />} Try demo mode
          </button>
        ) : (
          <button onClick={resetAll} style={{ ...S.row, gap:6, background:'transparent', border:'0.5px solid #27272a', color:'#a1a1aa', fontSize:12, fontWeight:500, padding:'0 14px', height:32, borderRadius:6 }}>
            <X size={12} /> New Project
          </button>
        )}
      </header>

      {/* ═══ SIDEBAR ═══ */}
      <aside style={S.sidebar}>
        {[Grid, Clock, Radio].map((Ic, i) => (
          <div key={i} style={{ width:36, height:36, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center', background: i===0 ? '#1c1c1f' : 'transparent', marginBottom:4 }}>
            <Ic size={18} stroke={i===0 ? '#a1a1aa' : '#52525b'} strokeWidth={1.5} fill="none" />
          </div>
        ))}
        <div style={{ marginTop:'auto', width:36, height:36, borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center' }}>
          <User size={18} stroke="#52525b" strokeWidth={1.5} fill="none" />
        </div>
      </aside>

      {/* ═══ LEFT PANEL ═══ */}
      <div style={S.panel({ width:320, overflowY:'auto' })}>
        <div style={S.sectionLabel}>Source material</div>

        <div style={{ display:'flex', gap:4, margin:'0 16px 12px', padding:4, background:'#0d0d0f', borderRadius:8 }}>
          {['file','url'].map(t => (
            <button key={t} onClick={() => setTab(t)} disabled={job || uploading} style={{ flex:1, textAlign:'center', fontSize:11, fontWeight:500, padding:'6px 0', borderRadius:6, background: tab===t ? '#1c1c1f' : 'transparent', border: tab===t ? '0.5px solid #3f3f46' : '0.5px solid transparent', color: tab===t ? '#a1a1aa' : '#52525b', transition:'all 120ms ease', opacity: (job||uploading) ? 0.5 : 1 }}>
              {t === 'file' ? 'Local file' : 'YouTube link'}
            </button>
          ))}
        </div>

        {tab === 'file' ? (
             <div 
                {...getRootProps()} 
                style={{ margin:'0 16px', border: isDragActive ? '1px dashed #5DCAA5' : '0.5px dashed #3f3f46', borderRadius:10, padding:24, display:'flex', flexDirection:'column', alignItems:'center', gap:6, cursor: (job || uploading) ? 'not-allowed' : 'pointer', background: isDragActive ? '#04342C' : 'transparent' }}
             >
                <input {...getInputProps()} />
                <div style={{ width:36, height:36, background:'#1c1c1f', borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center' }}>
                    <Upload size={16} color="#a1a1aa" />
                </div>
                <span style={{ fontSize:13, fontWeight:500, color:'#a1a1aa', textAlign:'center' }}>{file ? file.name : (job ? job.filename : 'Drop your video here')}</span>
                {!file && !job && <span style={{ fontSize:11, color:'#52525b' }}>MP4, MOV, WebM up to 4GB</span>}
             </div>
        ) : (
             <div style={{ margin:'0 16px', display:'flex', flexDirection:'column', gap:8 }}>
                <input 
                    type="url" 
                    placeholder="Paste YouTube link here..."
                    value={ytUrl}
                    onChange={e => setYtUrl(e.target.value)}
                    onKeyDown={e => { if(e.key === 'Enter') handleUrlSubmit() }}
                    disabled={job || uploading}
                    style={{ background:'#161618', border:'0.5px solid #27272a', padding:'12px 14px', borderRadius:8, color:'#fafafa', fontSize:12, outline:'none' }}
                />
             </div>
        )}

        {error && (
            <div style={{ margin:'12px 16px 0', padding:'10px 12px', background:'#4A1B0C', border:'0.5px solid #F0997B', borderRadius:8, color:'#F0997B', fontSize:10, fontWeight:500, display:'flex', alignItems:'center', gap:8 }}>
                <AlertCircle size={14} /> {error}
            </div>
        )}

        {!job && (file || ytUrl) && !uploading && (
             <button onClick={tab === 'file' ? handleUpload : handleUrlSubmit} style={{ margin:'12px 16px 0', background:'#534AB7', color:'#fff', height:38, borderRadius:8, fontSize:11, fontWeight:500 }}>
                 START MINING NUGGETS
             </button>
        )}

        <div style={S.sectionLabel}>Analysis settings</div>
        {[
          { l:"Clip duration", v:"45–60 sec", bg:'#26215C', c:'#AFA9EC' },
          { l:"Peak detection", v:"Gemini + Librosa", bg:'#173404', c:'#97C459' },
          { l:"Face tracking", toggle:true },
          { l:"Karaoke captions", toggle:true },
          { l:"Caption color", select:true },
          { l:"Hook headline", toggle:true },
          { l:"Output format", v:"9:16 TikTok", bg:'#412402', c:'#FAC775' },
        ].map((s,i) => (
          <div key={i} style={S.settingRow}>
            <span style={{ fontSize:12, color:'#71717a' }}>{s.l}</span>
            {s.toggle ? <Toggle on /> : s.select ? (
                <select value={captionColor} onChange={e => setCaptionColor(e.target.value)} disabled={job || uploading} style={{ background:'#18181b', color:'#a1a1aa', border:'0.5px solid #27272a', borderRadius:6, padding:'2px 6px', fontSize:11, outline:'none' }}>
                    <option value="Yellow">Yellow</option>
                    <option value="Green">Green</option>
                    <option value="Cyan">Cyan</option>
                    <option value="Pink">Neon Pink</option>
                </select>
            ) : <span style={S.badge(s.bg, s.c)}>{s.v}</span>}
          </div>
        ))}
      </div>

      {/* ═══ CENTER PANEL ═══ */}
      <div style={S.panel({ flex:1 })}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', height:44, padding:'0 16px', borderBottom:'0.5px solid #18181b', flexShrink:0 }}>
          <span style={{ fontSize:12, fontWeight:500, color:'#a1a1aa' }}>Emotional peak timeline</span>
          {isDone && (
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              <div style={{ width:6, height:6, borderRadius:99, background:'#639922', animation:'pulse 2s infinite' }} />
              <span style={{ fontSize:10, color:'#71717a' }}>{NUGGETS.length} golden nuggets detected</span>
            </div>
          )}
        </div>

        <div style={{ flex:1, padding:16, overflowY:'auto', display:'flex', flexDirection:'column', gap:12 }}>
          {isProcessing ? (
            /* Processing View */
            <div style={{ display:'flex', flexDirection:'column', gap:10, paddingTop:16 }}>
              {STEPS.map((st, i) => {
                const done = i+1 < step || (step===4 && prog>=100)
                const active = i+1 === step
                return (
                  <div key={i} style={{ 
                    display:'flex', 
                    alignItems:'center', 
                    justifyContent:'space-between', 
                    padding:'0 12px', 
                    height:40, 
                    background:'#0d0d0f', 
                    borderTop:'0.5px solid #27272a',
                    borderRight:'0.5px solid #27272a',
                    borderBottom:'0.5px solid #27272a',
                    borderRadius:8, 
                    borderLeft: active ? '2px solid #7F77DD' : '0.5px solid #27272a' 
                  }}>
                    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                      {done ? <CheckCircle2 size={14} color="#639922" /> : <Loader2 size={14} color={active ? '#EF9F27' : '#52525b'} style={active ? { animation:'spin 1s linear infinite' } : {}} />}
                      <span style={{ fontSize:12, color: done ? '#fafafa' : '#a1a1aa' }}>{st.name}</span>
                    </div>
                    <span style={S.badge(done ? '#173404' : active ? '#412402' : '#161618', done ? '#97C459' : active ? '#FAC775' : '#52525b')}>
                      {done ? 'Done' : active ? st.engine : 'Queued'}
                    </span>
                  </div>
                )
              })}
              <div style={{ height:4, background:'#1c1c1f', borderRadius:4, overflow:'hidden', marginTop:8 }}>
                <div style={{ height:'100%', background:'#534AB7', width:`${prog}%`, transition:'width 300ms ease', borderRadius:4 }} />
              </div>
              <p style={{ textAlign:'center', marginTop:12, fontSize:10, color:'#71717a', letterSpacing:'0.05em' }}>JOB ID: {job?.job_id || 'Generating...'}</p>
            </div>
          ) : (
            /* Timeline + Nuggets View */
            <>
              {/* Waveform */}
              <div style={{ background:'#0d0d0f', borderRadius:8, height:72, padding:'6px 8px', display:'flex', alignItems:'flex-end', gap:1, position:'relative', flexShrink:0 }}>
                {bars.map((b, i) => (
                  <div key={i} style={{ flex:1, height:`${b.h}%`, background:b.c, borderRadius:'2px 2px 0 0', opacity: 0.45 + (b.h/100)*0.55, cursor: b.matchedPeak ? 'pointer' : 'default', transition:'opacity 120ms' }}
                    onClick={() => { if (b.matchedPeak) setSel(b.matchedPeak) }}
                    onMouseEnter={e => e.target.style.opacity='1'}
                    onMouseLeave={e => e.target.style.opacity = String(0.45 + (b.h/100)*0.55)}
                  />
                ))}
                
                {/* Visual Peak Overlays */}
                {isDone && NUGGETS.map((n, idx) => {
                    const peakPct = (n.time / (job?.duration || 3600)) * 100
                    const c = getPeakColor(idx)
                    return (
                        <div key={n.headline} style={{ position:'absolute', left:`${peakPct}%`, top:0, bottom:0, width: sel?.headline===n.headline ? 3 : 1.5, background: c, transition:'width 150ms', pointerEvents:'none' }}>
                            <span style={{ position:'absolute', top:-14, left:-12, fontSize:8, color: c, fontWeight:500, whiteSpace:'nowrap' }}>Peak {idx+1}</span>
                        </div>
                    )
                })}
              </div>

              <div style={{ display:'flex', justifyContent:'space-between', padding:'0 4px' }}>
                {['0:00','15:00','30:00','45:00','60:00'].map(t => <span key={t} style={{ fontSize:9, color:'#3f3f46' }}>{t}</span>)}
              </div>

              {/* Stat Cards */}
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:6 }}>
                {[
                  { v: isDone ? NUGGETS.length : '—', l:'Nuggets found' },
                  { v: isDone && NUGGETS.length>0 ? `${Math.round(NUGGETS[0].score*100)}%` : '—', l:'Top virality score' },
                  { v: isDone ? (() => {
                      const totalSecs = NUGGETS.reduce((acc, n) => acc + (n.end - n.start), 0)
                      return `${Math.floor(totalSecs/60)}:${(totalSecs%60).toFixed(0).padStart(2,'0')}`
                  })() : '—', l:'Total clip time' },
                ].map((c,i) => (
                  <div key={i} style={{ background:'#0d0d0f', border:'0.5px solid #1c1c1f', borderRadius:8, padding:10 }}>
                    <div style={{ fontSize:18, fontWeight:500 }}>{c.v}</div>
                    <div style={{ fontSize:10, color:'#52525b', marginTop:2 }}>{c.l}</div>
                  </div>
                ))}
              </div>

              {/* Nugget Cards */}
              <div style={{ display:'flex', flexDirection:'column', gap:8, flex:1, overflowY:'auto' }}>
                {isDone ? NUGGETS.map((n, idx) => {
                   const color = getPeakColor(idx)
                   const pill = getCatPill(idx)
                   return (
                  <div key={idx} onClick={() => setSel(n)} style={{ display:'flex', gap:14, padding:12, background:'#0d0d0f', border: sel?.headline===n.headline ? `1px solid ${color}` : '0.5px solid #1c1c1f', borderRadius:10, cursor:'pointer', transition:'border-color 150ms' }}>
                    <div style={{ width:44, display:'flex', flexDirection:'column', alignItems:'center', flexShrink:0 }}>
                      <span style={{ fontSize:18, fontWeight:500, color: color }}>{Math.round(n.score * 100)}%</span>
                      <span style={{ fontSize:9, color:'#52525b' }}>Virality</span>
                    </div>
                    <div style={{ display:'flex', flexDirection:'column', gap:6, flex:1, minWidth:0 }}>
                      <span style={{ fontSize:13, fontWeight:500, color:'#d4d4d8', lineHeight:'1.4' }}>{n.headline || n.clip_title}</span>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <span style={S.badge(pill.bg, pill.c)}>{n.reason || 'Peak'}</span>
                        <span style={{ fontSize:10, fontFamily:'monospace', color:'#52525b' }}>{Math.floor(n.time/60)}:{(n.time % 60).toFixed(0).padStart(2,'0')}</span>
                      </div>
                    </div>
                  </div>
                )}) : (
                  <div style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:10, border:'0.5px dashed #27272a', borderRadius:10, minHeight:120 }}>
                    <Radio size={22} color="#27272a" />
                    <span style={{ fontSize:10, color:'#3f3f46', letterSpacing:'0.08em', textTransform:'uppercase' }}>Process a video to find nuggets</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ═══ RIGHT PANEL ═══ */}
      <div style={{ ...S.panel({}), width:280, borderRight:'none' }}>
        <div style={S.sectionLabel}>Clip preview</div>
        <div style={{ padding:'0 16px', display:'flex', flexDirection:'column', gap:16, flex:1 }}>

          {/* Preview Pair */}
          <div style={{ display:'flex', flexDirection:'column', gap:16, width:'100%', flex:1 }}>
            {/* 16:9 Source */}
            <div style={{ width:'100%', aspectRatio:'16/9', background:'#0d0d0f', border:'0.5px solid #1c1c1f', borderRadius:8, position:'relative', overflow:'hidden', flexShrink:0 }}>
              <div style={{ position:'absolute', left:'25%', top:0, bottom:0, width:'38%', background:'rgba(127,119,221,0.1)', borderLeft:'1px solid #7F77DD', borderRight:'1px solid #7F77DD', zIndex:10 }} />
              
              {sel?.clip_url ? (
                  <video src={sel.clip_url} autoPlay loop muted playsInline style={{ width:'100%', height:'100%', objectFit:'cover', opacity:0.6 }} />
              ) : null}

              <span style={{ position:'absolute', bottom:4, left:6, zIndex:20, fontSize:8, color:'#52525b', background:'#18181b', padding:'1px 5px', borderRadius:4 }}>Source 16:9</span>
            </div>
            
            {/* 9:16 Output */}
            <div style={{ flex: 1, display:'flex', justifyContent:'center', paddingBottom: 16, overflow:'hidden' }}>
              <div style={{ height:'100%', aspectRatio:'9/16', background:'#0d0d0f', border:'0.5px solid #1c1c1f', borderRadius:8, position:'relative', overflow:'hidden', display:'flex', alignItems:'center', justifyContent:'center' }}>
                
                {sel?.clip_url ? (
                    <video key={sel.clip_url} src={sel.clip_url} autoPlay loop muted playsInline style={{ position:'absolute', top:0, left:0, width:'100%', height:'100%', objectFit:'cover', zIndex:5 }} />
                ) : null}

                {/* Live Captions Overlay */}
                {sel?.words && (
                  <div style={{ position:'absolute', bottom:'20%', left:0, right:0, padding:'0 10px', display:'flex', flexWrap:'wrap', justifyContent:'center', gap:4, zIndex:10, pointerEvents:'none' }}>
                    {sel.words.map((w, idx) => {
                      const video = document.querySelector('video')
                      const currentTime = video?.currentTime || 0
                      const active = currentTime >= (w.start - sel.start) && currentTime <= (w.end - sel.start)
                      return (
                        <span key={idx} style={{ 
                          fontSize: active ? 14 : 12, 
                          fontWeight: 900, 
                          color: active ? selectedColor.hex : 'rgba(255,255,255,0.6)',
                          textTransform: 'uppercase',
                          textShadow: '0 2px 4px rgba(0,0,0,0.8)',
                          transform: active ? 'scale(1.1)' : 'scale(1)',
                          transition: 'all 0.1s ease'
                        }}>
                          {w.word}
                        </span>
                      )
                    })}
                  </div>
                )}

                <span style={{ position:'absolute', bottom:4, left:4, zIndex:20, fontSize:7, color:'#52525b', background:'#18181b', padding:'1px 4px', borderRadius:3 }}>9:16 Output</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop:'auto' }}>
            <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:16 }}>
              <span style={{ fontSize:10, color:'#52525b', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.05em' }}>Caption Style</span>
              <div style={{ display:'flex', gap:8 }}>
                {COLORS.map(c => (
                  <button 
                    key={c.name}
                    onClick={() => { setSelectedColor(c); setCaptionColor(c.name) }}
                    style={{ 
                      width:24, height:24, borderRadius:99, background:c.hex, 
                      border: selectedColor.name === c.name ? '2px solid #fff' : '2px solid transparent',
                      boxShadow: selectedColor.name === c.name ? '0 0 10px ' + c.hex : 'none',
                      transition: 'all 0.2s ease'
                    }}
                  />
                ))}
              </div>
            </div>

            <button onClick={handleExport} style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:8, width:'100%', height:40, background: isDone ? '#534AB7' : '#1c1c1f', color: isDone ? '#fff' : '#52525b', fontSize:13, fontWeight:500, borderRadius:8, transition:'all 200ms', cursor: isDone ? 'pointer' : 'not-allowed' }}
                disabled={!isDone || isExporting}>
                {isExporting ? <Loader2 size={16} className="animate-spin" /> : <DownloadCloud size={16} />} 
                {isExporting ? 'Exporting...' : 'Export Final Clip'}
            </button>
          </div>
        </div>
      </div>

      {/* ═══ BOTTOM BAR ═══ */}
      <footer style={S.bottomBar}>
        <div style={{ display:'flex', alignItems:'center', gap:20 }}>
          {[
            { l:'GPU Acceleration', v:'ENABLED', c:'#639922' },
            { l:'Librosa Audio Analysis', v: isProcessing ? 'POLLING' : isDone ? 'READY' : 'IDLE', c: isProcessing ? '#EF9F27' : isDone ? '#639922' : '#52525b' },
            { l:'FastAPI Backend', v: job ? 'CONNECTED' : 'STANDBY', c: job ? '#639922' : '#52525b' },
          ].map((s,i) => (
            <div key={i} style={{ display:'flex', alignItems:'center', gap:6, fontSize:10, color:'#52525b' }}>
              <div style={{ width:5, height:5, borderRadius:99, background:s.c, flexShrink:0 }} />
              <span>{s.l}: <span style={{ color:'#71717a' }}>{s.v}</span></span>
            </div>
          ))}
        </div>
        <span style={{ fontSize:10, color:'#3f3f46' }}>{new Date().toLocaleTimeString()}</span>
      </footer>
    </div>
  )
}
