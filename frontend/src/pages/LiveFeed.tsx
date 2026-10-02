import { hasCoordinates } from '../lib/coordinates';
import type { RegistryCamera, CameraStream, SecurityEvent, ActiveVehicle, JourneyStep, Journey, Watchlist, StreamDetections, ChatCompletion } from '../types';
import { useState, useEffect, useRef } from 'react';
import { analyticsApi as axios, dashboardFetch, getRegistryCameras, getRegistryCameraStreams, getEvents, getLiveStreamUrl, readJson } from '../api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Camera, Map, CheckCircle, AlertTriangle, ShieldAlert, MonitorPlay, Download, ChevronLeft, ChevronRight, Video, Camera as CameraIcon, BarChart2, Bell, FileText, Upload, Disc, Sun, Moon, Search, SlidersHorizontal, Eye, Maximize, Clock, FileBarChart, Send, Bot, User, MessageSquare, Car } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, Marker, Popup, Polyline, LayersControl } from 'react-leaflet';
import L from 'leaflet';
import { useDashboardAuth } from '../DashboardAuth';
import { useNavigate, useSearchParams } from 'react-router-dom';
import EvidenceModal from '../components/ui/EvidenceModal';
import VahanUploadModal from '../components/ui/VahanUploadModal';

// Leaflet Icon setup
// Explicit asset URLs avoid depending on Leaflet’s internal icon path detection.
L.Marker.prototype.options.icon = L.icon({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], tooltipAnchor: [16, -28], shadowSize: [41, 41],
});

const cameraIcon = new L.DivIcon({
  html: `<div style="background-color: #3b82f6; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px #3b82f6;"></div>`,
  className: '',
  iconSize: [12, 12],
  iconAnchor: [6, 6]
});

const nodeIcon = new L.DivIcon({
  html: `<div style="background-color: #ef4444; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 15px #ef4444;"></div>`,
  className: '',
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});

function registryCameraToLiveCamera(camera: RegistryCamera) {
  return {
    registry_id: camera.id,
    camera_id: camera.external_id,
    name: camera.name,
    city: camera.location || camera.department || 'Location pending',
    department: camera.department || 'Department pending',
    lat: camera.coordinates?.latitude ?? null,
    lng: camera.coordinates?.longitude ?? null,
    stream_count: camera.stream?.count || 0,
    stream_protocols: camera.stream?.protocols || [],
  };
}

type LiveCamera = ReturnType<typeof registryCameraToLiveCamera>;
interface Snapshot { url: string; camera: string; time: string }
interface ChatMessage { role: 'assistant' | 'user'; content: string }

export default function LiveFeed() {
  const auth = useDashboardAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedCamera = searchParams.get('camera');
  const displayName = auth.identity?.display_name || auth.identity?.email || 'Signed-in user';
  const initials = displayName.trim().split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase();
  const roleLabel = auth.identity?.roles?.map(role => role.replaceAll('_', ' ')).join(' · ') || 'Role unavailable';
  const [criticalCount, setCriticalCount] = useState<number | null>(null);
  const canReadEvents = auth.has('event.read');
  useEffect(() => {
    if (!canReadEvents) return;
    let active = true;
    const load = () => getEvents({ severity: 'critical', status: 'pending_review', limit: 1 })
      .then(response => { if (active) setCriticalCount(response.data.total); })
      .catch(() => { if (active) setCriticalCount(null); });
    void load();
    const timer = setInterval(load, 30000);
    return () => { active = false; clearInterval(timer); };
  }, [canReadEvents]);
  const [cameras, setCameras] = useState<LiveCamera[]>([]);
  const [selectedCam, setSelectedCam] = useState<LiveCamera | null>(null);
  const [selectedStreams, setSelectedStreams] = useState<CameraStream[]>([]);
  const [registryError, setRegistryError] = useState('');
  
  const [liveEvents, setLiveEvents] = useState<SecurityEvent[]>([]);
  const [activeVehicles, setActiveVehicles] = useState<ActiveVehicle[]>([]);
  const [search, setSearch] = useState("");
  const [districtFilter, setDistrictFilter] = useState("ALL");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [viewMode, setViewMode] = useState("VIDEO"); 
  const [plateSearch, setPlateSearch] = useState("");
  const [journeyRoute, setJourneyRoute] = useState<JourneyStep[] | null>(null);
  const [showVahanModal, setShowVahanModal] = useState(false);
  const [selectedEvidenceStep, setSelectedEvidenceStep] = useState<JourneyStep | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  
  // Interactivity State
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false); // Default to light mode

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: "Hello! I am Sentinel Copilot. I have full context of this dashboard. How can I assist you with the live feeds today?" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getRegistryCameras({ limit: 500 }).then(res => {
      const cams = (res.data.data || []).map(registryCameraToLiveCamera);
      setCameras(cams);
      if (cams.length > 0) setSelectedCam(cams.find(camera => camera.registry_id === requestedCamera) || cams[0]);
    }).catch(error => {
      console.error(error);
      setRegistryError('Camera registry is unavailable. Start the registry service and confirm its reader token.');
    });

    const poll = async () => {
      try {
        const eventRes = await axios.get<{ events: SecurityEvent[] }>('/events/?limit=5');
        setLiveEvents(eventRes.data.events || []);
        
        const vehRes = await axios.get<{ vehicles: ActiveVehicle[] }>('/vehicles/active');
        setActiveVehicles(vehRes.data.vehicles || []);
      } catch(e) {}
    };
    poll();
    const intv = setInterval(poll, 3000);
    return () => clearInterval(intv);
  }, []);

  useEffect(() => {
    if (!selectedCam?.registry_id) {
      setSelectedStreams([]);
      return;
    }
    let active = true;
    getRegistryCameraStreams(selectedCam.registry_id)
      .then(response => active && setSelectedStreams(response.data.streams || []))
      .catch(error => {
        console.error(error);
        if (active) setSelectedStreams([]);
      });
    return () => { active = false; };
  }, [selectedCam?.registry_id]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const filteredCams = cameras.filter(c => {
    if (districtFilter !== "ALL" && c.city !== districtFilter) return false;
    if (search && !`${c.name} ${c.camera_id} ${c.city}`.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleNextCam = () => {
    if (!cameras.length) return;
    const idx = cameras.findIndex(c => c.camera_id === selectedCam?.camera_id);
    const nextIdx = (idx + 1) % cameras.length;
    setSelectedCam(cameras[nextIdx]);
    setViewMode("VIDEO");
  };

  const handlePrevCam = () => {
    if (!cameras.length) return;
    const idx = cameras.findIndex(c => c.camera_id === selectedCam?.camera_id);
    const prevIdx = (idx - 1 + cameras.length) % cameras.length;
    setSelectedCam(cameras[prevIdx]);
    setViewMode("VIDEO");
  };

  const handleSnapshot = () => {
    const videoImg = document.querySelector<HTMLImageElement>("#video-container img");
    if (videoImg) {
      const canvas = document.createElement("canvas");
      canvas.width = videoImg.naturalWidth || 640;
      canvas.height = videoImg.naturalHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(videoImg, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
      
      setSnapshots(prev => [{
        url: dataUrl,
        camera: selectedCam?.camera_id?.toUpperCase() || "CAM",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }, ...prev].slice(0, 3));
    }

    const el = document.getElementById("video-container");
    if(el) {
      el.style.opacity = "0";
      setTimeout(() => el.style.opacity = "1", 150);
    }
    showToast("Snapshot captured successfully!");
  };

  const handleTracePlate = async (plate: string) => {
    if (!plate) return;
    try {
      // Actually fetch the journey for this real plate
      const jRes = await axios.get<Journey>(`/vehicles/journey/${encodeURIComponent(plate)}`);
      setJourneyRoute(jRes.data.route || []);
      setPlateSearch(plate);
      setViewMode("MAP");
      showToast(`Tracing real route for ${plate}...`);
    } catch (error) {
      console.error(error);
      showToast(`Error tracing ${plate} - no journey found`);
    }
  };

  const handleGenerateReport = async () => {
    showToast("Generating PDF report...");
    try {
      const res = await dashboardFetch('/reports/eod/pdf');
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentinel_eod_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("PDF downloaded successfully!");
    } catch (err) {
      showToast("PDF generation failed — check backend.");
    }
  };

  const handleWatchlist = async () => {
    try {
      const res = await dashboardFetch('/watchlist/');
      const data = await readJson<Watchlist>(res);
      const plates = data.entries.map(e => `${e.plate} (${e.make})`).join(', ');
      showToast(`Watchlist: ${data.total} vehicles — ${plates.slice(0,80)}`);
    } catch {
      showToast("Watchlist unavailable — check backend.");
    }
  };

  const handleStatewideTrace = () => {
    setViewMode("MAP");
    showToast("Map view active — all confirmed ANPR plates plotted on Gujarat grid.");
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim()) return;
    const userText = chatInput.trim();
    const newMsgs: ChatMessage[] = [...chatMessages, { role: 'user', content: userText }];
    setChatMessages(newMsgs);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const activePlatesStr = activeVehicles.length 
        ? activeVehicles.map(v => `Vehicle ${v.plate} was last seen on camera ${v.last_camera}.`).join(" ") 
        : "No vehicles recently detected.";
        
      const recentEvtsStr = liveEvents.length 
        ? liveEvents.slice(0, 3).map(e => `Alert: ${e.event_type} on camera ${e.camera_id}.`).join(" ") 
        : "No recent security alerts.";

      let sceneDescription = "No camera is currently selected by the user.";
      if (selectedCam) {
        try {
          const detRes  = await dashboardFetch(`/stream/${encodeURIComponent(selectedCam.registry_id)}/detections`);
          const detData = await readJson<StreamDetections>(detRes);
          if (detData.status === "live" && detData.total_objects > 0) {
            sceneDescription = `The user is currently looking at camera '${selectedCam.name}'. It sees ${detData.total_objects} objects right now.`;
            if (detData.confirmed_plates.length > 0) {
              sceneDescription += ` License plates visible right now: ${detData.confirmed_plates.join(", ")}.`;
            }
          } else if (detData.status === "stream_not_active") {
            sceneDescription = `The user selected camera '${selectedCam.name}', but the stream is not playing.`;
          } else {
            sceneDescription = `The user is looking at camera '${selectedCam.name}', but no objects are detected in the frame right now.`;
          }
        } catch {
          sceneDescription = `The user selected camera '${selectedCam.name}', but live data is unavailable.`;
        }
      }

      const context = `You are a helpful AI assistant for a CCTV surveillance system. Answer the user's questions based ONLY on the data provided below. Do not make up answers. Keep responses short and conversational.

SYSTEM DATA:
- ${sceneDescription}
- ${activePlatesStr}
- ${recentEvtsStr}
`;

      const response = await dashboardFetch(`/inference/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMsgs.map(m => ({ role: m.role, content: m.content })),
          context: context
        })
      });

      if (!response.ok) {
        throw new Error("Local LLM request failed");
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader available");

      const decoder = new TextDecoder();
      let botReply = "";
      
      setChatMessages([...newMsgs, { role: 'assistant', content: botReply }]);
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        botReply += decoder.decode(value, { stream: true });
        setChatMessages([...newMsgs, { role: 'assistant', content: botReply }]);
      }
    } catch (err) {
      console.error(err);
      setChatMessages([...newMsgs, { role: 'assistant', content: "Connection error with Local AI API." }]);
    } finally {
      setIsChatLoading(false);
    }
  };



  const currentDate = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  const currentTime = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
  const selectedFeedUrl = selectedCam?.registry_id
    ? getLiveStreamUrl(selectedCam.registry_id)
    : null;
  const selectedProtocolLabel = selectedStreams.length
    ? [...new Set(selectedStreams.map(stream => stream.protocol?.toUpperCase()).filter(Boolean))].join(' / ')
    : selectedCam?.stream_protocols?.map(protocol => protocol.toUpperCase()).join(' / ') || 'No stream';

  // -----------------------------------------------------
  // DYNAMIC THEMING CLASSES
  // -----------------------------------------------------
  const tWrapper = isDarkMode ? "bg-[#0b0f19] text-gray-200" : "bg-[#f4f2ee] text-[#1e293b]";
  const tHeader = isDarkMode ? "bg-[#111827] border-b border-gray-800 shadow-none" : "bg-white border-b border-gray-200 shadow-sm";
  const tCard = isDarkMode ? "bg-[#1e293b] border-gray-700 shadow-none" : "bg-white border-gray-100 shadow-sm";
  const tTextPrimary = isDarkMode ? "text-white" : "text-[#1e293b]";
  const tTextSecondary = isDarkMode ? "text-gray-400" : "text-[#64748b]";
  const tInput = isDarkMode ? "bg-[#0f172a] border-gray-700 text-gray-200 focus:border-blue-500" : "bg-gray-50 border-gray-200 text-gray-700 focus:border-blue-400";
  const tHover = isDarkMode ? "hover:bg-slate-700" : "hover:bg-gray-50";
  const tButtonAction = isDarkMode ? "bg-slate-700 border-slate-600 text-gray-200 hover:bg-slate-600 active:bg-slate-500" : "bg-gray-50 border-gray-200 text-[#1e293b] hover:bg-gray-100 active:bg-gray-200";

  return (
    <div className={`flex flex-col h-screen w-full font-sans overflow-hidden transition-colors duration-300 ${tWrapper}`}>
      
      {showVahanModal && <VahanUploadModal onClose={() => setShowVahanModal(false)} />}
      <EvidenceModal step={selectedEvidenceStep} onClose={() => setSelectedEvidenceStep(null)} />
      <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept="image/*,video/*" />

      {/* Toast Notification */}
      {toastMsg && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-[100] bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 animate-bounce border border-gray-700">
          <CheckCircle size={16} className="text-[#10b981]"/> {toastMsg}
        </div>
      )}

      {/* TOP HEADER */}
      <header className={`h-[60px] flex items-center justify-between px-6 shrink-0 z-50 transition-colors duration-300 ${tHeader}`}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm">
             <ShieldAlert size={18} color="white" />
          </div>
          <div className="flex flex-col">
            <h1 className={`text-[15px] font-bold leading-tight ${tTextPrimary}`}>
              Gujarat Sentinel Grid
            </h1>
            <span className={`text-[10px] font-medium tracking-wide ${tTextSecondary}`}>STATEWIDE CCTV & VEHICLE RE-IDENTIFICATION</span>
          </div>
        </div>

        <div className="flex items-center gap-2 lg:gap-6">
          <button onClick={() => setViewMode("VIDEO")} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all ${viewMode === "VIDEO" ? 'bg-blue-500/20 text-blue-500' : `${tTextSecondary} ${tHover}`}`}>
            <MonitorPlay size={16} /> <span className="hidden md:inline">Live Monitor</span>
          </button>
          <button onClick={() => setViewMode("MAP")} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all ${viewMode === "MAP" ? 'bg-blue-500/20 text-blue-500' : `${tTextSecondary} ${tHover}`}`}>
            <Map size={16} /> <span className="hidden md:inline">GIS Route Trace</span>
          </button>
          <button className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold ${tTextSecondary} ${tHover}`}><CameraIcon size={16}/> <span className="hidden lg:inline">Cameras</span></button>
          <button className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold ${tTextSecondary} ${tHover}`}><ShieldAlert size={16}/> <span className="hidden lg:inline">Watchlist</span></button>
          <button className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold ${tTextSecondary} ${tHover}`}><BarChart2 size={16}/> <span className="hidden xl:inline">Analytics</span></button>
        </div>

        <div className="flex items-center gap-4">
          <div className={`flex items-center p-1 rounded-full cursor-pointer transition-colors ${isDarkMode ? 'bg-slate-800' : 'bg-gray-100'}`}>
            <button onClick={() => setIsDarkMode(false)} className={`p-1 rounded-full transition-all ${!isDarkMode ? 'bg-white shadow-sm text-[#d97706]' : 'text-gray-500 hover:text-gray-300'}`}><Sun size={14}/></button>
            <button onClick={() => setIsDarkMode(true)} className={`p-1 rounded-full transition-all ${isDarkMode ? 'bg-slate-600 shadow-sm text-yellow-300' : 'text-gray-400 hover:text-gray-600'}`}><Moon size={14}/></button>
          </div>
          {canReadEvents && <button type="button" className="relative cursor-pointer group" onClick={() => navigate('/dashboard/events')} aria-label={criticalCount === null ? 'Open events; critical alert count unavailable' : `Open events; ${criticalCount} pending critical alerts`}>
            <Bell size={20} className={`${tTextSecondary} hover:text-blue-500 transition-colors`}/>
            {criticalCount !== null && criticalCount > 0 && <span className="absolute -top-1 -right-1 min-w-3.5 h-3.5 px-0.5 bg-red-500 rounded-full text-white text-[8px] font-bold flex items-center justify-center border border-transparent">{criticalCount}</span>}
          </button>}
          <div className={`flex items-center gap-2 pl-2 border-l ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shadow-sm">{initials}</div>
            <div className="flex flex-col hidden sm:flex">
              <span className={`text-[12px] font-bold ${tTextPrimary}`}>{displayName}</span>
              <span className="text-[10px] text-gray-500">{roleLabel}</span>
            </div>
          </div>
          <div className="flex flex-col items-end ml-2 lg:ml-4 text-[11px] text-gray-500 font-medium">
            <span>{currentDate}</span>
            <span className={`font-bold tracking-wide ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>{currentTime}</span>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT WRAPPER */}
      <div className="flex flex-1 p-3 gap-3 overflow-hidden">
        
        {/* LEFT SIDEBAR: CAMERA REGISTRY */}
        <div className={`w-[280px] rounded-xl flex flex-col shrink-0 overflow-hidden border transition-colors duration-300 ${tCard}`}>
          <div className={`p-4 border-b flex justify-between items-center ${isDarkMode ? 'border-gray-700 bg-[#1e293b]' : 'border-gray-100 bg-white'}`}>
            <span className={`text-[13px] font-bold flex items-center gap-2 ${tTextPrimary}`}>
              <CameraIcon size={16}/> Camera Registry
            </span>
            <span className="bg-[#10b981]/10 text-[#10b981] text-[10px] px-2 py-0.5 rounded-full font-bold">
              {cameras.length} Registered
            </span>
          </div>
          
          <div className="p-3 space-y-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
              <input 
                type="text" 
                placeholder="Search cameras..." 
                className={`w-full text-xs pl-8 pr-3 py-2 rounded-lg focus:outline-none focus:ring-1 transition-all border ${tInput}`}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select className={`w-full text-[11px] font-medium p-2 rounded-lg focus:outline-none transition-colors border ${tInput}`}>
                <option>All Depts</option>
                <option>Traffic</option>
              </select>
              <select 
                className={`w-full text-[11px] font-medium p-2 rounded-lg focus:outline-none transition-colors border ${tInput}`}
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}
              >
                {["ALL", ...new Set(cameras.map(c => c.city).filter(Boolean))].map(d => <option key={d} value={d}>{d === 'ALL' ? 'All Districts' : d}</option>)}
              </select>
            </div>
          </div>
          {registryError && <div className="mx-3 mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[10px] font-medium text-red-700">{registryError}</div>}

          <div className="flex-1 overflow-y-auto px-2 pb-2 custom-scrollbar space-y-1">
            {filteredCams.map(cam => (
              <div 
                key={cam.camera_id} 
                onClick={() => { setSelectedCam(cam); setViewMode("VIDEO"); }}
                className={`flex gap-3 p-2 rounded-lg cursor-pointer transition-colors border border-transparent ${selectedCam?.camera_id === cam.camera_id && viewMode === "VIDEO" ? (isDarkMode ? 'bg-slate-700/50 border-slate-600' : 'bg-blue-50 border-blue-200 shadow-sm') : tHover}`}
              >
                <div className={`w-[50px] h-[35px] shrink-0 rounded overflow-hidden relative flex items-center justify-center ${isDarkMode ? 'bg-slate-800' : 'bg-gray-200'}`}>
                  <Video size={16} className="text-gray-500" />
                  <div className={`absolute top-0 right-0 w-1.5 h-1.5 rounded-full m-1 shadow-sm ${selectedCam?.camera_id === cam.camera_id ? 'bg-[#10b981] animate-pulse' : 'bg-gray-500'}`}></div>
                </div>
                <div className="flex-1 flex flex-col justify-center min-w-0">
                  <div className="flex justify-between items-center">
                    <span className={`text-[12px] font-bold leading-tight truncate ${tTextPrimary}`}>{cam.camera_id.toUpperCase()}</span>
                    {selectedCam?.camera_id === cam.camera_id && <span className="text-[8px] font-bold text-[#10b981] bg-[#10b981]/10 px-1.5 py-0.5 rounded ml-1 shrink-0">LIVE</span>}
                  </div>
                  <span className={`text-[10px] leading-tight mt-0.5 truncate ${tTextSecondary}`}>{cam.name}</span>
                  <span className={`text-[9px] leading-tight truncate ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>{cam.city}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER AREA */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          
          {/* Main Video View */}
          <div className={`rounded-xl flex flex-col p-3 h-[50vh] border transition-colors duration-300 ${tCard}`}>
            {viewMode === "VIDEO" && selectedCam && (
              <>
                <div className="flex justify-between items-center mb-3">
                  <div className="flex items-center gap-3">
                    <div className="bg-red-600 text-white text-[10px] font-bold px-3 py-1 rounded-full flex items-center gap-1.5 shadow-sm">
                      <span className="w-2 h-2 bg-white rounded-full animate-pulse" /> LIVE
                    </div>
                    <div className="flex flex-col">
                       <span className={`text-[14px] font-bold ${tTextPrimary}`}>{selectedCam.camera_id.toUpperCase()} - {selectedCam.name}</span>
                       <span className={`text-[10px] font-medium ${tTextSecondary}`}>{selectedCam.city} • {selectedCam.department} • {selectedProtocolLabel}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={handlePrevCam} className={`flex items-center gap-1 px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors border shadow-sm ${tButtonAction}`}><ChevronLeft size={14}/> <span className="hidden lg:inline">Prev Cam</span></button>
                    <button onClick={handleNextCam} className={`flex items-center gap-1 px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors border shadow-sm ${tButtonAction}`}><span className="hidden lg:inline">Next Cam</span> <ChevronRight size={14}/></button>
                    <button onClick={handleSnapshot} className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors border shadow-sm ${tButtonAction}`}><CameraIcon size={14}/> <span className="hidden xl:inline">Snapshot</span></button>
                    <button className={`p-1.5 rounded-lg transition-colors border shadow-sm ml-2 ${tButtonAction}`}><Maximize size={14}/></button>
                  </div>
                </div>
                
                <div id="video-container" className="flex-1 relative rounded-xl overflow-hidden bg-black shadow-inner transition-opacity duration-150 border border-gray-800">
                  <div className="absolute top-3 left-4 text-white font-mono font-bold text-sm tracking-wide z-20 drop-shadow-md">
                     {new Date().toLocaleDateString('en-GB').replace(/\//g,'-')} <span className="ml-2">{new Date().toLocaleTimeString('en-GB', {hour12:false})}</span>
                  </div>
                  <div className="absolute top-3 right-4 text-white/80 font-mono text-[9px] z-20">
                     ANPR ACTIVE | FPS: 20.1 | {new Date().toLocaleTimeString('en-US', {hour12:true})} IST
                  </div>
                  <div className="absolute bottom-3 left-4 flex gap-2 z-20">
                     <span className="bg-[#1e293b]/80 backdrop-blur border border-gray-600 text-[#10b981] text-[10px] font-bold px-2 py-1 rounded-lg flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#10b981] rounded-full"/> Sentinel Edge AI Active</span>
                  </div>
                  <div className="absolute bottom-3 right-4 text-white/80 text-[11px] font-medium z-20 drop-shadow-md">
                     {selectedCam.name} - PTZ2
                  </div>
                  <img 
                    key={selectedFeedUrl}
                    crossOrigin="use-credentials"
                    src={selectedFeedUrl ?? undefined}
                    alt="Live Feed"
                    className="w-full h-full object-cover opacity-95"
                    onLoad={(e) => { e.currentTarget.style.display = ''; }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                </div>
              </>
            )}

            {viewMode === "MAP" && (
              <div className={`w-full h-full rounded-xl overflow-hidden relative border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <MapContainer center={[23.0225, 72.5714]} zoom={11} style={{ height: '100%', width: '100%' }} zoomControl={false}>
                  <LayersControl position="topright">
                    <LayersControl.BaseLayer checked name="Street View">
                      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
                    </LayersControl.BaseLayer>
                    <LayersControl.BaseLayer name="Satellite View">
                      <TileLayer url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}" attribution="Google" />
                    </LayersControl.BaseLayer>
                  </LayersControl>
                  {cameras.filter(hasCoordinates).map(cam => (
                    <Marker key={cam.camera_id} position={[cam.lat, cam.lng]} icon={cameraIcon}>
                      <Popup><div className="font-bold text-gray-800">{cam.name}</div></Popup>
                    </Marker>
                  ))}
                  {journeyRoute && journeyRoute.length > 0 && (
                    <>
                      <Polyline positions={journeyRoute.filter(hasCoordinates).map(j => [j.lat, j.lng])} color="#ef4444" weight={4} dashArray="10, 10" />
                      {journeyRoute.filter(hasCoordinates).map((j, idx) => (
                        <Marker key={idx} position={[j.lat, j.lng]} icon={nodeIcon}>
                          <Popup>
                             <div className="p-1 text-gray-800">
                               <div className="font-bold text-red-600">{plateSearch} spotted</div>
                               <div className="text-xs">{new Date(j.timestamp).toLocaleString()} at {j.camera_id}</div>
                             </div>
                          </Popup>
                        </Marker>
                      ))}
                    </>
                  )}
                </MapContainer>
              </div>
            )}
          </div>

          {/* Bottom Grid: Recent Events & Snapshot Gallery */}
          <div className="grid grid-cols-5 gap-3 min-h-0 flex-1">
            {/* Recent Events (Real Data) */}
            <div className={`col-span-2 rounded-xl flex flex-col overflow-hidden border transition-colors duration-300 ${tCard} p-4`}>
               <div className="flex justify-between items-center mb-3">
                 <h2 className={`text-[13px] font-bold flex items-center gap-2 ${tTextPrimary}`}>Recent Events <span className="bg-[#10b981]/10 text-[#10b981] px-2 py-0.5 rounded-full text-[9px]">Live Data</span></h2>
                 <span className="text-[10px] font-bold text-blue-500 cursor-pointer hover:underline flex items-center gap-1">View All <ChevronRight size={10}/></span>
               </div>
               
               <div className="flex-1 overflow-y-auto custom-scrollbar">
                 <table className="w-full text-left table-fixed">
                   <thead className={`sticky top-0 ${isDarkMode ? 'bg-[#1e293b]' : 'bg-white'}`}>
                     <tr className={`text-[10px] border-b ${isDarkMode ? 'border-gray-700 text-gray-400' : 'border-gray-100 text-gray-400'}`}>
                       <th className="font-medium py-2 w-1/4">Time</th>
                       <th className="font-medium py-2 w-1/4">Camera</th>
                       <th className="font-medium py-2 w-1/4">Type</th>
                       <th className="font-medium py-2 w-1/4">Details</th>
                     </tr>
                   </thead>
                   <tbody>
                     {liveEvents.length === 0 && (
                       <tr><td colSpan={4} className={`py-4 text-center text-xs ${tTextSecondary}`}>No recent events found.</td></tr>
                     )}
                     {liveEvents.map((evt) => (
                       <tr key={evt.id} className={`border-b transition-colors ${isDarkMode ? 'border-gray-700/50 hover:bg-slate-700/50' : 'border-gray-50 hover:bg-gray-50'}`}>
                         <td className={`py-2.5 text-[11px] flex items-center gap-1.5 truncate ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                           <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${evt.severity === 'critical' ? 'bg-red-500' : evt.severity === 'medium' ? 'bg-yellow-500' : 'bg-gray-400'}`}/> 
                           {new Date(evt.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                         </td>
                         <td className={`py-2.5 text-[11px] font-medium truncate ${tTextPrimary}`}>{evt.camera_id}</td>
                         <td className={`py-2.5 text-[11px] truncate ${tTextSecondary}`}>{evt.event_type.replace('_',' ')}</td>
                         <td className={`py-2.5 text-[11px] font-bold truncate flex justify-between items-center pr-1 ${evt.severity === 'critical' ? 'text-red-500' : tTextPrimary}`}>
                           <span className="truncate">{evt.confidence ? `Conf ${(evt.confidence*100).toFixed(0)}%` : 'Detected'}</span> 
                           <ChevronRight size={12} className={`${tTextSecondary} shrink-0`}/>
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
            </div>

            {/* Snapshot Gallery */}
            <div className={`col-span-3 rounded-xl flex flex-col overflow-hidden border transition-colors duration-300 ${tCard} p-4`}>
               <div className="flex justify-between items-start mb-3">
                 <div className="flex flex-col">
                   <h2 className={`text-[13px] font-bold flex items-center gap-2 ${tTextPrimary}`}><CameraIcon size={14}/> Snapshot Gallery</h2>
                   <span className={`text-[9px] mt-0.5 ${tTextSecondary}`}>Auto-captured events from Live Feed</span>
                 </div>
                 <span className="text-[10px] font-bold text-blue-500 cursor-pointer hover:underline flex items-center gap-1">View All <ChevronRight size={10}/></span>
               </div>
               
               {snapshots.length === 0 ? (
                 <div className="flex-1 flex flex-col items-center justify-center p-4">
                   <div className={`text-center flex flex-col items-center justify-center ${tTextSecondary}`}>
                     <CameraIcon size={24} className="mb-2 opacity-30" />
                     <p className="text-[11px] font-medium">Waiting for new captures...</p>
                     <p className="text-[9px] opacity-70 mt-1">Click the 'Snapshot' button on any live feed.</p>
                   </div>
                 </div>
               ) : (
                 <div className="flex-1 grid grid-cols-3 gap-3 overflow-y-auto custom-scrollbar p-1">
                   {snapshots.map((snap, idx) => (
                     <div key={idx} onClick={() => setSelectedSnapshot(snap)} className="flex flex-col gap-1.5 group cursor-pointer">
                       <div className={`w-full aspect-video rounded-lg overflow-hidden relative shadow-sm border ${isDarkMode ? 'bg-slate-800 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
                         <img src={snap.url} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"/>
                       </div>
                       <div className="flex flex-col items-center">
                         <span className={`text-[10px] font-bold ${tTextPrimary}`}>{snap.camera}</span>
                         <span className={`text-[8px] ${tTextSecondary}`}>{snap.time}</span>
                       </div>
                     </div>
                   ))}
                 </div>
               )}
            </div>
          </div>

        </div>

        {/* RIGHT SIDEBAR */}
        <div className="w-[320px] shrink-0 flex flex-col gap-3">
          
          {/* AI Copilot Chat Card */}
          <div className={`rounded-xl flex flex-col h-[400px] border transition-colors duration-300 ${tCard} p-0 overflow-hidden shadow-2xl relative`}>
            {/* Background gradient effect for premium feel */}
            <div className={`absolute inset-0 pointer-events-none opacity-20 ${isDarkMode ? 'bg-gradient-to-br from-blue-900/40 via-transparent to-purple-900/20' : 'bg-gradient-to-br from-blue-100 via-transparent to-purple-50'}`}></div>
            
            <div className={`flex justify-between items-center px-4 py-3 border-b shrink-0 z-10 backdrop-blur-md ${isDarkMode ? 'border-gray-700 bg-slate-800/80' : 'border-gray-200 bg-white/80'}`}>
               <h2 className={`text-[14px] font-bold flex items-center gap-2 ${tTextPrimary}`}><Bot size={16} className="text-blue-500"/> Sentinel Copilot AI</h2>
               <span className="bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded-full text-[9px] font-bold flex items-center gap-1 border border-blue-500/20"><span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span> Context Active</span>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-3 p-4 text-[12px]">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 shadow-sm border ${isDarkMode ? 'bg-slate-800 border-gray-700' : 'bg-white border-blue-100'}`}><Bot size={14} className="text-blue-500"/></div>}
                  <div className={`px-4 py-2.5 rounded-2xl max-w-[85%] leading-relaxed shadow-sm backdrop-blur-sm ${msg.role === 'user' ? 'bg-blue-600/90 text-white rounded-tr-sm border border-blue-500/50' : (isDarkMode ? 'bg-slate-700/80 text-gray-100 rounded-tl-sm border border-gray-600/50' : 'bg-white/90 text-gray-800 rounded-tl-sm border border-gray-200/50')}`}>
                    <div className="whitespace-pre-wrap font-medium markdown-body" style={{ letterSpacing: '0.01em', fontSize: '0.95em' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content.replace('[CLIP]', '')}
                      </ReactMarkdown>
                    </div>
                    {msg.content.includes('[CLIP]') && (
                      <div className="mt-3 rounded-lg overflow-hidden border border-gray-500/30 relative shadow-inner">
                        <span className="absolute top-2 left-2 bg-red-600/90 backdrop-blur-sm text-white text-[9px] px-1.5 py-0.5 font-bold rounded-sm flex items-center gap-1 shadow-sm z-10"><span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span> LIVE EVIDENCE CLIP</span>
                        <img 
                          crossOrigin="use-credentials"
                          src={selectedFeedUrl || '/cctv_placeholder.jpg'} 
                          alt="Live Evidence" 
                          className="w-full object-cover max-h-40" 
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex gap-3 justify-start">
                   <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 shadow-sm border ${isDarkMode ? 'bg-slate-800 border-gray-700' : 'bg-white border-blue-100'}`}><Bot size={14} className="text-blue-500"/></div>
                   <div className={`px-4 py-3 rounded-2xl flex items-center gap-1.5 rounded-tl-sm shadow-sm ${isDarkMode ? 'bg-slate-700 border border-gray-600' : 'bg-white border border-gray-100'}`}>
                     <span className="w-1.5 h-1.5 rounded-full animate-bounce bg-blue-500"></span>
                     <span className="w-1.5 h-1.5 rounded-full animate-bounce bg-blue-500" style={{animationDelay: '150ms'}}></span>
                     <span className="w-1.5 h-1.5 rounded-full animate-bounce bg-blue-500" style={{animationDelay: '300ms'}}></span>
                   </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className={`p-3 border-t ${isDarkMode ? 'border-gray-700 bg-slate-800/50' : 'border-gray-200 bg-gray-50/50'}`}>
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Ask Sentinel Copilot..." 
                  className={`w-full text-[12px] pl-4 pr-10 py-2.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all border shadow-sm ${tInput}`}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
                />
                <button 
                  onClick={sendChatMessage}
                  disabled={isChatLoading || !chatInput.trim()}
                  className="absolute right-1.5 top-1.5 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors disabled:opacity-50 shadow-sm"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          </div>

          {/* Live Detected Plates (Real Data) */}
          <div className={`rounded-xl flex flex-col flex-1 min-h-0 overflow-hidden border transition-colors duration-300 ${tCard}`}>
             <div className={`p-4 border-b flex justify-between items-center shrink-0 ${isDarkMode ? 'border-gray-700' : 'border-gray-100'}`}>
               <h2 className={`text-[13px] font-bold flex items-center gap-2 ${tTextPrimary}`}><ShieldAlert size={14} className="text-[#10b981]"/> Live Detected Plates</h2>
               <div className="flex items-center gap-3">
                 <span className={`text-[10px] ${tTextSecondary}`}>{activeVehicles.length} Vehicles</span>
                 <span className="text-[10px] font-bold text-blue-500 cursor-pointer hover:underline flex items-center gap-1">View All <ChevronRight size={10}/></span>
               </div>
             </div>
             
             <div className="p-3 overflow-y-auto custom-scrollbar flex flex-col gap-3">
                {activeVehicles.length === 0 && (
                  <div className={`text-center py-4 text-xs ${tTextSecondary}`}>No active vehicles detected in last 5 mins.</div>
                )}
                
                {activeVehicles.map((veh, idx) => (
                  <div key={idx} className={`border rounded-lg p-2.5 flex items-start gap-3 relative shadow-sm transition-colors group ${isDarkMode ? 'border-gray-700 hover:bg-slate-700/50' : 'border-gray-200 hover:bg-gray-50'}`}>
                     <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-l-lg"></div>
                     <div className={`w-[50px] h-[40px] rounded overflow-hidden shrink-0 border flex items-center justify-center ${isDarkMode ? 'border-gray-600 bg-slate-800' : 'border-gray-200 bg-gray-100'}`}>
                        <Car size={20} className={isDarkMode ? 'text-gray-500' : 'text-gray-400'} />
                     </div>
                     <div className="flex-1 flex flex-col min-w-0">
                       <div className="flex items-center gap-2">
                          <span className={`font-bold text-[13px] tracking-wide ${tTextPrimary}`}>{veh.plate}</span>
                          <span className="bg-blue-500/10 text-blue-500 border border-blue-500/20 text-[8px] font-bold px-1.5 py-0.5 rounded shrink-0 uppercase">TRACKED</span>
                       </div>
                       <span className={`text-[10px] mt-0.5 truncate ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>Sightings: {veh.sightings_last_5min}</span>
                       <div className="flex justify-between items-end mt-1.5">
                         <span className={`text-[9px] ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>{veh.last_camera} • {new Date(veh.last_seen).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                         <button onClick={() => handleTracePlate(veh.plate)} className="text-[10px] font-bold text-blue-500 hover:text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded transition-colors flex items-center gap-1"><Map size={10}/> Trace</button>
                       </div>
                     </div>
                  </div>
                ))}
             </div>
          </div>

          {/* Quick Actions */}
          <div className={`rounded-xl flex flex-col p-4 shrink-0 border transition-colors duration-300 ${tCard}`}>
            <h2 className={`text-[13px] font-bold flex items-center gap-2 mb-3 ${tTextPrimary}`}><SlidersHorizontal size={14}/> Quick Actions</h2>
            <div className="flex flex-col gap-2">
              <button onClick={() => { setViewMode("MAP"); showToast("Opening Watchlist Database..."); handleWatchlist(); }} className={`w-full py-2 px-3 text-[11px] font-bold rounded-lg flex items-center gap-2 transition-colors border shadow-sm ${tButtonAction}`}><Upload size={14} className={tTextSecondary}/> Upload Media for ANPR</button>
              <button onClick={handleStatewideTrace} className={`w-full py-2 px-3 text-[11px] font-bold rounded-lg flex items-center gap-2 transition-colors border shadow-sm ${tButtonAction}`}><Map size={14} className={tTextSecondary}/> Statewide ANPR Trace Map</button>
              <div className="flex gap-2">
                <button onClick={handleWatchlist} className={`flex-1 py-2 px-3 text-[11px] font-bold rounded-lg flex items-center justify-center gap-2 transition-colors border shadow-sm ${tButtonAction}`}><Search size={14} className={tTextSecondary}/> Watchlist</button>
                <button onClick={handleGenerateReport} className={`flex-1 py-2 px-3 bg-[#10b981]/10 border border-[#10b981]/20 text-[#10b981] text-[11px] font-bold rounded-lg flex items-center justify-center gap-2 hover:bg-[#10b981]/20 active:bg-[#10b981]/30 transition-colors shadow-sm`}><FileBarChart size={14} className="text-[#10b981]"/> PDF Report</button>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Snapshot Modal */}
      {selectedSnapshot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-8" onClick={() => setSelectedSnapshot(null)}>
          <div className="relative max-w-5xl w-full max-h-full flex flex-col items-center justify-center" onClick={e => e.stopPropagation()}>
            <img src={selectedSnapshot.url} className="max-w-full max-h-[85vh] rounded-lg shadow-2xl border border-gray-700 object-contain" />
            <div className="mt-4 flex gap-4">
              <button 
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-bold text-sm shadow-lg flex items-center gap-2 transition-colors"
                onClick={() => {
                  const a = document.createElement('a');
                  a.href = selectedSnapshot.url;
                  a.download = `snapshot_${selectedSnapshot.camera}_${selectedSnapshot.time.replace(/:/g, '-')}.jpg`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                }}
              >
                <Download size={16} /> Download
              </button>
              <button onClick={() => setSelectedSnapshot(null)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-bold text-sm shadow-lg transition-colors">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
