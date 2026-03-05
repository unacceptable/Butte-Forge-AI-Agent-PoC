'''
Tools package - loads definitions from tools.json, maps names to executors.
'''

import json
from pathlib import Path
from tools.rgb_mixer import set_rgb_color

ALL_TOOL_DEFINITIONS: list[dict] = json.loads(
    (Path(__file__).parent / "tools.json").read_text()
)

ALL_TOOLS: dict = {
    "set_rgb_color": set_rgb_color,
}
