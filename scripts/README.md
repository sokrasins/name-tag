# Scripts

Run these from the repository root. Both need KiCad 9 or newer.

## render_pcbs.sh: renders, schematic PDF and assembly docs

```sh
scripts/render_pcbs.sh          # top side (the images in the main README)
scripts/render_pcbs.sh both     # also writes docs/renders/*_render_bottom.png
```

It calls `kicad-cli pcb render` for each board and `kicad-cli sch export pdf`
to write `docs/nametag_back_schematic_rev<N>.pdf`, where `<N>` is the
revision from the schematic's title block. Set `KICAD_CLI` if
`kicad-cli` isn't on your `PATH`. `QUALITY`, `WIDTH`, `HEIGHT` and `BACKGROUND`
change the output.

If the [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom)
plugin is installed through KiCad's Plugin and Content Manager, it also writes
`docs/assembly/assembly_ibom.html`. Set `IBOM` to point at
`generate_interactive_bom.py` if the plugin lives elsewhere, and
`PCBNEW_PYTHON` if the python that can import KiCad's `pcbnew` module isn't
found automatically.

It also runs `assembly_doc.py` (below) to write the assembly guide in color
and grayscale.

## assembly_doc.py: printable assembly guide

`docs/assembly/assembly_guide.pdf` is a printable guide with one step per
component (each value/footprint group, e.g. all 27 1k resistors). Each step
fills half a US letter page, so two print per sheet with a dashed line between
them to cut along. Each step shows the back board and its silkscreen with that
component's locations highlighted, pin 1 marked for polarized parts and parts
from earlier steps shaded. Steps run top to bottom, left to right across the
board, with the resistors last (`--last` changes which reference prefixes go at
the end). Mounting holes and the hand-soldered AA holder (BT1) get no step;
`--skip` changes which references are left out.

```sh
scripts/assembly_doc.py                       # back board -> docs/assembly/assembly_guide.pdf
scripts/assembly_doc.py --grayscale           # -> docs/assembly/assembly_guide_grayscale.pdf
scripts/assembly_doc.py path/to/board.kicad_pcb -o out.pdf
```

It needs KiCad's `pcbnew` python module (set `PCBNEW_PYTHON` if it isn't
found) and `rsvg-convert` (`brew install librsvg`).
