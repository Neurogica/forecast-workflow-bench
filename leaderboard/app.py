"""Neurogica-branded read-only leaderboard. No model execution or paid calls."""

import os
import sys
from pathlib import Path

os.environ.setdefault("GRADIO_SSR_MODE", "false")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "false")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402
from view import (  # noqa: E402
    FILTERS,
    SORT_OPTIONS,
    header,
    hero,
    leaderboard,
    protocol,
    references,
    stylesheet,
)

with gr.Blocks(title="FWBench | Neurogica", analytics_enabled=False) as app:
    gr.HTML(header())
    gr.HTML(hero())
    with gr.Row(elem_id="model-controls"):
        group = gr.Radio(
            list(FILTERS), value="All models", label="Model group", elem_id="group-filter", scale=3
        )
        order = gr.Dropdown(
            SORT_OPTIONS,
            value=SORT_OPTIONS[0],
            label="Sort results",
            elem_id="sort-order",
            scale=1,
        )
    table = gr.HTML(leaderboard(), elem_id="model-table")
    group.change(leaderboard, [group, order], table, api_name=False, queue=False)
    order.change(leaderboard, [group, order], table, api_name=False, queue=False)
    gr.HTML(references())
    gr.HTML(protocol())

if __name__ == "__main__":
    app.launch(css=stylesheet(), ssr_mode=False, footer_links=[])
