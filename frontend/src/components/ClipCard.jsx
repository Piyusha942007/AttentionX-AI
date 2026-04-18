import React from 'react'
import { Bookmark, Download, Zap, Clock, Play } from 'lucide-react'

const ClipCard = ({ peak, isSelected, onSelect }) => {
    const getScoreColor = (score) => {
        if (score >= 0.8) return 'badge-green'
        if (score >= 0.5) return 'badge-amber'
        return 'badge-gray'
    }

    const formatReason = (reason) => {
        return (reason || 'Viral Moment').replace(/_/g, ' ')
    }

    const handleDownload = (e) => {
        e.stopPropagation()
        if (peak.clip_id) {
            window.open(`/api/clips/${peak.clip_id}/download`, '_blank')
        }
    }

    return (
        <div 
            onClick={onSelect}
            className={`
                group glass-card p-4 cursor-pointer relative overflow-hidden flex gap-4 transition-all duration-300
                ${isSelected ? 'border-teal-500 shadow-lg scale-[1.01] bg-white-5' : 'hover:border-white-10'}
            `}
        >
            {/* Thumbnail Section */}
            <div className="w-24 h-24 rounded-xl overflow-hidden relative flex-shrink-0 bg-black border border-white-10">
                <div className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-transparent transition-all z-10">
                    <Play className={`w-8 h-8 fill-white text-white drop-shadow-lg transition-transform ${isSelected ? 'scale-110' : 'group-hover:scale-110'}`} />
                </div>
                {/* Placeholder Thumbnail Background */}
                <div className="absolute inset-0 bg-grad-aurora opacity-20" />
            </div>

            {/* Content Section */}
            <div className="flex-1 flex flex-col justify-between py-1">
                <div className="flex justify-between items-start">
                    <h3 className="text-xs font-black leading-tight text-white group-hover:text-amber transition-colors line-clamp-2 max-w-[160px]">
                        {peak.headline || "Identifying viral insight..."}
                    </h3>
                    <div className="flex gap-2">
                         <button className="p-1 hover:text-white text-muted transition-colors"><Download className="w-3.5 h-3.5" /></button>
                         <button className="p-1 hover:text-white text-muted transition-colors"><Zap className="w-3.5 h-3.5" /></button>
                         <button className="p-1 hover:text-white text-muted transition-colors"><Play className="w-3.5 h-3.5" /></button>
                    </div>
                </div>

                <div className="flex items-center justify-between">
                    <div className="virality-pill flex items-center gap-1.5">
                        <span className="opacity-60">VIRALITY SCORE:</span>
                        <span className="text-white">{(peak.score * 100).toFixed(0)}%</span>
                    </div>
                    <span className="text-[9px] font-black text-muted uppercase tracking-widest">
                        {new Date(peak.start * 1000).toISOString().substr(14, 5)} - {new Date(peak.end * 1000).toISOString().substr(14, 5)}
                    </span>
                </div>
            </div>

            {isSelected && !peak.clip_url && (
                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-amber-500/20 overflow-hidden">
                    <div className="h-full bg-amber-500 w-1/3 animate-loading-bar" />
                </div>
            )}
        </div>
    )
}

export default ClipCard
