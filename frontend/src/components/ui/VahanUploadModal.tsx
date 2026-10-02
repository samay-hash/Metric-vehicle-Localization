import React, { useState } from 'react';
import { X, Upload, Search, CheckCircle, Car, ShieldAlert, FileText, Fingerprint } from 'lucide-react';

export default function VahanUploadModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0); 
  // 0: Upload prompt, 1: Scanning, 2: Result
  const [image, setImage] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImage(URL.createObjectURL(e.target.files[0]));
      setStep(1);
      
      // Simulate OCR and DB hit
      setTimeout(() => {
        setStep(2);
      }, 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl w-full max-w-lg shadow-[0_0_50px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="flex justify-between items-center bg-[#0f172a] border-b border-[#1e293b] p-3 px-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-1.5 rounded">
              <Upload size={14} color="white" />
            </div>
            <div className="flex flex-col">
              <span className="text-white text-sm font-bold tracking-wide">National VAHAN Database Sync</span>
              <span className="text-[#64748b] text-[10px] font-medium">Upload CCTV Image for Direct ANPR Query</span>
            </div>
          </div>
          <button onClick={onClose} className="text-[#64748b] hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-6">
          {step === 0 && (
            <div className="border-2 border-dashed border-[#334155] rounded-lg bg-[#0f172a] p-10 flex flex-col items-center justify-center text-center cursor-pointer hover:border-blue-500 transition-colors group relative">
              <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" accept="image/*" onChange={handleFileSelect} />
              <div className="w-12 h-12 bg-[#1e293b] rounded-full flex items-center justify-center mb-4 group-hover:bg-blue-600 transition-colors">
                <Upload size={20} className="text-blue-400 group-hover:text-white" />
              </div>
              <h3 className="text-white font-bold text-sm mb-1">Click or drag image to upload</h3>
              <p className="text-[#64748b] text-xs">Supports JPG, PNG up to 10MB</p>
              
              <div className="mt-6 flex items-center gap-4 border-t border-[#1e293b] pt-4 w-full justify-center">
                 <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/800px-Emblem_of_India.svg.png" className="h-8 opacity-50 grayscale" alt="India Emblem"/>
                 <div className="text-[9px] text-[#64748b] font-medium text-left">
                    Integrated with<br/><span className="text-white font-bold">Ministry of Road Transport & Highways</span>
                 </div>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="relative w-48 h-48 mb-6 rounded-lg overflow-hidden border border-[#1e293b]">
                <img src={image ?? undefined} className="w-full h-full object-cover opacity-50 grayscale" />
                <div className="absolute top-0 left-0 right-0 h-1 bg-blue-500 shadow-[0_0_20px_rgba(37,99,235,1)] animate-[scan_1.5s_ease-in-out_infinite]" />
              </div>
              <div className="flex items-center gap-3 text-blue-400 font-bold tracking-widest text-sm">
                <Search className="animate-spin" size={16} /> 
                EXTRACTING LICENSE PLATE...
              </div>
              <div className="text-[10px] text-[#64748b] mt-2 font-mono">Querying Parivahan / eChallan servers</div>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-center mb-4">
                 <div className="bg-white text-black font-extrabold text-2xl px-4 py-2 rounded-lg border-2 border-gray-400 shadow-[0_0_20px_rgba(255,255,255,0.2)] flex items-center">
                   <div className="flex flex-col items-center mr-3">
                     <span className="text-[10px] text-blue-800 leading-none mb-1">IND</span>
                     <div className="w-4 h-4 rounded-full border border-blue-800 opacity-50"></div>
                   </div>
                   GJ01AB1234
                 </div>
              </div>

              <div className="bg-[#10b981]/10 border border-[#10b981]/30 rounded-lg p-3 flex items-center justify-center gap-2 mb-6">
                 <CheckCircle size={16} className="text-[#10b981]" />
                 <span className="text-[#10b981] text-xs font-bold tracking-wider">VAHAN RECORD FOUND</span>
              </div>

              <div className="bg-[#0f172a] rounded-lg border border-[#1e293b] p-4 space-y-4">
                 <div className="flex justify-between items-center border-b border-[#1e293b] pb-3">
                    <div className="flex items-center gap-2 text-[#94a3b8] text-[10px] font-bold"><Car size={14}/> MAKE & MODEL</div>
                    <div className="text-white text-xs font-bold">HYUNDAI CRETA (WHITE)</div>
                 </div>
                 <div className="flex justify-between items-center border-b border-[#1e293b] pb-3">
                    <div className="flex items-center gap-2 text-[#94a3b8] text-[10px] font-bold"><Fingerprint size={14}/> CHASSIS NO.</div>
                    <div className="text-white text-xs font-mono font-bold">MALC841BCM10XXXX</div>
                 </div>
                 <div className="flex justify-between items-center border-b border-[#1e293b] pb-3">
                    <div className="flex items-center gap-2 text-[#94a3b8] text-[10px] font-bold"><FileText size={14}/> REGISTRATION NAME</div>
                    <div className="text-white text-xs font-bold">HARSHIL PATEL</div>
                 </div>
                 <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2 text-[#94a3b8] text-[10px] font-bold"><ShieldAlert size={14}/> STATUS</div>
                    <div className="bg-[#ef4444] text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider shadow-[0_0_10px_rgba(239,68,68,0.4)]">STOLEN - HOTLISTED</div>
                 </div>
              </div>

              <button onClick={onClose} className="w-full mt-6 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 rounded shadow-[0_0_15px_rgba(37,99,235,0.4)] transition-colors text-sm tracking-wide">
                 Import to Sentinel Dossier
              </button>
            </div>
          )}
        </div>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes scan {
          0% { top: 0%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
      `}} />
    </div>
  );
}
