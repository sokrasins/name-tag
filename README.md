# MAKE Roanoke Name tag

A battery-powered, LED-lit "My name is" name tag for
MAKE Roanoke, designed in KiCad 9.

It is made of two stacked PCBs:

- **Back board:** holds all the electronics, including the battery, power
  switch, boost converter and 27 LEDs. This board provides 
  illumination to highlight the features on the front board.
- **Front board:** a plain faceplate with no parts. It has the "My name is:"
  silkscreen and a wrench graphic, and it covers the LED area of the back 
  board. The board lacks soldermask so that the wrench and the area with the 
  individual's name light up when the name tag is on.

The boards line up on four M3 mounting holes and are held together with
standoffs. A slot at the top of the back board is for a clip.

This project has been designed explicitly to be built via reflow as part of a 
class.

Viewable links are here:
- [Schematic](https://github.com/sokrasins/nametag/blob/main/docs/nametag_back_schematic_rev3.pdf)
- [Back PCB](https://pcbview.io/?github=https%3A%2F%2Fgithub.com%2Fsokrasins%2Fnametag%2Fblob%2FHEAD%2Fpcbs%2Fnametag_back%2Fnametag_back.kicad_pcb)
- [Front PCB](https://pcbview.io/?github=https%3A%2F%2Fgithub.com%2Fsokrasins%2Fnametag%2Fblob%2FHEAD%2Fpcbs%2Fnametag_front%2Fnametag_front.kicad_pcb)
- [Assembly](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sokrasins/nametag/refs/heads/main/docs/assembly.html)

## Renders

![Back PCB](docs/renders/nametag_back_render.png)

![Front PCB](docs/renders/nametag_front_render.png)

## How it works

- **Power:** a single AA cell (Keystone 2460 holder) switched by an SPDT
  slide switch.
- **Boost converter:** a TI TPS613222A steps the cell up to a +5V rail.
- **LEDs:** 27× 1206 SMD LEDs (22 white, 5 green). Each one has a 1 kΩ
  current-limiting resistor to GND.
- **Brightness:** fixed. This revision (Rev 3) has no brightness control; the
  LEDs run at about 2.25 mA each whenever the switch is on.

See [docs/power_analysis.md](docs/power_analysis.md) for current draw and
battery life estimates.

## Boards

| | Back | Front |
| --- | --- | --- |
| Size | 100 × 78 mm | 100 × 53 mm |
| Layers / thickness | 2 / 1.6 mm | 2 / 1.6 mm |
| Components | All electronics | None (4× M3 holes) |

## Repository layout

| Path | Contents |
| --- | --- |
| `pcbs/nametag_back/` | Back board KiCad project (schematic and layout) |
| `pcbs/nametag_back/gerbs/` | Back board Gerbers and drill files |
| `pcbs/nametag_front/` | Front board KiCad project (layout only, no schematic) |
| `pcbs/nametag_front/gerbs/` | Front board Gerbers and drill files |
| `docs/assembly.html` | Interactive BOM for assembling the back board |
| `docs/bom.csv` | Bill of materials for the back board, with LCSC / Digi-Key part numbers |

## Regenerating the renders, schematic PDF and interactive BOM

With KiCad 9 or newer installed, run:

```sh
scripts/render_pcbs.sh          # top side (the images above)
scripts/render_pcbs.sh both     # also writes docs/renders/*_render_bottom.png
```

It calls `kicad-cli pcb render` for each board and `kicad-cli sch export pdf`
to write `docs/nametag_back_schematic_rev<N>.pdf`, where `<N>` is the
revision from the schematic's title block. Set `KICAD_CLI` if
`kicad-cli` isn't on your `PATH`. `QUALITY`, `WIDTH`, `HEIGHT` and `BACKGROUND`
change the output.

If the [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom)
plugin is installed through KiCad's Plugin and Content Manager, it also writes
`docs/assembly.html`. Set `IBOM` to point at `generate_interactive_bom.py` if
the plugin lives elsewhere, and `IBOM_PYTHON` if the python that can import
KiCad's `pcbnew` module isn't found automatically.

## Open items

- SW2 (PCM12SMTR) is rated 0.3 A, but the battery current reaches ~230–430 mA
  over a discharge. See the power analysis; a higher-rated switch may be worth
  considering.
