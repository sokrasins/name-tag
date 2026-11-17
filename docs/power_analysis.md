# Power analysis

This is an estimate of the back board's (`nametag_back`, Rev 4) current draw
and battery life. It is worked out from the current schematic, the BOM, the
TPS61322 datasheet (`docs/datasheets/tps61322.pdf`, SLVSDY5E) and the
manufacturer listings for the LEDs and switch, plus measured LED forward
voltages (white 2.68 V, green 2.45 V). Battery current and runtime are still
calculated, not measured, so confirm them on hardware.

## Circuit summary

```
AA cell ─ SW2 ─ L1 4.7 µH ─ U1 TPS613221A (boost) ─ +3V3 ─ 22× (white LED + 270 Ω) ─ GND
                │                                     │    5× (green LED + 330 Ω)
               C1 2.2 µF                             C2 22 µF
```

- **Source:** one AA cell (BT1, Keystone 2460 holder). SW2 (C&K PCM12SMTR) is
  an SPDT switch. Its common pin feeds L1. When the switch is on, the common
  pin connects to the cell. When it is off, the cell is left open and the
  converter input is tied to GND.
- **Regulator:** U1 is a TI TPS613221A synchronous boost converter with a
  fixed 3.3 V output. The datasheet gives 3.2–3.4 V output, a 0.9 V minimum
  input to start, 6.5 µA quiescent current, and a 0.75 A minimum (1.2 A
  typical) switch current limit.
- **Load:** 27 LED/resistor branches in parallel, each wired as +3V3 → LED →
  resistor → GND:
  - 22× XINGLIGHT XL-3216UWC white (C965828), D1–D20, D26 and D27, each with
    a 270 Ω resistor (R1–R20, R26, R27)
  - 5× XINGLIGHT XL-3216UGC emerald green (C965825), D21–D25, each with a
    330 Ω resistor (R21–R25)

  Both LED types are InGaN, rated 3.4 V at 20 mA.
- **No brightness control:** the LEDs run at a fixed current whenever SW2 is
  on.

## What changed from Rev 3

Rev 3 ran the LEDs from a 5 V rail (TPS613222A) through 1 kΩ resistors, so
about half of the rail power was burned in the resistors. Rev 4 drops the
rail to 3.3 V and shrinks the resistors to match. The LEDs get about the same
current as before (~2.3–2.6 mA), but the rail power falls from 319 mW to
209 mW, so the battery current drops by about a third and runtime goes up by
about half.

## Assumptions

| Parameter | Value used | Source / notes |
| --- | --- | --- |
| White LED V<sub>f</sub> | 2.68 V | Measured |
| Green LED V<sub>f</sub> | 2.45 V | Measured |
| Output voltage | 3.3 V | Datasheet typical |
| Boost efficiency at ~63 mA out | 88 % at 1.5 V, 86 % at 1.3 V, 84.5 % at 1.2 V, 80 % at 1.0 V, 77 % at 0.9 V | Read from datasheet Fig. 6-3 (TPS613221A), interpolating between the 0.9 V and 1.5 V curves. That curve was measured with a 2.2 µH inductor. This board uses 4.7 µH, which has lower ripple, so efficiency is likely similar or slightly better |
| Alkaline AA usable energy | 2.0–2.5 Wh | Premium alkaline at ~240–270 mW constant power, down to ~0.9–1.0 V. Still less than the ~3 Wh low-drain rating, but better than at Rev 3's higher draw |
| Eneloop AA usable energy | 2.2–2.4 Wh | Panasonic eneloop standard (BK-3MCC) is 1900 mAh min / 2000 mAh typ × ~1.2 V. At this ~0.1 C rate, nearly all of the rated capacity is available |

## LED load (3.3 V rail)

Per-branch current is `(3.3 V − Vf) / R`.

| Group | V<sub>f</sub> | R | Per LED | Count | Current | 3.3 V rail power | Lost in resistors | In LEDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| White | 2.68 V | 270 Ω | 2.30 mA | 22 | 50.5 mA | 167 mW | 31 mW | 135 mW |
| Green | 2.45 V | 330 Ω | 2.58 mA | 5 | 12.9 mA | 42 mW | 11 mW | 32 mW |
| **Total** | | | | **27** | **63.4 mA** | **209 mW** | **42 mW** | **167 mW** |

U1's quiescent current (6.5 µA × 3.3 V ≈ 21 µW) is negligible.

Only ~20 % of the output power is now lost in the resistors (it was ~47 % at
Rev 3). The cost is that the LED current is more sensitive to voltage,
because the resistors only drop 0.6–0.85 V:

- **Rail tolerance:** at the 3.2 V and 3.4 V datasheet limits, the total is
  about 53.7 mA or 73.1 mA (−15 % / +15 %), so brightness varies more from
  board to board than it did at 5 V (±6 %).
- **LED V<sub>f</sub> spread:** a 0.1 V shift in a white LED's V<sub>f</sub>
  changes its current by ~0.37 mA (~16 %). Some LED-to-LED brightness
  difference may be visible. The green LEDs' 330 Ω resistors hold them at
  ~12 % more current than the whites.

At 2.3–2.6 mA each, the LEDs run at about 12–13 % of their 20 mA rating.

## Battery current

The boost converter holds a constant 3.3 V, so the board draws constant
*power* from the cell. As the cell voltage falls, the battery current rises:

`I_bat = P_out / (η × V_bat)`, with P<sub>out</sub> = 209 mW

| V<sub>bat</sub> | 1.5 V (fresh alkaline) | 1.3 V (fresh eneloop) | 1.2 V (eneloop plateau / mid alkaline) | 1.0 V | 0.9 V |
| --- | --- | --- | --- | --- | --- |
| η | 88 % | 86 % | 84.5 % | 80 % | 77 % |
| Battery power | 238 mW | 243 mW | 248 mW | 262 mW | 272 mW |
| **Battery current** | **159 mA** | **187 mA** | **206 mA** | **262 mA** | **302 mA** |
| U1 + L1 loss | 29 mW | 34 mW | 38 mW | 52 mW | 63 mW |

### Converter headroom

Datasheet Eq. 1 gives the worst-case output capability:
`I_OUT(max) = V_IN × (I_LIM − I_LH/2) × η / V_OUT`. With V<sub>IN</sub> =
0.9 V, I<sub>LIM</sub> = 0.75 A (minimum), I<sub>LH</sub> = 200 mA and
η = 70 %, the result is **≈ 124 mA**. That is about twice the 63 mA load.
Fig. 6-3 shows the same thing: the 0.9 V curve runs out at roughly 120 mA.
The converter can therefore hold the load down to the end of a cell's
useful life. The lower output voltage makes up for the TPS613221A's lower
current limit, so the margin is about the same as Rev 3's.

Peak inductor current at 0.9 V is about 0.30 A + 0.1 A of ripple, or
≈ 0.40 A. That is under the 0.75 A minimum current limit, and L1 (Murata
DFE252012P-4R7M, I<sub>sat</sub> 2 A, I<sub>rated</sub> 1.4 A) has plenty of
margin.

## Estimated runtime (switch on, continuous)

| Battery | Behavior during discharge | Estimated runtime |
| --- | --- | --- |
| **Alkaline AA** (e.g. Energizer / Duracell) | Starts at ~160 mA. Current climbs to ~300 mA as the cell sags. Near end of life the cell's internal resistance grows, so the input collapses at a loaded ~0.9–1.0 V and some of the remaining energy is stranded | **~7.75–10 h** |
| **Panasonic eneloop AA** | The cell holds a flat ~1.2–1.25 V for most of the discharge, so current stays near ~205 mA. Low internal resistance (~20–30 mΩ) means little sag | **~8.75–9.75 h** |

Because the converter regulates, the LEDs stay at full brightness for the
whole run. They don't fade gradually. Near the end the badge drops out,
and an alkaline cell may let it blink or restart a few times as it recovers.
For predictable behavior, swap the cell when that starts.

At this ~160–300 mA drain, a good alkaline and an eneloop deliver similar
runtimes. The alkaline has a higher ceiling, while the eneloop's runtime
varies less from cell to cell. Cheap zinc-carbon ("heavy duty") cells are
poorly suited to this load. Expect roughly a third of the alkaline runtime or
less.

**Eneloop note:** once running, the converter keeps going below 0.9 V. If the
badge is left on, it will drain the NiMH cell deeply. That doesn't harm a
single cell much, but switch the badge off once it quits, and recharge
promptly.

## Off state

With SW2 off, the cell is open-circuit. The only drain is the cell's own
self-discharge: a few % per year for alkaline, and the eneloop is rated
to keep ~70 % of its charge after 10 years.

## Component stress and thermal check

| Part | Worst case | Rating | Comment |
| --- | --- | --- | --- |
| SW2, PCM12SMTR | 159–302 mA carried | 0.3 A at 6 V DC, 70 mΩ max | Within rating for nearly the whole discharge. It only reaches 0.3 A at a ~0.9 V end-of-life cell (and beyond if a cell is run below that). Contact loss is ≤ ~6 mW. Rev 3 ran it well past its rating (up to ~454 mA), so this is a big improvement |
| U1 TPS613221A | ~63 mW loss at 0.9 V (part in L1) | R<sub>θJA</sub> 190 °C/W | < +12 °C rise. Fine |
| L1 | ~0.40 A peak | I<sub>sat</sub> 2 A | Fine |
| C2 22 µF / 25 V X5R 0805 | 3.3 V bias | ≥ 10 µF effective required for 4.7 µH | At 3.3 V a 25 V-rated 0805 part keeps more of its capacitance than at 5 V, comfortably above the 10 µF minimum. TI's Table 8-3 pairs 4.7 µH with 22 µF. Check output ripple on the scope |
| Each 270 Ω 0805 resistor (white) | 1.4 mW | 125 mW | Fine |
| Each 330 Ω 0805 resistor (green) | 2.2 mW | 125 mW | Fine |
| Each LED | ~6.2 mW; 2.30 mA (white), 2.58 mA (green) | 20 mA | Fine |

Nothing on the board needs thermal attention, and every part is now within
its rating for normal use.

## How to verify on hardware

1. Measure the +3V3 rail. It should be 3.2–3.4 V.
2. Measure the voltage across a few resistors, both white and green. With a
   3.3 V rail, expect ~0.62 V across the 270 Ω white-LED resistors (2.3 mA)
   and ~0.85 V across the 330 Ω green-LED resistors (2.6 mA). Current is
   `V / R`. Because these drops are small, a rail a little off 3.3 V moves
   them noticeably.
3. Put an ammeter in series with the cell (for example, a bench supply in
   place of the cell). Measure battery current at 1.5 V, 1.2 V and 1.0 V and
   compare it with the battery-current table. Use a short, low-resistance
   meter range: a 160–300 mA draw through a meter's shunt will pull the input
   down noticeably.
4. Run the badge from a fresh alkaline cell and from a fully charged eneloop
   until it drops out, to get real runtimes.
