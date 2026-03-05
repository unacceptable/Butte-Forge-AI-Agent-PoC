'''
RGB Color Mixer - controls an RGB LED diode.
'''

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path("/tmp/rgb_state.json")


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def set_rgb_color(red: int, green: int, blue: int) -> dict:
    '''
    Set the RGB LED to the given color. Persists state to disk.

    On a real Pi, use MTECH_GPIO to drive PWM pins.
    '''
    state = {
        "red": _clamp(red),
        "green": _clamp(green),
        "blue": _clamp(blue),
        "hex": f'#{_clamp(red):02x}{_clamp(green):02x}{_clamp(blue):02x}'
    }

    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    logger.info("RGB LED → %s", state["hex"])

    # TODO: Control actual GPIO pins # pylint: disable=fixme

    return {
        "status": "ok",
        "color": state,
        "message": f"LED set to {state['hex']}"
    }
