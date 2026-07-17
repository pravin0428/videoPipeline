"""Phase 7 — Documentary Rhythm: structure pacing (fast/slow)."""

from services.director.models import DocumentaryPacing, Emotion, StoryBeat


class DocumentaryRhythm:
    def plan(self, beats: list[StoryBeat]) -> DocumentaryPacing:
        pacing = DocumentaryPacing()
        n = len(beats)
        if n == 0:
            return pacing

        hook_type = "question" if beats[0].purpose == "hook" else "statement"
        pacing.hook_type = hook_type

        structure = []
        emotional_arc = []

        for i, beat in enumerate(beats):
            pos = i / max(n - 1, 1)

            if pos < 0.15:
                rhythm = "fast"
                if "?" in beat.sentence:
                    structure.append((beat.sentence[:40], "hook"))
                    pacing.has_mystery = True
            elif pos < 0.35:
                rhythm = "fast"
                structure.append((beat.sentence[:40], "context"))
                pacing.has_mystery = True
            elif pos < 0.65:
                rhythm = "slow"
                structure.append((beat.sentence[:40], "explanation"))
            elif pos < 0.85:
                rhythm = "fast"
                structure.append((beat.sentence[:40], "reveal"))
                pacing.has_reveal = True
            else:
                rhythm = "slow"
                structure.append((beat.sentence[:40], "closing"))

            pacing.rhythm_map[i] = rhythm
            emotional_arc.append(beat.emotion)

        pacing.structure = structure
        pacing.emotional_arc = emotional_arc
        return pacing
