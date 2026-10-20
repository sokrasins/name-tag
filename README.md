# MAKE Roanoke Name tag

A two-tier, battery-powered, LED-lit "My name is:" name tag for
MAKE Roanoke, designed in KiCad 9.

It is made of two stacked PCBs:

- **Back board:** holds all the electronics, including the battery, power
  switch, boost converter, brightness pot and 27 LEDs.
- **Front board:** a plain faceplate with no parts. It has the "My name is:"
  silkscreen and a wrench graphic, and it covers the LED area of the back board.

The boards line up on four M4 mounting holes and are held together with
standoffs. A slot at the top of the back board is for a lanyard or clip.

![Back PCB](docs/nametag_back_render.png)

![Front PCB](docs/nametag_front_render.png)

## How it works

- **Power:** a single AAA cell in a Keystone 2466 holder, switched by an SPDT
  slide switch.
- **Boost converter:** a TI TPS613221A (SOT-23-5) with a 4.7 µH inductor and
  2.2 µF in / 22 µF out capacitors steps the cell up to a +3V3 rail.
- **LEDs:** 27× 1206 SMD LEDs. Each one has a 1 kΩ current-limiting resistor and
  a BSS138 N-channel MOSFET low-side switch.
- **Brightness:** a 10 kΩ Bourns TC33X trimmer potentiometer divides the 3.3 V
  rail and drives the shared `CTRL` gate line of all 27 MOSFETs, so turning it
  dims or brightens every LED together.

## Boards

| | Back | Front |
| --- | --- | --- |
| Size | 100 × 75 mm | 100 × 53 mm |
| Layers / thickness | 2 / 1.6 mm | 2 / 1.6 mm |
| Components | All electronics | None (4× M4 holes) |

## Repository layout

| Path | Contents |
| --- | --- |
| `nametag_back/oven_nametag.kicad_pro` | Back board KiCad project |
| `nametag_back/oven_nametag.kicad_sch` | Top-level schematic: battery, switch, boost converter, brightness pot, mounting holes |
| `nametag_back/leds.kicad_sch` | Hierarchical `LEDs` sheet: 27 LED / resistor / MOSFET channels |
| `nametag_back/oven_nametag.kicad_pcb` | Back board layout |
| `nametag_back/gerbs/` | Back board Gerbers and drill files |
| `nametag_back/bom/ibom.html` | Interactive BOM for assembling the back board |
| `nametag_front/nametag_front.kicad_pro` | Front board KiCad project (PCB only, no schematic) |
| `nametag_front/gerbs/` | Front board Gerbers and drill files |
| `docs/` | 3D renders of both boards |

## Building

1. Open each `.kicad_pro` in [KiCad](https://www.kicad.org/) 9.0 or newer.
2. Send each board's `gerbs/` folder to a PCB fab.
3. Use `nametag_back/bom/ibom.html` in a browser to guide hand assembly of the
   back board.
4. Stack the front board over the back board with M4 standoffs, put in a AAA
   cell, switch it on, and set the brightness with RV1.

## Open items

- The top-level schematic still has a couple of "TODO: Verify" notes.
- Ideas from the original requirements that aren't built yet: running on two
  AAA cells and an optional ESP add-on.
