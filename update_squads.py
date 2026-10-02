import os
file_path = "/Users/samaysamrat/Downloads/Infra-camera-main 3/frontend/src/components/landing/marketing/Squads.tsx"

with open(file_path, "r") as f:
    content = f.read()

new_squads = """const squads: Squad[] = [
  {
    id: "sitegpt",
    pill: "Stage 1",
    label: "Baseline Approach",
    count: "Center-pixel sampling",
    image: "/marketing/squad-canvas-hills.jpg",
    blurb:
      "A simple baseline using the bounding box center pixel to sample depth from the DepthAnything v2 output.",
    agents: [
      { icon: SparklesIcon, name: "Input", role: "Image + Intrinsics", lead: true },
      { icon: Search01Icon, name: "DepthAny v2", role: "Relative Depth" },
      { icon: Analytics01Icon, name: "Center Sampler", role: "Depth Aggregation" },
      { icon: CodeIcon, name: "Pinhole Math", role: "X, Z Estimate" }
    ],
    time: "Baseline",
    model: "DepthAnything v2",
    prompt: "Sample depth at bounding box center",
    deliverableCount: "MAE_Z ~18.5m",
    missionTarget: "Establish Baseline Error",
    brief:
      "Center-pixel sampling is fast but highly susceptible to noise, especially if the center pixel falls on the windshield (reflecting the sky) or the road behind a truck.",
    diagnostic: {
      badge: "Baseline Metrics",
      text: "Shows significant error on far and occluded vehicles due to single-pixel noise.",
    },
    approvals: [
      {
        id: "sitegpt-1",
        title: "Identify Failure Cases",
        description: "Windshield reflections and bounding box misalignments cause severe depth spikes.",
        tag: "Analysis",
        leadIcon: QuillWrite01Icon,
        assignees: "Evaluator",
        actionLabel: "View Failures",
      }
    ],
    quickReplies: ["View Method A", "See Metrics"],
    statusNote: "Baseline established",
    userName: "Evaluator",
    thread: [
      { id: "sitegpt-m1", role: "user", text: "Run Method A (Center Pixel)" },
      {
        id: "sitegpt-m2",
        role: "agent",
        text: "Baseline execution complete. MAE_Z is high on occluded targets.",
      },
    ],
  },
  {
    id: "govpitch",
    pill: "Stage 2",
    label: "Improved Method",
    count: "Robust Aggregation",
    image: "/marketing/squad-canvas-canyon.jpg",
    blurb:
      "Improved sampling strategy that aggregates the lower half of the bounding box using a trimmed median to avoid windshield reflections and background noise.",
    agents: [
      {
        icon: SparklesIcon,
        name: "Lower-Half BBox",
        role: "Masking",
        lead: true,
      },
      { icon: Coins01Icon, name: "Trimmed Median", role: "Outlier Rejection" },
      { icon: Hospital01Icon, name: "Vehicle Prior", role: "Width ~1.8m" },
    ],
    time: "Improved",
    model: "DepthAnything + Prior",
    prompt: "Apply trimmed median on lower bounding box",
    deliverableCount: "MAE_Z ~5.7m",
    missionTarget: "Improve Depth Reliability",
    brief:
      "By isolating the vehicle body (lower half) and discarding the top and bottom 10% depth values, we recover a highly stable depth estimate robust to occlusions.",
    diagnostic: {
      badge: "Meaningful Improvement",
      text: "Significant reduction in MAE_Z and P90 tail errors.",
    },
    approvals: [
      {
        id: "govpitch-1",
        title: "Geometric Verification",
        description:
          "Combine depth output with a geometric width prior (~1.8m) for scale recovery.",
        tag: "Geometry",
        leadIcon: Hospital01Icon,
        assignees: "Pinhole Model",
        actionLabel: "Verify Scale",
      },
    ],
    quickReplies: ["View Method C", "See Ablation"],
    statusNote: "Experiment successful",
    userName: "Evaluator",
    thread: [
      { id: "govpitch-m1", role: "user", text: "Apply trimmed median and vehicle prior" },
      {
        id: "govpitch-m2",
        role: "agent",
        text: "Method C complete. Substantial error reduction achieved.",
      },
    ],
  }
];"""

start_str = "const squads: Squad[] = ["
end_str = "];"
start_idx = content.find(start_str)

if start_idx != -1:
    end_idx = content.find(end_str, start_idx)
    if end_idx != -1:
        end_idx += len(end_str)
        new_content = content[:start_idx] + new_squads + content[end_idx:]
        with open(file_path, "w") as f:
            f.write(new_content)
        print("Success")
    else:
        print("End not found")
else:
    print("Start not found")
