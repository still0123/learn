"""Focus-context image reconstruction under a fixed visual-view budget."""

from __future__ import annotations

from PIL import Image


def compose_focus_context(
    context: Image.Image,
    focus: Image.Image,
    context_fraction: float = 0.5,
    divider_px: int = 4,
    background: tuple[int, int, int] = (18, 18, 18),
) -> Image.Image:
    """Place the full frame and an ROI zoom in one image without cropping context."""
    if context.width < 2 or context.height < 1:
        raise ValueError("context image is too small")
    if focus.width < 1 or focus.height < 1:
        raise ValueError("focus image is empty")
    if not 0.35 <= float(context_fraction) <= 0.75:
        raise ValueError("context_fraction must be in [0.35, 0.75]")

    width, height = context.size
    divider = min(max(int(divider_px), 0), max(0, height - 2))
    usable = height - divider
    context_height = min(usable - 1, max(1, round(usable * float(context_fraction))))
    focus_height = usable - context_height

    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(
        context.convert("RGB").resize((width, context_height), Image.Resampling.LANCZOS),
        (0, 0),
    )
    canvas.paste(
        focus.convert("RGB").resize((width, focus_height), Image.Resampling.LANCZOS),
        (0, context_height + divider),
    )
    return canvas
