import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class ScientificAnimationProvider(MediaProvider):
    media_type = "scientific_animation"

    def __init__(self):
        self.ffmpeg = subprocess.check_output(["which", "ffmpeg"], text=True).strip()

    async def available(self) -> bool:
        return True

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        output_dir.mkdir(parents=True, exist_ok=True)
        context = plan.narrative_context[:200]

        concept = self._detect_concept(context)
        if not concept:
            return []

        video_path = await self._render_animation(concept, plan.duration, output_dir)
        if video_path:
            return [MediaAsset(
                media_type="scientific_animation",
                file_path=video_path,
                duration=plan.duration,
                source="atlas_animation",
                metadata={"concept": concept},
            )]
        return []

    @staticmethod
    def _detect_concept(text: str) -> str | None:
        concepts = [
            ("root", ["जड़", "root", "roots", "underground network", "जड़ों"]),
            ("fungus", ["फंगस", "fungus", "fungi", "mycorrhizal", "mushroom"]),
            ("network", ["नेटवर्क", "network", "web", "जाल", "connected"]),
            ("cell", ["कोशिका", "cell", "cellular", "सूक्ष्म"]),
            ("volcano", ["ज्वालामुखी", "volcano", "volcanic", "lava"]),
            ("gravity", ["गुरुत्वाकर्षण", "gravity", "gravitational"]),
            ("dna", ["डीएनए", "DNA", "genetic", "gene"]),
            ("solar", ["सौर", "solar system", "ग्रह", "planet", "star"]),
        ]
        lower = text.lower()
        for concept, keywords in concepts:
            if any(k in lower for k in keywords):
                return concept
        return None

    async def _render_animation(self, concept: str, duration: float, output_dir: Path) -> str | None:
        frames_dir = Path(tempfile.mkdtemp())
        try:
            n_frames = max(4, int(duration * 6))
            for i in range(n_frames):
                progress = i / max(n_frames - 1, 1)
                path = str(frames_dir / f"frame_{i:04d}.png")
                self._draw_frame(concept, progress, path)

            output_path = str(output_dir / f"anim_{uuid.uuid4().hex[:12]}.mp4")
            cmd = [
                self.ffmpeg, "-y", "-framerate", "6",
                "-i", str(frames_dir / "frame_%04d.png"),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-pix_fmt", "yuv420p", "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                "-t", str(duration),
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
                return output_path
        finally:
            import shutil
            shutil.rmtree(frames_dir, ignore_errors=True)
        return None

    def _draw_frame(self, concept: str, progress: float, path: str):
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams['font.sans-serif'] = ['Kohinoor Devanagari', 'Devanagari Sangam MN', 'Devanagari MT'] + matplotlib.rcParams.get('font.sans-serif', [])
        matplotlib.rcParams['font.family'] = 'sans-serif'
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=80)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        bg = "#0a0f1a"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)

        if concept == "root":
            self._draw_root_network(ax, progress)
        elif concept == "network":
            self._draw_network(ax, progress)
        elif concept == "fungus":
            self._draw_fungus(ax, progress)
        elif concept == "cell":
            self._draw_cell(ax, progress)
        elif concept == "solar":
            self._draw_solar(ax, progress)
        else:
            ax.text(50, 50, f"⚡ {concept}", fontsize=30,
                    color="#e8c84a", ha="center", va="center")

        fig.savefig(path, bbox_inches="tight", pad_inches=0, facecolor=bg)
        plt.close(fig)

    @staticmethod
    def _draw_root_network(ax, progress: float):
        import numpy as np
        depth = 20 + progress * 50
        for i in range(12):
            x = 30 + np.random.uniform(-5, 5) + i * 4
            y = 70 - (i / 12) * depth
            size = max(2, 8 - i * 0.5)
            alpha = max(0.3, 1 - i * 0.07)
            ax.plot([x, x + np.random.uniform(-8, 8)],
                     [y, y - np.random.uniform(3, 8)],
                     color="#6b8e23", linewidth=size * 0.3, alpha=alpha)
            ax.scatter(x, y, s=size * 4, color="#8b5e3c", alpha=alpha, zorder=2)
        ax.text(50, 15, "🌱 Root Network", fontsize=16, color="#e8c84a",
                ha="center", va="center", alpha=min(1, progress * 2))

    @staticmethod
    def _draw_network(ax, progress: float):
        import numpy as np
        nodes = 8 + int(progress * 6)
        points = np.column_stack([np.random.uniform(10, 90, nodes),
                                   np.random.uniform(20, 80, nodes)])
        for i in range(nodes):
            for j in range(i + 1, nodes):
                dist = np.linalg.norm(points[i] - points[j])
                if dist < 25:
                    alpha = max(0.2, 1 - dist / 30)
                    ax.plot([points[i, 0], points[j, 0]],
                             [points[i, 1], points[j, 1]],
                             color="#4a90d9", linewidth=0.5, alpha=alpha)
        for (x, y) in points:
            ax.scatter(x, y, s=20, c="#e8c84a", alpha=0.8, zorder=3)
        if progress > 0.5:
            ax.text(50, 10, "🌐 Network", fontsize=16, color="#e8c84a", ha="center")

    @staticmethod
    def _draw_fungus(ax, progress: float):
        import numpy as np
        for i in range(15):
            x = 20 + np.random.uniform(0, 60)
            y = 30 + progress * 40 + np.random.uniform(-5, 5)
            if y > 90:
                continue
            cap_color = np.array([0.8, 0.6, 0.3]) + np.random.uniform(-0.1, 0.1, 3)
            ax.plot([x, x + np.random.uniform(-2, 2)],
                     [y, y - np.random.uniform(3, 6)],
                     color="#d4c5a9", linewidth=1.5)
            circle = plt.Circle((x, y), 1.5 + np.random.uniform(0, 1),
                                 color=cap_color, alpha=0.7, zorder=2)
            ax.add_patch(circle)
        if progress > 0.3:
            ax.text(50, 12, "🍄 Fungal Network", fontsize=14,
                    color="#e8c84a", ha="center")

    @staticmethod
    def _draw_cell(ax, progress: float):
        r = 15 + progress * 5
        circle = plt.Circle((50, 55), r, color="#2a4a6a", alpha=0.5,
                             ec="#4a90d9", linewidth=2)
        ax.add_patch(circle)
        nucleus = plt.Circle((50, 55), r * 0.35, color="#6a2a8a",
                              alpha=0.7, ec="#9a5aba", linewidth=1)
        ax.add_patch(nucleus)
        ax.text(50, 15, "🔬 Cellular Structure", fontsize=14,
                color="#e8c84a", ha="center")

    @staticmethod
    def _draw_solar(ax, progress: float):
        ax.add_patch(plt.Circle((50, 50), 8, color="#f5c542", alpha=0.8))
        planets = [(15, 35), (22, 28), (30, 22), (40, 18), (55, 15), (70, 12)]
        colors = ["#8a8a8a", "#c4a86a", "#4a7ab5", "#c44a4a", "#d4a86a", "#6a8ab5"]
        for j, ((px, py), col) in enumerate(zip(planets, colors)):
            angle = progress * 2 * np.pi + j * 0.8
            x = 50 + (px - 50) * np.cos(angle) - (py - 50) * np.sin(angle)
            y = 50 + (px - 50) * np.sin(angle) + (py - 50) * np.cos(angle)
            ax.plot([50, x], [50, y], color="#666", linewidth=0.3, alpha=0.5)
            ax.add_patch(plt.Circle((x, y), 1.5 + j * 0.3, color=col, alpha=0.7))
        ax.text(50, 8, "🪐 Solar System", fontsize=14, color="#e8c84a", ha="center")
