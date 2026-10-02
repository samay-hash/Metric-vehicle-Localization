import re

file_path = "/Users/samaysamrat/bankcctv/frontend/src/components/landing/marketing/Integrations.tsx"

with open(file_path, "r") as f:
    content = f.read()

# Update Category type
content = re.sub(r'type Category = "all" \| "sales" \| "communication" \| "productivity" \| "ai";', 
                 'type Category = "all" | "databases" | "alerts" | "storage" | "ai";', content)

# Update categories array
new_categories = """const categories: { id: Category; label: string }[] = [
  { id: "all", label: "All" },
  { id: "databases", label: "Databases & APIs" },
  { id: "alerts", label: "Alerts & Comms" },
  { id: "storage", label: "Video & Storage" },
  { id: "ai", label: "AI Models" },
];"""
content = re.sub(r'const categories: \{ id: Category; label: string \}.*?\];', new_categories, content, flags=re.DOTALL)

# Add Iconify import if not exists
if "import { Icon } from" not in content:
    content = content.replace('import { Section }', 'import { Icon } from "@iconify/react";\nimport { Section }')

# Define new icons
new_icons = """
const VahanIcon = ({ className }: { className?: string }) => <Icon icon="lucide:car" className={className} />;
const PoliceIcon = ({ className }: { className?: string }) => <Icon icon="lucide:shield-check" className={className} />;
const FingerprintIcon = ({ className }: { className?: string }) => <Icon icon="lucide:fingerprint" className={className} />;
const CameraIcon = ({ className }: { className?: string }) => <Icon icon="lucide:cctv" className={className} />;
const ServerIcon = ({ className }: { className?: string }) => <Icon icon="lucide:server" className={className} />;
const HardDriveIcon = ({ className }: { className?: string }) => <Icon icon="lucide:hard-drive" className={className} />;
const BrainIcon = ({ className }: { className?: string }) => <Icon icon="lucide:brain" className={className} />;
const ScanIcon = ({ className }: { className?: string }) => <Icon icon="lucide:scan" className={className} />;
"""

# Place new icons before integrations array
integrations_start = content.find('const integrations: Integration[] = [')
content = content[:integrations_start] + new_icons + content[integrations_start:]

# Update integrations array
new_integrations = """const integrations: Integration[] = [
  {
    name: "VAHAN Registry",
    body: "Instantly cross-references detected number plates with the national vehicle registry.",
    icon: VahanIcon,
    category: "databases",
  },
  {
    name: "eGujCop",
    body: "Direct sync with Gujarat Police crime database for real-time suspect matching.",
    icon: PoliceIcon,
    category: "databases",
  },
  {
    name: "NAFIS",
    body: "Automated Fingerprint Identification System integration for biometric verification.",
    icon: FingerprintIcon,
    category: "databases",
  },
  {
    name: "WhatsApp API",
    body: "Pushes critical video snippets directly to the nearest patrol unit's phone.",
    icon: WhatsAppIcon,
    category: "alerts",
  },
  {
    name: "Slack",
    body: "Dedicated channels for command center coordination and threat escalation.",
    icon: SlackIcon,
    category: "alerts",
  },
  {
    name: "Milestone VMS",
    body: "Seamlessly pulls RTSP streams from your existing Milestone servers.",
    icon: CameraIcon,
    category: "storage",
  },
  {
    name: "Genetec",
    body: "Native plugin to ingest and analyze Genetec camera grids without replacing hardware.",
    icon: ServerIcon,
    category: "storage",
  },
  {
    name: "Local NAS / S3",
    body: "Archives verified anomalies locally to comply with strict data privacy laws.",
    icon: HardDriveIcon,
    category: "storage",
  },
  {
    name: "Local LLaVA",
    body: "On-premise Vision Language Model for contextual scene understanding without cloud.",
    icon: BrainIcon,
    category: "ai",
  },
  {
    name: "YOLOv8 Edge",
    body: "Edge-optimized object detection running at 190 FPS on low-power nodes.",
    icon: ScanIcon,
    category: "ai",
  },
];"""

content = re.sub(r'const integrations: Integration\[\] = \[.*?\];', new_integrations, content, flags=re.DOTALL)

# Update Section Header text
content = content.replace('heading="They log into Slack, Gmail, Stripe, GitHub."', 'heading="Plug and play with your existing infrastructure."')
content = content.replace('description="70+ apps. Access is set per employee. Nothing sends until you tap it."', 'description="Seamlessly integrates with national databases, VMS platforms, and command center comms."')

with open(file_path, "w") as f:
    f.write(content)

print("Replacement successful")
