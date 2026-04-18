import React, { useState, useEffect } from 'react'
import UploadZone from '../components/UploadZone'
import PeakTimeline from '../components/PeakTimeline'
import ClipCard from '../components/ClipCard'
import PreviewPane from '../components/PreviewPane'
import { Sparkles, History, LayoutDashboard, Settings, LogOut, RotateCcw, Zap, Clock } from 'lucide-react'

const Dashboard = () => {
    const [job, setJob] = useState(null)
    const [selectedPeak, setSelectedPeak] = useState(null)
    const [isPolling, setIsPolling] = useState(false)

    // Polling logic for job status
    useEffect(() => {
        let timer
        if (isPolling && job?.job_id) {
            timer = setInterval(async () => {
                try {
                    const res = await fetch(`/api/jobs/${job.job_id}`)
                    if (res.ok) {
                        const data = await res.json()
                        setJob(data)
                        if (data.status === 'done' || data.status === 'failed') {
                            setIsPolling(false)
                        }
                    }
                } catch (error) {
                    console.error('Polling error:', error)
                }
            }, 3000)
        }
        return () => clearInterval(timer)
    }, [isPolling, job?.job_id])

    const handleUploadComplete = (jobData) => {
        setJob(jobData)
        setIsPolling(true)
        setSelectedPeak(null)
    }

    const resetDashboard = () => {
        setJob(null)
        setSelectedPeak(null)
        setIsPolling(false)
    }

    const loadMockData = async () => {
        try {
            const res = await fetch('/api/jobs/mock/demo')
            if (res.ok) {
                const data = await res.json()
                setJob(data)
                setIsPolling(false)
                setSelectedPeak(data.peaks[0] || null)
            }
        } catch (error) {
            console.error('Mock data error:', error)
        }
    }

    return (
        <div className="dashboard-layout dashboard-container overflow-hidden">
            {/* Navigation Rail */}
            <aside className="nav-rail py-10">
                <div className="w-12 h-12 bg-grad-premium rounded-2xl flex items-center justify-center shadow-lg transition-transform hover:scale-105 cursor-pointer mb-10">
                    <span className="text-2xl font-black text-dark">A</span>
                </div>
                
                <nav className="flex-1 flex flex-col gap-8">
                    <button className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber flex items-center justify-center transition-all">
                        <LayoutDashboard className="w-5 h-5" />
                    </button>
                    <button className="w-10 h-10 rounded-xl text-secondary hover:bg-white/5 hover:text-white flex items-center justify-center transition-all">
                        <History className="w-5 h-5" />
                    </button>
                    <button className="w-10 h-10 rounded-xl text-secondary hover:bg-white/5 hover:text-white flex items-center justify-center transition-all">
                        <Settings className="w-5 h-5" />
                    </button>
                </nav>

                <button className="w-10 h-10 rounded-xl text-secondary hover:bg-rose-500/10 hover:text-rose-500 flex items-center justify-center transition-all mt-auto">
                    <LogOut className="w-5 h-5" />
                </button>
            </aside>

            {/* Main Content Area */}
            <main className="main-content relative dashboard-map-bg">
                <header className="px-10 py-8 flex justify-between items-center bg-deep/20 backdrop-blur-sm border-b border-white-5">
                    <div className="animate-fade-in">
                        <div className="flex items-center gap-3">
                             <h1 className="text-2xl font-black tracking-tight flex items-center gap-2">
                                Attention<span className="text-teal-400">X</span> AI
                             </h1>
                             <span className="px-2 py-0.5 bg-white-10 rounded text-[8px] font-black uppercase text-muted tracking-widest border border-white-5">MVP 1.0</span>
                        </div>
                        <p className="text-muted text-[10px] mt-1 font-bold uppercase tracking-[0.2em] opacity-60">Advanced Short-Clip Video Generation Engine</p>
                    </div>
                    
                    <div className="flex items-center gap-4">
                        {!job ? (
                            <button onClick={loadMockData} className="btn-mining group text-[9px] px-6 py-3">
                                <Sparkles className="w-4 h-4" /> TRY DEMO MODE
                            </button>
                        ) : (
                            <button onClick={resetDashboard} className="btn btn-ghost text-[9px] group px-6 py-3">
                                <RotateCcw className="w-3.5 h-3.5 group-hover:rotate-180 transition-transform duration-500" /> NEW PROJECT
                            </button>
                        )}
                    </div>
                </header>

                <div className="content-grid overflow-hidden">
                    {/* Left Panel: Input & Status */}
                    <div className="panel-left">
                        <section className="animate-fade-in-up delay-1">
                            <h2 className="text-xxs font-black uppercase tracking-[0.3em] text-muted mb-4 flex items-center gap-2">
                                <span className="w-1 h-1 bg-teal-500 rounded-full"></span> Source Material
                            </h2>
                            <div className="glass-card p-6 bg-white-5">
                                <UploadZone onUploadComplete={handleUploadComplete} isProcessing={isPolling} currentStatus={job?.status} />
                            </div>
                        </section>

                        {job && (
                            <section className="animate-fade-in-up delay-2">
                                <h2 className="text-xxs font-black uppercase tracking-[0.3em] text-muted mb-4 flex items-center gap-2">
                                    <span className="w-1 h-1 bg-blue-500 rounded-full"></span> Pipeline Live
                                </h2>
                                <div className="glass-card p-6 bg-white-5">
                                    <div className="flex items-center justify-between mb-4">
                                        <span className="text-xxs font-black text-muted tracking-widest">Active Job ID</span>
                                        <span className="text-xxs font-black text-white bg-white-10 px-2 py-1 rounded truncate max-w-[120px]">{job.job_id}</span>
                                    </div>
                                    <div className={`status-pill status-${job.status} w-full justify-center`}>
                                        <div className="dot"></div>
                                        {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                                    </div>
                                </div>
                            </section>
                        )}
                    </div>

                    {/* Middle: Timeline & Preview */}
                    <div className="panel-center">
                        <section className="timeline-panel animate-fade-in-up delay-3">
                            <PeakTimeline 
                                rmsArray={job?.rms_array || []} 
                                peaks={job?.peaks || []} 
                                onPeakSelect={setSelectedPeak}
                                selectedPeak={selectedPeak}
                                duration={job?.duration || 0}
                            />
                        </section>

                        <section className="preview-panel animate-fade-in-up delay-4 p-8">
                            <PreviewPane selectedPeak={selectedPeak || (job?.peaks?.[0])} />
                        </section>
                    </div>

                    {/* Right Panel: Results */}
                    <div className="panel-right overflow-hidden">
                        <h2 className="text-xxs font-black uppercase tracking-[0.3em] text-muted mb-4 flex items-center gap-2">
                            <span className="w-1 h-1 bg-teal-500 rounded-full"></span> Viral Nuggets
                        </h2>
                        
                        <div className="results-list custom-scroll flex flex-col gap-4">
                            {job?.peaks && job.peaks.length > 0 ? (
                                job.peaks.map((peak, idx) => (
                                    <ClipCard 
                                        key={idx} 
                                        peak={peak} 
                                        isSelected={selectedPeak?.time === peak.time}
                                        onSelect={() => setSelectedPeak(peak)}
                                    />
                                ))
                            ) : (
                                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-card border-dashed bg-white-2">
                                    <Zap className={`w-10 h-10 mb-4 ${job?.status === 'cropping' ? 'text-amber animate-pulse' : 'opacity-5'}`} />
                                    <p className="text-[10px] font-black uppercase tracking-[0.3em] opacity-40">
                                        {job?.status === 'cropping' ? 'Identifying Viral Nuggets...' : 'Awaiting Extraction'}
                                    </p>
                                    {job?.status === 'cropping' && (
                                        <p className="text-[8px] text-muted mt-2 uppercase font-bold tracking-widest">AI is mining hooks right now</p>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer Status Bar */}
                <footer className="footer-status-bar h-12">
                     <div className="flex items-center gap-6">
                        <span className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50"></div>
                            GPU ACCELERATION: <span className="text-white">ENABLED</span>
                        </span>
                        <span className="opacity-40">|</span>
                        <span className="flex items-center gap-2">
                            LIBROSA AUDIO ANALYSIS: <span className={job?.status === 'done' || job?.status === 'cropping' ? "text-emerald-500" : "text-amber"}>
                                {job?.status === 'done' || job?.status === 'cropping' ? "[COMPLETE]" : "[AWAITING]"}
                            </span>
                        </span>
                     </div>
                     <div className="flex items-center gap-6">
                        <span className="flex items-center gap-2">
                            WHISPER TRANSCRIPTION: <span className={job?.status === 'done' || job?.status === 'cropping' || job?.status === 'analyzing' ? "text-emerald-500" : "text-amber"}>
                                {job?.status === 'done' || job?.status === 'cropping' || job?.status === 'analyzing' ? "[COMPLETE]" : "[IN PROGRESS]"}
                            </span>
                        </span>
                        <span className="opacity-40">|</span>
                        <span className="text-muted tracking-widest flex items-center gap-2">
                            <Clock className="w-3 h-3" /> {new Date().toLocaleTimeString()}
                        </span>
                     </div>
                </footer>
            </main>
        </div>
    )
}

export default Dashboard
