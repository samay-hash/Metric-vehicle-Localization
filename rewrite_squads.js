const fs = require('fs');
const filePath = '/Users/samaysamrat/bankcctv/frontend/src/components/landing/marketing/Squads.tsx';

let content = fs.readFileSync(filePath, 'utf8');

const newSquads = `const squads: Squad[] = [
  {
    id: "sitegpt",
    pill: "Command Center",
    label: "Gujarat Police Command Center",
    count: "80,000 cameras",
    image: "/marketing/squad-canvas-hills.jpg",
    blurb:
      "Centralized monitoring platform actively parsing feeds from isolated departments and deploying real-time AI to identify threats before they escalate.",
    agents: [
      { icon: SparklesIcon, name: "Sentinel Lead", role: "AI Coordinator", lead: true },
      { icon: Search01Icon, name: "YOLOv8 Edge", role: "Edge Filtering" },
      { icon: Analytics01Icon, name: "LLaVA VLM", role: "Threat Analyst" },
      { icon: PaintBoardIcon, name: "WebSockets", role: "Telemetry Sync" },
      { icon: CodeIcon, name: "ANPR Tracker", role: "Vehicle Tracking" },
      { icon: Mail01Icon, name: "VAHAN DB", role: "Watchlist Matcher" },
    ],
    time: "11:42 PM",
    model: "Local LLaVA",
    prompt: "Track vehicle MH-12-1234 across North Zone",
    deliverableCount: "43 matches found",
    missionTarget: "City-Wide Vehicle Tracking",
    brief:
      "Analyzed 12,000 vehicles across North Zone cameras. 43 potential matches detected. Suspect vehicle identified near highway exit 5 mins ago.",
    diagnostic: {
      badge: "High Priority Alert",
      text: "Suspect vehicle matched against VAHAN database with 98% confidence.",
    },
    approvals: [
      {
        id: "sitegpt-1",
        title: "Dispatch Patrol Unit",
        description:
          "Automatically alert the nearest patrol unit to Highway Exit 4",
        tag: "Action",
        leadIcon: QuillWrite01Icon,
        assignees: "Sentinel & Control",
        actionLabel: "Dispatch Now",
      },
      {
        id: "sitegpt-2",
        title: "Elevate Threat Level",
        description:
          "Broadcast vehicle details to all surrounding edge nodes for priority tracking",
        tag: "Tracking",
        leadIcon: Mail01Icon,
        assignees: "YOLOv8 & WebSockets",
        actionLabel: "Elevate Priority",
      },
    ],
    quickReplies: ["Dispatch units instantly", "Show camera feed"],
    statusNote: "2 actions pending · 43 matches found",
    userName: "Operator",
    userImage: "/marketing/founders/bhanu.jpg",
    thread: [
      { id: "sitegpt-m1", role: "user", text: "Track vehicle MH-12-1234 across North Zone" },
      {
        id: "sitegpt-m2",
        role: "agent",
        text: "Vehicle detected near Highway Exit 4. Matching with VAHAN complete. Dispatch units?",
      },
    ],
  },
  {
    id: "govpitch",
    pill: "Bank Security",
    label: "Global Bank Operations",
    count: "1,200 branches",
    image: "/marketing/squad-canvas-canyon.jpg",
    blurb:
      "Securing high-value vaults and cash counters. Edge AI drops normal traffic and only alerts on loitering or unauthorized access.",
    agents: [
      {
        icon: SparklesIcon,
        name: "Vault Guard",
        role: "Security Lead",
        lead: true,
      },
      { icon: Coins01Icon, name: "Cash Monitor", role: "Transaction Sync" },
      { icon: Hospital01Icon, name: "Entry Scanner", role: "Biometrics" },
    ],
    time: "2:05 AM",
    model: "YOLOv8 + VLM",
    prompt: "Any after-hours movement in Vault 3?",
    deliverableCount: "4 branches scanned",
    missionTarget: "After-hours Vault Monitoring",
    brief:
      "Edge nodes processed 4 hours of footage instantly. Vault 3 is secure, but one person lingered near the lobby for 5 mins.",
    diagnostic: {
      badge: "Anomaly Detected",
      text: "Unauthorized loitering identified outside secure zone.",
    },
    approvals: [
      {
        id: "govpitch-1",
        title: "Lockdown Lobby Doors",
        description:
          "Engage magnetic locks on all lobby entry points",
        tag: "Security",
        leadIcon: Hospital01Icon,
        assignees: "Vault Guard & Entry Scanner",
        actionLabel: "Lockdown Now",
      },
    ],
    quickReplies: ["Engage lockdown", "View lobby feed"],
    statusNote: "1 alert pending · 4 branches scanned",
    userName: "Operator",
    thread: [
      { id: "govpitch-m1", role: "user", text: "Any after-hours movement in Vault 3?" },
      {
        id: "govpitch-m2",
        role: "agent",
        text: "Vault 3 is secure. One person lingered near the lobby for 5 mins.",
      },
    ],
  },
  {
    id: "agency",
    pill: "Traffic Control",
    label: "Smart City Traffic Management",
    count: "12,000 junctions",
    image: "/marketing/squad-canvas-waves.jpg",
    blurb:
      "Real-time congestion tracking and accident detection without sending heavy video to the cloud.",
    agents: [
      { icon: Target01Icon, name: "Traffic Lead", role: "Coordinator", lead: true },
      { icon: Search01Icon, name: "Crash Detect", role: "YOLOv8 Edge" },
      { icon: ToolsIcon, name: "Congestion Sync", role: "Telemetry" },
    ],
    time: "4:20 PM",
    model: "Local AI",
    prompt: "Report accidents on Ring Road",
    deliverableCount: "1 collision detected",
    missionTarget: "Ring Road Collision Detection",
    brief:
      "Edge nodes on Ring Road North reported a sudden stop in traffic flow. VLM analysis confirms a two-vehicle collision.",
    diagnostic: {
      badge: "Accident Confirmed",
      text: "Two-vehicle collision. Emergency services not yet present.",
    },
    approvals: [
      {
        id: "agency-1",
        title: "Dispatch Ambulance",
        description:
          "Send nearest emergency services to Ring Road North junction",
        tag: "Emergency",
        leadIcon: ToolsIcon,
        assignees: "Traffic Lead & Crash Detect",
        actionLabel: "Dispatch Services",
      },
    ],
    quickReplies: ["Dispatch ambulance", "Show live feed"],
    statusNote: "1 emergency pending",
    userName: "Operator",
    thread: [
      { id: "agency-m1", role: "user", text: "Report accidents on Ring Road" },
      {
        id: "agency-m2",
        role: "agent",
        text: "One collision detected on Ring Road North. Ambulance notified.",
      },
    ],
  }
];`;

const startIndex = content.indexOf('const squads: Squad[] = [');
const endIndex = content.indexOf('];', startIndex) + 2;

if (startIndex !== -1 && endIndex !== -1) {
    content = content.substring(0, startIndex) + newSquads + content.substring(endIndex);
    fs.writeFileSync(filePath, content);
    console.log("Successfully replaced squads array.");
} else {
    console.log("Failed to find squads array.");
}
