import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileVideo, CheckCircle2, AlertCircle, Loader2, Youtube, Link as LinkIcon } from 'lucide-react'

const UploadZone = ({ onUploadComplete, isProcessing, currentStatus }) => {
    const [mode, setMode] = useState('file') // 'file' or 'url'
    const [file, setFile] = useState(null)
    const [youtubeUrl, setYoutubeUrl] = useState('')
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState(null)
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

    const onDrop = useCallback((acceptedFiles) => {
        setFile(acceptedFiles[0])
        setError(null)
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'video/*': ['.mp4', '.mov', '.mkv'] },
        multiple: false,
        disabled: uploading || isProcessing
    })

    const handleUpload = async () => {
        if (!file) return
        setUploading(true)
        setError(null)

        const formData = new FormData()
        formData.append('file', file)

        try {
            const response = await fetch(`${API_BASE}/api/jobs`, {
                method: 'POST',
                body: formData,
            })

            if (response.ok) {
                const data = await response.json()
                onUploadComplete(data)
            } else {
                const errData = await response.json()
                setError(errData.detail || 'Upload failed')
            }
        } catch (err) {
            setError('Connection error occurred')
        } finally {
            setUploading(false)
        }
    }

    const handleUrlSubmit = async (e) => {
        e.preventDefault()
        if (!youtubeUrl) return
        setUploading(true)
        setError(null)

        try {
            const response = await fetch(`${API_BASE}/api/jobs/youtube`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: youtubeUrl }),
            })

            if (response.ok) {
                const data = await response.json()
                onUploadComplete(data)
            } else {
                const errData = await response.json()
                setError(errData.detail || 'URL processing failed')
            }
        } catch (err) {
            setError('Connection error occurred')
        } finally {
            setUploading(false)
        }
    }
    return (
        <div className="flex flex-col gap-6">
            {/* Premium Toggle Switch */}
            <div className="flex bg-dark-40 p-1.5 rounded-2xl border border-white-10 shadow-inner-dark">
                <button 
                    onClick={() => setMode('file')}
                    disabled={uploading || isProcessing}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[9px] font-black transition-all duration-300 ${mode === 'file' ? 'bg-white text-dark shadow-lg' : 'text-secondary hover:text-white'}`}
                >
                    <Upload className="w-3.5 h-3.5" /> LOCAL FILE
                </button>
                <button 
                    onClick={() => setMode('url')}
                    disabled={uploading || isProcessing}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[9px] font-black transition-all duration-300 ${mode === 'url' ? 'bg-white text-dark shadow-lg' : 'text-secondary hover:text-white'}`}
                >
                    <Youtube className="w-3.5 h-3.5" /> YOUTUBE LINK
                </button>
            </div>

            <div className="min-h-[160px] flex flex-col justify-center">
                {mode === 'file' ? (
                    <div 
                        {...getRootProps()} 
                        className={`
                            relative group border border-dashed rounded-2xl p-6 transition-all duration-500 cursor-pointer flex flex-col items-center justify-center gap-3 text-center overflow-hidden
                            ${isDragActive ? 'border-teal-500 bg-teal-500/5 scale-[1.01]' : 'border-white-10 hover:border-teal-500/50 bg-white-2'}
                            ${(uploading || isProcessing) ? 'opacity-40 cursor-not-allowed' : ''}
                        `}
                    >
                        <input {...getInputProps()} />
                        
                        <div className="flex items-center gap-6 w-full justify-center">
                            <div className="w-10 h-5 bg-white-10 rounded-full relative p-0.5">
                                <div className="w-4 h-4 bg-white rounded-full transition-all" style={{ transform: isDragActive ? 'translateX(20px)' : 'translateX(0)' }}></div>
                            </div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-muted">
                                {file ? file.name : (isDragActive ? 'Release' : 'Drop your masterpiece here')}
                            </p>
                            <div className="w-10 h-5 bg-teal-500 rounded-full relative p-0.5">
                                 <div className="w-4 h-4 bg-white rounded-full translate-x-[20px]"></div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-4 animate-fade-in">
                        <div className="relative group">
                            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                                <LinkIcon className={`w-3.5 h-3.5 transition-colors ${youtubeUrl ? 'text-teal-400' : 'text-muted'}`} />
                            </div>
                            <input 
                                type="url"
                                placeholder="Paste YouTube link here..."
                                className="w-full bg-dark-40 border border-white-10 rounded-2xl py-4 pl-12 pr-6 text-xs font-bold placeholder:text-muted focus:outline-none focus:border-teal-500/50 transition-all shadow-inner-dark"
                                value={youtubeUrl}
                                onChange={(e) => setYoutubeUrl(e.target.value)}
                            />
                        </div>
                    </div>
                )}
            </div>

            {error && (
                <div className="flex flex-col gap-2 animate-shake">
                    <div className="bg-rose-500/10 border border-rose-500/20 p-3 rounded-xl flex items-center gap-3 text-rose-500 text-[9px] font-black uppercase tracking-tight">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>{error}</span>
                    </div>
                    {error.toLowerCase().includes('youtube') && (
                        <p className="text-[8px] text-muted font-bold uppercase px-2 leading-relaxed">
                            💡 YouTube is currently blocking our server. <br/>
                            Try downloading the video and using the <span className="text-white">LOCAL FILE</span> tab above for 100% success.
                        </p>
                    )}
                </div>
            )}

            {((mode === 'file' && file) || (mode === 'url' && youtubeUrl)) && !uploading && !isProcessing && (
                <button 
                    onClick={mode === 'file' ? handleUpload : handleUrlSubmit}
                    className="btn-mining w-full text-[10px] py-4"
                >
                    IMPORT & START MINING
                </button>
            )}

            {(uploading || isProcessing) && (
                <div className="flex flex-col gap-5 mt-2 p-6 glass-card bg-white-5">
                    <div className="flex items-center justify-between text-xxs font-black uppercase tracking-widest">
                        <span className="text-muted">Pipeline Progress</span>
                        <span className="text-amber flex items-center gap-2">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            {currentStatus || 'Processing...'}
                        </span>
                    </div>
                    <div className="h-1.5 w-full bg-white-10 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-grad-premium shadow-lg transition-all duration-1000"
                            style={{ 
                                width: uploading ? '20%' : 
                                       currentStatus === 'downloading' ? '35%' :
                                       currentStatus === 'transcribing' ? '50%' :
                                       currentStatus === 'analyzing' ? '70%' :
                                       currentStatus === 'cropping' ? '90%' : '100%'
                            }}
                        />
                    </div>
                </div>
            )}
            
            {currentStatus === 'done' && (
                <div className="flex items-center flex-col gap-4 p-8 glass-card bg-emerald-500/5 border-emerald-500/20 animate-fade-in text-center">
                    <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center animate-bounce shadow-lg shadow-emerald-500/20">
                        <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                    </div>
                    <div>
                        <h3 className="text-sm font-black text-emerald-500 uppercase tracking-widest">Extraction Complete</h3>
                        <p className="text-[10px] text-emerald-500/60 mt-1 uppercase tracking-widest font-black">Viral nuggets ready for export</p>
                    </div>
                </div>
            )}
        </div>
    )
}

export default UploadZone
