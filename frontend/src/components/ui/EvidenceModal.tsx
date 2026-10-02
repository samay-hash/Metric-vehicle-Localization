import type { JourneyStep } from '../../types';
import React from 'react';
import { X, Play, Pause, Download, AlertTriangle } from 'lucide-react';

export default function EvidenceModal({ step, onClose }: { step: JourneyStep | null; onClose: () => void }) {
  const [isPlaying, setIsPlaying] = React.useState(true);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  
  if (!step) return null;

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) videoRef.current.pause();
      else videoRef.current.play();
      setIsPlaying(!isPlaying);
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = `/streams/cam${(parseInt(step.camera_id.replace('cam','')) % 8) + 1}.mp4`;
    link.download = `Evidence_${step.camera_id}_${step.timestamp}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl w-full max-w-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden animate-in zoom-in-95">
        
        {/* Header */}
        <div className="flex justify-between items-center bg-[#0f172a] border-b border-[#1e293b] p-3 px-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-1.5 rounded">
              <Play size={14} color="white" />
            </div>
            <div className="flex flex-col">
              <span className="text-white text-sm font-bold tracking-wide">CCTV Video Clip Evidence — Stop #{step.step}</span>
              <span className="text-[#64748b] text-[10px] font-medium">{step.camera_name} • Recorded Checkpoint</span>
            </div>
          </div>
          <button onClick={onClose} className="text-[#64748b] hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Video Area */}
        <div className="relative aspect-video bg-black flex items-center justify-center group overflow-hidden">
          <video 
            ref={videoRef}
            src="https://assets.mixkit.co/videos/preview/mixkit-traffic-in-the-city-during-the-evening-4155-large.mp4"
            className="w-full h-full object-cover opacity-80"
            autoPlay
            loop
            muted
            playsInline
          />
          
          {/* Simulated Bounding Box */}
          <div className="absolute top-[40%] left-[35%] w-32 h-24 border-2 border-red-500 animate-pulse pointer-events-none shadow-[0_0_15px_rgba(239,68,68,0.5)] bg-red-500/10"></div>
          
          {/* Simulated ANPR Overlay */}
          <div className="absolute top-[30%] left-[40%] -mt-6 bg-black/80 border border-red-500/50 px-2 py-0.5 text-[10px] font-bold text-red-500 font-mono flex gap-2 pointer-events-none">
            <span>PICKUP 94%</span>
            <span className="bg-white text-black px-1 rounded-sm border border-gray-300 flex items-center">
               <span className="text-[6px] text-blue-800 leading-none mr-0.5">IND</span> {step.plate}
            </span>
          </div>
          
          {/* Top Overlays */}
          <div className="absolute top-2 left-2 flex gap-2">
            <span className="bg-red-600/20 border border-red-600 text-red-500 text-[9px] font-bold px-2 py-0.5 rounded flex items-center gap-1"><span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"/> EVIDENCE PLAYBACK</span>
            <span className="bg-black/60 text-white text-[9px] font-bold px-2 py-0.5 rounded border border-gray-700">{step.camera_id.toUpperCase()} 1080p Full HD</span>
          </div>
          <div className="absolute top-2 right-2">
            <span className="bg-black/60 text-white text-[9px] font-mono font-bold px-2 py-0.5 rounded border border-gray-700">{new Date(step.timestamp).toLocaleString()}</span>
          </div>

          {/* Bottom Overlays & Controls */}
          <div className="absolute bottom-4 left-4 right-4 bg-[#0f172a]/90 backdrop-blur border border-[#1e293b] p-2 rounded-lg flex items-center gap-3">
             <button onClick={togglePlay} className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded text-xs font-bold transition-colors">
               {isPlaying ? <Pause size={14}/> : <Play size={14}/>}
             </button>
             <div className="flex-1 bg-gray-800 h-1.5 rounded-full overflow-hidden relative">
               <div className="absolute left-0 top-0 bottom-0 bg-blue-500 w-[45%] rounded-full shadow-[0_0_10px_rgba(37,99,235,1)]"></div>
             </div>
             <span className="text-[10px] font-bold text-white font-mono">00:04 / 00:10</span>
          </div>
        </div>

        {/* Footer Info */}
        <div className="bg-[#0f172a] p-4 flex flex-col gap-3 border-t border-[#1e293b]">
           <div className="grid grid-cols-4 gap-2">
             <div className="bg-[#1e293b] p-2 rounded border border-[#334155] flex flex-col items-center justify-center">
                <span className="text-[8px] text-[#94a3b8] font-bold tracking-wider mb-1">VEHICLE LICENSE PLATE</span>
                <span className="text-[11px] font-bold text-blue-400 tracking-widest">{step.plate}</span>
             </div>
             <div className="bg-[#1e293b] p-2 rounded border border-[#334155] flex flex-col items-center justify-center">
                <span className="text-[8px] text-[#94a3b8] font-bold tracking-wider mb-1">CHECKPOINT NODE</span>
                <span className="text-[11px] font-bold text-white text-center leading-tight">{step.camera_name}</span>
             </div>
             <div className="bg-[#1e293b] p-2 rounded border border-[#334155] flex flex-col items-center justify-center">
                <span className="text-[8px] text-[#94a3b8] font-bold tracking-wider mb-1">RADAR VEHICLE SPEED</span>
                <span className="text-[11px] font-bold text-yellow-500">7.4 km/h</span>
             </div>
             <div className="bg-[#1e293b] p-2 rounded border border-[#334155] flex flex-col items-center justify-center">
                <span className="text-[8px] text-[#94a3b8] font-bold tracking-wider mb-1">ANPR CONFIDENCE</span>
                <span className="text-[11px] font-bold text-[#10b981]">96.8%</span>
             </div>
           </div>

           <div className="flex justify-between items-center mt-2">
             <span className="text-[9px] text-[#64748b] font-medium flex items-center gap-1.5">
               <AlertTriangle size={12}/> Watermark: CCTNS / eGujCop Law Enforcement Certified Archive
             </span>
             <button onClick={handleDownload} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded text-[11px] font-bold flex items-center gap-2 shadow-[0_0_10px_rgba(37,99,235,0.4)] transition-colors">
               <Download size={14}/> Download Evidence Clip (.mp4)
             </button>
           </div>
        </div>
      </div>
    </div>
  );
}
