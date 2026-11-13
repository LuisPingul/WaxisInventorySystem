#!/usr/bin/env python3
"""
INVENTIQ (WaxisInventorySystem) — Automated Product Demo Video Generator
========================================================================
Stitches together application screen captures into a branded 1920x1080 Full HD
product pitch video complete with:
  - Exact scene-by-scene timestamps (0:00 to 2:00)
  - Waxi's brand styling (#871F09 Maroon, #FE5F10 Orange, #FED216 Gold)
  - Rounded browser window chrome + smooth Ken Burns zoom motion
  - Smooth crossfade transitions between scenes
  - On-screen text overlays (Top feature badge, Lower-Third headline, VO captions)
  - Automated voiceover synthesis (macOS `say` TTS) & H.264 MP4 encoding
  - High-res storyboard PNG keyframes for Google Flow / Veo / CapCut

Usage:
  /usr/bin/python3 scripts/generate_demo_video.py
  /usr/bin/python3 scripts/generate_demo_video.py --no-audio
  /usr/bin/python3 scripts/generate_demo_video.py --fps 12 --output media/demo_video/inventiq_demo_video.mp4
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print(
        "ERROR: Pillow (PIL) is required. Run with `/usr/bin/python3` or `pip install Pillow`.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Brand Tokens & Canvas Configuration
# ---------------------------------------------------------------------------
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

COLOR_MAROON = (135, 31, 9)        # #871F09 — Primary Brand Maroon
COLOR_DARK_BG = (32, 8, 4)         # #200804 — Deep Espresso Canvas
COLOR_ORANGE = (254, 95, 16)       # #FE5F10 — Electric Orange Accent
COLOR_GOLD = (254, 210, 22)        # #FED216 — Warm Amber Gold
COLOR_CREAM = (253, 248, 244)      # #FDF8F4 — Warm Cream Surface
COLOR_CHARCOAL = (30, 41, 59)      # #1E293B — Slate Charcoal
COLOR_MUTED = (203, 213, 225)      # #CBD5E1 — Light Slate Text
COLOR_WHITE = (255, 255, 255)


@dataclass
class SceneSpec:
    scene_number: int
    timestamp_label: str
    duration_sec: float
    image_rel_path: Optional[str]
    url_bar: str
    top_badge: str
    headline: str
    subtitle: str
    voiceover: str
    zoom_start: float = 1.00
    zoom_end: float = 1.05


# ---------------------------------------------------------------------------
# Master 2-Minute (120s) Storyboard Definition
# ---------------------------------------------------------------------------
SCENES: List[SceneSpec] = [
    SceneSpec(
        scene_number=1,
        timestamp_label="0:00 – 0:12",
        duration_sec=12.0,
        image_rel_path="static/demo_captures/01_login.png",
        url_bar="https://inventiq.waxis.ph/accounts/login/",
        top_badge="SHD FOODS INTERNATIONAL INC. • WAXI'S",
        headline="INVENTIQ: Enterprise Kitchen Intelligence",
        subtitle="Role-Based Access Control (Owner • Manager • Crew) + Standalone PWA",
        voiceover=(
            "In fast-paced food-service operations, a single unexpected stockout "
            "halts the entire kitchen line. Meet INVENTIQ—an enterprise Progressive "
            "Web App purpose-built for Waxi's to eliminate stockouts, automate "
            "procurement, and track every gram in real time."
        ),
        zoom_start=1.00,
        zoom_end=1.05,
    ),
    SceneSpec(
        scene_number=2,
        timestamp_label="0:12 – 0:30",
        duration_sec=18.0,
        image_rel_path="static/demo_captures/02_crew_deduct.jpg",
        url_bar="https://inventiq.waxis.ph/inventory/deduct/",
        top_badge="ROLE: KITCHEN CREW • ZERO-TYPO UX",
        headline="5-Second Stock Deduction on Kitchen Tablets",
        subtitle="48px Touch Targets • +1 / +5 / +10 / Max Quick Pills • Automatic Zero-Stock Lock",
        voiceover=(
            "For kitchen crew on the line, speed is everything. Crew members log "
            "into a distraction-free, two-tab workspace designed for tablets. With "
            "forty-eight-pixel touch targets and one-tap increment pills, deducting "
            "ingredients takes under five seconds—while zero-stock items automatically "
            "lock to prevent negative inventory."
        ),
        zoom_start=1.00,
        zoom_end=1.06,
    ),
    SceneSpec(
        scene_number=3,
        timestamp_label="0:30 – 0:50",
        duration_sec=20.0,
        image_rel_path="static/demo_captures/03_owner_dashboard.jpg",
        url_bar="https://inventiq.waxis.ph/dashboard/owner/",
        top_badge="ROLE: BUSINESS OWNER • EXECUTIVE TELEMETRY",
        headline="Live Operational Health Score & Executive Briefing",
        subtitle="Instant Triage Across Stock Depletion, Pending PRs, and Cold-Chain Exposure",
        voiceover=(
            "Owners get an instant pulse on the business without digging through "
            "spreadsheets. The Executive Operations Briefing computes a live "
            "zero-to-one-hundred Operational Health Score—synthesizing critical stock "
            "depletion, pending purchase approvals, and cold-chain exposure into one "
            "actionable directive."
        ),
        zoom_start=1.00,
        zoom_end=1.05,
    ),
    SceneSpec(
        scene_number=4,
        timestamp_label="0:50 – 1:10",
        duration_sec=20.0,
        image_rel_path="static/demo_captures/04_manager_dashboard.png",
        url_bar="https://inventiq.waxis.ph/dashboard/manager/",
        top_badge="ROLE: OPERATIONS MANAGER • DAILY COMMAND",
        headline="Cold-Chain Distribution & 30-Day Demand Curves",
        subtitle="Real-Time Dry / Chilled / Frozen Telemetry & Supplier Delivery Window Radar",
        voiceover=(
            "For store managers, the aligned command center pairs real-time "
            "cold-chain storage distribution and thirty-day consumption spikes with "
            "the Agrilytics Procurement Radar—flagging exactly which suppliers are "
            "entering their active delivery window today."
        ),
        zoom_start=1.00,
        zoom_end=1.05,
    ),
    SceneSpec(
        scene_number=5,
        timestamp_label="1:10 – 1:30",
        duration_sec=20.0,
        image_rel_path="static/demo_captures/05_forecast_predictions.png",
        url_bar="https://inventiq.waxis.ph/forecast/",
        top_badge="DUAL-MODE FORECAST ENGINE • PHP 0 API COST",
        headline="30-Day Burn-Rate + Supplier Rhythm Prediction",
        subtitle="Pure-Python Statistical Engine • Zero External Paid AI Dependencies",
        voiceover=(
            "Under the hood, INVENTIQ runs a pure-Python, dual-mode forecasting "
            "engine with zero recurring AI API costs. It combines each ingredient's "
            "thirty-day rolling burn rate with historical supplier inter-arrival "
            "times—accurately predicting stockout dates and optimal reorder quantities."
        ),
        zoom_start=1.00,
        zoom_end=1.06,
    ),
    SceneSpec(
        scene_number=6,
        timestamp_label="1:30 – 1:46",
        duration_sec=16.0,
        image_rel_path="static/demo_captures/06_procurement_dispatch.png",
        url_bar="https://inventiq.waxis.ph/procurement/",
        top_badge="CLOSED-LOOP PROCUREMENT • VIBER & EMAIL PO",
        headline="From AI Alert to Supplier Dispatch in 3 Clicks",
        subtitle="1-Click Convert to PR • Instant Approval • Formatted Viber & Email Purchase Orders",
        voiceover=(
            "With one click, managers convert any forecast alert into a pre-filled "
            "Purchase Request. Once approved, INVENTIQ generates a formatted Purchase "
            "Order ready for instant dispatch via Viber or email—closing the loop "
            "from kitchen deduction to warehouse restock."
        ),
        zoom_start=1.00,
        zoom_end=1.05,
    ),
    SceneSpec(
        scene_number=7,
        timestamp_label="1:46 – 2:00",
        duration_sec=14.0,
        image_rel_path="static/demo_captures/03_owner_dashboard.jpg",
        url_bar="https://inventiq.waxis.ph/ — UN SDG 12.3 & Cloud-Native PWA",
        top_badge="UN SDG 12.3 ALIGNED • CLOUD-NATIVE PWA",
        headline="INVENTIQ — Smart Inventory Management System",
        subtitle="Zero-Cost Forecasting • Peso Waste Analytics • Immutable Audit Trail • Offline-Ready PWA",
        voiceover=(
            "Complete with Peso-denominated SDG-twelve waste analytics, immutable "
            "audit logs, and offline PWA resilience, INVENTIQ transforms restaurant "
            "inventory into a competitive advantage. INVENTIQ—smart inventory, "
            "engineered for Waxi's."
        ),
        zoom_start=1.03,
        zoom_end=1.00,
    ),
]


# ---------------------------------------------------------------------------
# Font Loader Helper
# ---------------------------------------------------------------------------
def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Loads a clean system sans-serif font on macOS/Linux/Windows with fallback."""
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Frame Compositor
# ---------------------------------------------------------------------------
def build_base_background(width: int, height: int) -> Image.Image:
    """Creates a rich Waxi's Maroon & Espresso gradient canvas."""
    bg = Image.new("RGB", (width, height), COLOR_DARK_BG)
    draw = ImageDraw.Draw(bg)
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(COLOR_MAROON[0] * (1 - t * 0.72) + COLOR_DARK_BG[0] * (t * 0.72))
        g = int(COLOR_MAROON[1] * (1 - t * 0.72) + COLOR_DARK_BG[1] * (t * 0.72))
        b = int(COLOR_MAROON[2] * (1 - t * 0.72) + COLOR_DARK_BG[2] * (t * 0.72))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return bg


def clean_screenshot_crop(img: Image.Image) -> Image.Image:
    """
    If a screenshot includes the macOS Chrome top tab/address bar (e.g. 1024x640 full window),
    crops the top browser chrome so all scenes share a clean, consistent app viewport.
    """
    w, h = img.size
    # Check if top-left pixel is dark gray/black (macOS dark menu bar + Chrome tabs)
    top_pixel = img.convert("RGB").getpixel((w // 2, 8))
    if sum(top_pixel) < 180 and h >= 540:
        crop_top = int(h * 0.135)
        return img.crop((0, crop_top, w, h))
    return img


def render_scene_frame(
    base_bg: Image.Image,
    scene: SceneSpec,
    screenshot_img: Image.Image,
    scene_progress: float,
    global_progress: float,
    total_scenes: int,
) -> Image.Image:
    """
    Renders a single 1920x1080 frame for `scene` at `scene_progress` (0.0 -> 1.0).
    """
    frame = base_bg.copy()
    draw = ImageDraw.Draw(frame, "RGBA")

    font_badge = load_font(20, bold=True)
    font_url = load_font(18, bold=False)
    font_headline = load_font(36, bold=True)
    font_subtitle = load_font(22, bold=False)
    font_vo = load_font(22, bold=True)

    # 1. Top Header Bar (Scene indicator + Timestamp + Feature Badge)
    top_y = 26
    scene_pill_text = f"SCENE 0{scene.scene_number} / 0{total_scenes}   •   {scene.timestamp_label}"
    draw.rounded_rectangle(
        (60, top_y, 430, top_y + 44),
        radius=22,
        fill=(254, 95, 16, 235),
    )
    draw.text((84, top_y + 10), scene_pill_text, fill=COLOR_WHITE, font=font_badge)

    # Right-side Top Feature Badge
    badge_w = int(draw.textlength(scene.top_badge, font=font_badge)) + 48
    draw.rounded_rectangle(
        (VIDEO_WIDTH - 60 - badge_w, top_y, VIDEO_WIDTH - 60, top_y + 44),
        radius=22,
        fill=(30, 41, 59, 210),
        outline=(254, 210, 22, 180),
        width=2,
    )
    draw.text(
        (VIDEO_WIDTH - 60 - badge_w + 24, top_y + 10),
        scene.top_badge,
        fill=COLOR_GOLD,
        font=font_badge,
    )

    # 2. Browser Viewport Card (Center stage: x=60..1860, y=88..838)
    card_x, card_y = 60, 88
    card_w, card_h = 1800, 748
    header_h = 44

    # Soft shadow behind browser window
    draw.rounded_rectangle(
        (card_x + 8, card_y + 10, card_x + card_w + 8, card_y + card_h + 10),
        radius=18,
        fill=(0, 0, 0, 110),
    )

    # Browser top chrome bar
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        radius=16,
        fill=COLOR_CREAM,
        outline=(255, 255, 255, 60),
        width=2,
    )
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + header_h),
        radius=16,
        fill=(30, 41, 59, 255),
    )
    draw.rectangle(
        (card_x, card_y + header_h - 16, card_x + card_w, card_y + header_h),
        fill=(30, 41, 59, 255),
    )

    # Traffic light dots
    for idx, dot_color in enumerate([(239, 68, 68), (245, 158, 11), (16, 185, 129)]):
        cx = card_x + 26 + idx * 22
        cy = card_y + header_h // 2
        draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=dot_color)

    # URL bar pill inside browser header
    draw.rounded_rectangle(
        (card_x + 110, card_y + 8, card_x + card_w - 110, card_y + header_h - 8),
        radius=8,
        fill=(15, 23, 42, 255),
    )
    draw.text(
        (card_x + 130, card_y + 11),
        scene.url_bar,
        fill=COLOR_MUTED,
        font=font_url,
    )

    # 3. Render Screenshot with Smooth Ken Burns Zoom inside Viewport
    vp_w = card_w - 4
    vp_h = card_h - header_h - 2
    zoom = scene.zoom_start + (scene.zoom_end - scene.zoom_start) * (
        0.5 - 0.5 * math.cos(math.pi * scene_progress)
    )

    # Fit screenshot aspect-ratio-preserving onto Cream canvas, then apply zoom
    fitted = Image.new("RGB", (vp_w, vp_h), COLOR_CREAM)
    src_w, src_h = screenshot_img.size
    scale = min(vp_w / src_w, vp_h / src_h) * zoom
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized_shot = screenshot_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    paste_x = (vp_w - new_w) // 2
    paste_y = (vp_h - new_h) // 2
    fitted.paste(resized_shot, (paste_x, paste_y))
    frame.paste(fitted, (card_x + 2, card_y + header_h))

    # 4. Lower-Third Overlay Banner (Headline + Subtitle + Voiceover Closed Captions)
    lt_x, lt_y = 60, 854
    lt_w, lt_h = 1800, 196
    draw.rounded_rectangle(
        (lt_x, lt_y, lt_x + lt_w, lt_y + lt_h),
        radius=16,
        fill=(20, 10, 8, 238),
        outline=(254, 95, 16, 190),
        width=2,
    )
    # Left Orange Accent Bar
    draw.rounded_rectangle(
        (lt_x + 16, lt_y + 18, lt_x + 26, lt_y + lt_h - 18),
        radius=5,
        fill=COLOR_ORANGE,
    )

    # Headline & Subtitle
    draw.text(
        (lt_x + 46, lt_y + 18),
        scene.headline,
        fill=COLOR_WHITE,
        font=font_headline,
    )
    draw.text(
        (lt_x + 46, lt_y + 64),
        scene.subtitle,
        fill=COLOR_GOLD,
        font=font_subtitle,
    )

    # Voiceover Caption Box (synchronizes active sentence segment with scene_progress)
    words = scene.voiceover.split()
    chunk_size = max(14, (len(words) + 1) // 2)
    chunks = [
        " ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)
    ]
    active_chunk_idx = min(len(chunks) - 1, int(scene_progress * len(chunks)))
    active_vo_line = f'VO: "{chunks[active_chunk_idx]}"'

    draw.rounded_rectangle(
        (lt_x + 46, lt_y + 104, lt_x + lt_w - 28, lt_y + lt_h - 16),
        radius=10,
        fill=(30, 41, 59, 210),
    )
    wrapped_vo = textwrap.wrap(active_vo_line, width=112)[:2]
    for line_idx, line in enumerate(wrapped_vo):
        draw.text(
            (lt_x + 64, lt_y + 114 + line_idx * 28),
            line,
            fill=COLOR_CREAM,
            font=font_vo,
        )

    # 5. Bottom Global Timeline Progress Bar
    bar_y = VIDEO_HEIGHT - 12
    draw.rectangle((0, bar_y, VIDEO_WIDTH, VIDEO_HEIGHT), fill=(15, 23, 42, 255))
    prog_w = int(VIDEO_WIDTH * max(0.0, min(1.0, global_progress)))
    if prog_w > 0:
        draw.rectangle((0, bar_y, prog_w, VIDEO_HEIGHT), fill=COLOR_ORANGE)

    return frame


# ---------------------------------------------------------------------------
# macOS Native Swift / AVFoundation MP4 Encoder + `say` Voiceover Synthesizer
# ---------------------------------------------------------------------------
SWIFT_MP4_ENCODER = r"""
import AVFoundation
import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count >= 4 else {
    fputs("Usage: encode_mp4 <manifest.txt> <output.mp4> <fps> [audio.m4a]\n", stderr)
    exit(1)
}

let manifestPath = args[1]
let outputPath = args[2]
let fps = Int32(args[3]) ?? 10
let audioPath: String? = args.count >= 5 ? args[4] : nil

let width = 1920
let height = 1080

let fm = FileManager.default
if fm.fileExists(atPath: outputPath) {
    try? fm.removeItem(atPath: outputPath)
}

let content = try String(contentsOfFile: manifestPath, encoding: .utf8)
let lines = content.split(separator: "\n").map { String($0) }.filter { !$0.isEmpty }

let tempVideoPath = outputPath + ".video_only.mp4"
if fm.fileExists(atPath: tempVideoPath) {
    try? fm.removeItem(atPath: tempVideoPath)
}

let videoURL = URL(fileURLWithPath: tempVideoPath)
let writer = try AVAssetWriter(outputURL: videoURL, fileType: .mp4)

let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
]
let writerInput = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
writerInput.expectsMediaDataInRealTime = false

let attrs: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32ARGB),
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
]
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: writerInput,
    sourcePixelBufferAttributes: attrs
)

writer.add(writerInput)
writer.startWriting()
writer.startSession(atSourceTime: .zero)

var frameIndex: Int64 = 0
for line in lines {
    let parts = line.split(separator: "|").map { String($0) }
    guard parts.count == 2, let repeatCount = Int(parts[1]) else { continue }
    let imgPath = parts[0]
    guard let nsImage = NSImage(contentsOfFile: imgPath) else { continue }

    var rect = CGRect(x: 0, y: 0, width: width, height: height)
    guard let cgImage = nsImage.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { continue }

    var pixelBufferOut: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, adaptor.pixelBufferPool!, &pixelBufferOut)
    guard let pixelBuffer = pixelBufferOut else { continue }

    CVPixelBufferLockBaseAddress(pixelBuffer, [])
    let data = CVPixelBufferGetBaseAddress(pixelBuffer)
    let rgbColorSpace = CGColorSpaceCreateDeviceRGB()
    if let context = CGContext(
        data: data,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(pixelBuffer),
        space: rgbColorSpace,
        bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue
    ) {
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
    }
    CVPixelBufferUnlockBaseAddress(pixelBuffer, [])

    for _ in 0..<repeatCount {
        while !writerInput.isReadyForMoreMediaData {
            Thread.sleep(forTimeInterval: 0.005)
        }
        let presentationTime = CMTimeMake(value: frameIndex, timescale: fps)
        adaptor.append(pixelBuffer, withPresentationTime: presentationTime)
        frameIndex += 1
    }
}

writerInput.markAsFinished()
let sema = DispatchSemaphore(value: 0)
writer.finishWriting {
    sema.signal()
}
sema.wait()

// If audio file exists, mux video + audio into final MP4; otherwise move tempVideoPath
if let aPath = audioPath, fm.fileExists(atPath: aPath) {
    let composition = AVMutableComposition()
    let vAsset = AVURLAsset(url: videoURL)
    let aAsset = AVURLAsset(url: URL(fileURLWithPath: aPath))

    if let vTrack = vAsset.tracks(withMediaType: .video).first,
       let compVTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid) {
        try? compVTrack.insertTimeRange(CMTimeRange(start: .zero, duration: vAsset.duration), of: vTrack, at: .zero)
    }

    if let aTrack = aAsset.tracks(withMediaType: .audio).first,
       let compATrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid) {
        let muxDuration = min(vAsset.duration, aAsset.duration)
        try? compATrack.insertTimeRange(CMTimeRange(start: .zero, duration: muxDuration), of: aTrack, at: .zero)
    }

    let finalURL = URL(fileURLWithPath: outputPath)
    if let exporter = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality) {
        exporter.outputURL = finalURL
        exporter.outputFileType = .mp4
        let expSema = DispatchSemaphore(value: 0)
        exporter.exportAsynchronously {
            expSema.signal()
        }
        expSema.wait()
    }
    try? fm.removeItem(atPath: tempVideoPath)
} else {
    try fm.moveItem(atPath: tempVideoPath, toPath: outputPath)
}
"""


def synthesize_voiceover_macos(scenes: List[SceneSpec], work_dir: Path) -> Optional[Path]:
    """
    Uses macOS `/usr/bin/say` and `/usr/bin/avconvert` to synthesize a continuous
    voiceover track (`.m4a`) across all scenes. Returns None if unavailable.
    """
    if not (shutil.which("say") and shutil.which("avconvert")):
        return None

    full_script_parts = []
    for scene in scenes:
        full_script_parts.append(scene.voiceover)
        full_script_parts.append("[[slnc 700]]")

    script_text = " ".join(full_script_parts)
    aiff_path = work_dir / "voiceover.aiff"
    m4a_path = work_dir / "voiceover.m4a"

    try:
        subprocess.run(
            ["say", "-r", "155", "-o", str(aiff_path), script_text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "avconvert",
                "--source",
                str(aiff_path),
                "--output",
                str(m4a_path),
                "--preset",
                "PresetAppleM4A",
                "--replace",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return m4a_path if m4a_path.exists() else None
    except Exception:
        return None


def generate_video(
    project_root: Path,
    output_mp4: Path,
    fps: int = 6,
    include_audio: bool = True,
) -> None:
    """
    Generates the complete 2-minute (120s) INVENTIQ demo video, animated GIF preview,
    and individual high-res storyboard PNG keyframes.
    """
    output_dir = output_mp4.parent
    frames_export_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_export_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Preparing Waxi's 1920x1080 brand canvas & loading {len(SCENES)} scenes...")
    base_bg = build_base_background(VIDEO_WIDTH, VIDEO_HEIGHT)

    # Load and clean screenshots
    loaded_shots: List[Image.Image] = []
    for scene in SCENES:
        img_path = project_root / (scene.image_rel_path or "")
        if img_path.exists():
            raw_img = Image.open(img_path).convert("RGB")
            loaded_shots.append(clean_screenshot_crop(raw_img))
        else:
            fallback = Image.new("RGB", (1280, 720), COLOR_MAROON)
            loaded_shots.append(fallback)

    total_duration = sum(s.duration_sec for s in SCENES)
    total_scenes = len(SCENES)

    with tempfile.TemporaryDirectory(prefix="inventiq_video_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        manifest_entries: List[Tuple[Path, int]] = []
        gif_preview_frames: List[Image.Image] = []
        elapsed_sec = 0.0
        frame_counter = 0

        print(f"[2/4] Rendering scenes & crossfade transitions (Total runtime: {int(total_duration)}s)...")
        for idx, scene in enumerate(SCENES):
            shot = loaded_shots[idx]
            # Render 6 keyframes per scene for smooth Ken Burns + subtitle progression
            steps_per_scene = 6
            step_duration = scene.duration_sec / steps_per_scene
            repeat_frames = max(1, round(step_duration * fps))

            for step in range(steps_per_scene):
                scene_prog = step / max(1, steps_per_scene - 1)
                glob_prog = (elapsed_sec + step * step_duration) / total_duration
                rendered = render_scene_frame(
                    base_bg=base_bg,
                    scene=scene,
                    screenshot_img=shot,
                    scene_progress=scene_prog,
                    global_progress=glob_prog,
                    total_scenes=total_scenes,
                )

                # Save canonical storyboard keyframe PNG on midpoint of each scene
                if step == steps_per_scene // 2:
                    keyframe_path = frames_export_dir / f"scene_0{scene.scene_number}.png"
                    rendered.save(keyframe_path, format="PNG")
                    gif_preview_frames.append(
                        rendered.resize((960, 540), Image.Resampling.LANCZOS)
                    )

                step_path = tmp_dir / f"frame_{frame_counter:04d}.jpg"
                rendered.save(step_path, format="JPEG", quality=92)
                manifest_entries.append((step_path, repeat_frames))
                frame_counter += 1

            # Add a 2-step crossfade transition to the next scene
            if idx + 1 < total_scenes:
                next_scene = SCENES[idx + 1]
                next_shot = loaded_shots[idx + 1]
                next_start_frame = render_scene_frame(
                    base_bg=base_bg,
                    scene=next_scene,
                    screenshot_img=next_shot,
                    scene_progress=0.0,
                    global_progress=(elapsed_sec + scene.duration_sec) / total_duration,
                    total_scenes=total_scenes,
                )
                for alpha in (0.35, 0.70):
                    blended = Image.blend(rendered, next_start_frame, alpha)
                    fade_path = tmp_dir / f"frame_{frame_counter:04d}.jpg"
                    blended.save(fade_path, format="JPEG", quality=90)
                    manifest_entries.append((fade_path, 1))
                    frame_counter += 1

            elapsed_sec += scene.duration_sec

        # Export Animated GIF Preview
        gif_path = output_dir / "inventiq_demo_preview.gif"
        if gif_preview_frames:
            gif_preview_frames[0].save(
                gif_path,
                save_all=True,
                append_images=gif_preview_frames[1:],
                duration=2200,
                loop=0,
                optimize=True,
            )
            print(f"      -> Saved animated preview GIF: {gif_path}")

        # Synthesize Voiceover Audio if enabled
        audio_path: Optional[Path] = None
        if include_audio:
            print("[3/4] Synthesizing voiceover narration track...")
            audio_path = synthesize_voiceover_macos(SCENES, tmp_dir)
            if audio_path:
                print(f"      -> Voiceover synthesized ({audio_path.name})")
            else:
                print("      -> Audio TTS unavailable in current environment; proceeding with video track.")
        else:
            print("[3/4] Skipping voiceover synthesis (--no-audio).")

        # Write frame manifest
        manifest_path = tmp_dir / "manifest.txt"
        manifest_path.write_text(
            "\n".join(f"{p}|{count}" for p, count in manifest_entries) + "\n",
            encoding="utf-8",
        )

        # Encode H.264 MP4
        print(f"[4/4] Encoding 1920x1080 H.264 MP4 video -> {output_mp4} ...")
        if shutil.which("swift"):
            swift_script = tmp_dir / "encode_mp4.swift"
            swift_script.write_text(SWIFT_MP4_ENCODER, encoding="utf-8")
            cmd = [
                "swift",
                str(swift_script),
                str(manifest_path),
                str(output_mp4),
                str(fps),
            ]
            if audio_path:
                cmd.append(str(audio_path))
            subprocess.run(cmd, check=True)
        elif shutil.which("ffmpeg"):
            # Fallback to standard ffmpeg concat demuxer
            ff_concat = tmp_dir / "ffconcat.txt"
            lines = ["ffconcat version 1.0"]
            for p, count in manifest_entries:
                lines.append(f"file '{p}'")
                lines.append(f"duration {count / fps:.4f}")
            ff_concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(ff_concat),
                    "-vf",
                    "fps=24,format=yuv420p",
                    "-c:v",
                    "libx264",
                    str(output_mp4),
                ],
                check=True,
            )
        else:
            print("WARNING: Neither `swift` nor `ffmpeg` found for MP4 muxing; GIF and PNG keyframes were exported.")

    print("\n======================================================================")
    print("INVENTIQ DEMO VIDEO GENERATION COMPLETE")
    print("======================================================================")
    if output_mp4.exists():
        size_mb = output_mp4.stat().st_size / (1024 * 1024)
        print(f"  MP4 Video        : {output_mp4} ({size_mb:.2f} MB)")
    print(f"  Animated GIF     : {output_dir / 'inventiq_demo_preview.gif'}")
    print(f"  Storyboard PNGs  : {frames_export_dir}/scene_01.png .. scene_07.png")
    print("======================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the automated INVENTIQ 1080p MP4 demo video from screen captures."
    )
    parser.add_argument(
        "--output",
        default="media/demo_video/inventiq_demo_video.mp4",
        help="Output MP4 file path (default: media/demo_video/inventiq_demo_video.mp4)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=6,
        help="Frames per second for video encoding (default: 6)",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip macOS TTS voiceover synthesis",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    output_mp4 = (project_root / args.output).resolve()
    generate_video(
        project_root=project_root,
        output_mp4=output_mp4,
        fps=args.fps,
        include_audio=not args.no_audio,
    )


if __name__ == "__main__":
    main()
