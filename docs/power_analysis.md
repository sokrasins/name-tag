# Power analysis

This is an estimate of the back board's (`nametag_back`) current draw and
battery life. It is worked out from the current schematic, the BOM, the
TPS61322 datasheet (`docs/datasheets/tps61322.pdf`, SLVSDY5E) and the
manufacturer listings for the LEDs and switch, plus measured LED forward
voltages (white 2.68 V, green 2.45 V). Battery current and runtime are still
calculated, not measured, so confirm them on hardware.

## Circuit summary

```
AA cell ─ SW2 ─ L1 4.7 µH ─ U1 TPS613222A (boost) ─ +5V ─ 27× (LED + 1 kΩ) ─ GND
                │                                     │
               C1 2.2 µF                             C2 22 µF
```

- **Source:** one AA cell (BT1, Keystone 2460 holder). SW2 (C&K PCM12SMTR) is
  an SPDT switch. Its common pin feeds L1. When the switch is on, the common
  pin connects to the cell. When it is off, the cell is left open and the
  converter input is tied to GND.
- **Regulator:** U1 is a TI TPS613222A synchronous boost converter with a
  fixed 5.0 V output. The datasheet gives 4.85–5.15 V output, a 0.9 V minimum
  input to start, operation down to 0.4 V once running, 6.5 µA quiescent
  current, and a 1.10 A minimum (1.8 A typical) switch current limit.
- **Load:** 27 LED/resistor branches in parallel, each wired as +5V → LED →
  1 kΩ → GND:
  - 22× XINGLIGHT XL-3216UWC white (C965828), D1–D20, D26 and D27
  - 5× XINGLIGHT XL-3216UGC emerald green (C965825), D21–D25

  Both LED types are InGaN, rated 3.4 V at 20 mA.
- **No brightness control:** the pot and MOSFET from Rev 2 are gone (the
  `LIGHT_CTRL` labels now go straight to GND). The LEDs run at a fixed current
  whenever SW2 is on.

## Assumptions

| Parameter | Value used | Source / notes |
| --- | --- | --- |
| White LED V<sub>f</sub> | 2.68 V | Measured |
| Green LED V<sub>f</sub> | 2.45 V | Measured |
| Output voltage | 5.0 V | Datasheet typical |
| Boost efficiency at ~64 mA out | 87 % at 1.5 V, 83.5 % at 1.2 V, 80 % at 1.0 V, 78 % at 0.9 V | Read from datasheet Fig. 6-5 (TPS613222A). That curve was measured with a 2.2 µH inductor. This board uses 4.7 µH, which has lower ripple, so efficiency is likely similar or slightly better |
| Alkaline AA usable energy | 1.8–2.3 Wh | Premium alkaline at ~350–390 mW constant power, down to ~0.9–1.0 V. The cell delivers noticeably less than its ~3 Wh low-drain rating at this load |
| Eneloop AA usable energy | 2.2–2.4 Wh | Panasonic eneloop standard (BK-3MCC) is 1900 mAh min / 2000 mAh typ × ~1.2 V. At this ~0.15 C rate, nearly all of the rated capacity is available |

## LED load (5 V rail)

Per-branch current is `(5.0 V − Vf) / 1 kΩ`.

| Group | V<sub>f</sub> | Per LED | Count | Current | 5 V rail power | Lost in resistors | In LEDs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| White | 2.68 V | 2.32 mA | 22 | 51.0 mA | 255 mW | 118 mW | 137 mW |
| Green | 2.45 V | 2.55 mA | 5 | 12.8 mA | 64 mW | 33 mW | 31 mW |
| **Total** | | | **27** | **63.8 mA** | **319 mW** | **151 mW** | **168 mW** |

This is ~5 % more than the earlier estimate (60.8 mA / 304 mW at an assumed
2.75 V for both colors). If the rail sits at the 4.85 V or 5.15 V datasheet
limits, the total shifts to about 59.7 mA or 67.9 mA.

U1's quiescent current (6.5 µA × 5 V ≈ 33 µW) is negligible.

The 1 kΩ resistors drop about half of the rail voltage, so ~47 % of the
output power is turned into heat in the resistors. In exchange, the LED
current is fairly insensitive to V<sub>f</sub>: the green LEDs' 0.23 V lower
V<sub>f</sub> gives them only ~10 % more current than the whites. At
2.3–2.6 mA each, the LEDs run at about 12–13 % of their 20 mA rating.

## Battery current

The boost converter holds a constant 5 V, so the board draws constant
*power* from the cell. As the cell voltage falls, the battery current rises:

`I_bat = P_out / (η × V_bat)`, with P<sub>out</sub> = 319 mW

| V<sub>bat</sub> | 1.5 V (fresh alkaline) | 1.3 V (fresh eneloop) | 1.2 V (eneloop plateau / mid alkaline) | 1.0 V | 0.9 V |
| --- | --- | --- | --- | --- | --- |
| η | 87 % | 85 % | 83.5 % | 80 % | 78 % |
| Battery power | 367 mW | 375 mW | 382 mW | 399 mW | 409 mW |
| **Battery current** | **244 mA** | **289 mA** | **318 mA** | **399 mA** | **454 mA** |
| U1 + L1 loss | 48 mW | 56 mW | 63 mW | 80 mW | 90 mW |

The efficiency figures are the same as before. Going from 61 mA to 64 mA of
load moves the Fig. 6-5 curves by well under a percentage point.

### Converter headroom

Datasheet Eq. 1 gives the worst-case output capability:
`I_OUT(max) = V_IN × (I_LIM − I_LH/2) × η / V_OUT`. With V<sub>IN</sub> =
0.9 V, I<sub>LIM</sub> = 1.10 A (minimum), I<sub>LH</sub> = 200 mA and
η = 70 %, the result is **≈ 126 mA**. That is about twice the 64 mA load.
Fig. 6-5 shows the same thing: the 0.9 V curve runs out at roughly 110 mA.
The converter can therefore hold the load down to the end of a cell's
useful life.

Peak inductor current at 0.9 V is about 0.45 A + 0.1 A of ripple, or
≈ 0.56 A. L1 (Murata DFE252012P-4R7M, I<sub>sat</sub> 2 A, I<sub>rated</sub> 1.4 A) has
plenty of margin.

## Estimated runtime (switch on, continuous)

| Battery | Behavior during discharge | Estimated runtime |
| --- | --- | --- |
| **Alkaline AA** (e.g. Energizer / Duracell) | Starts at ~244 mA. Current climbs past 400 mA as the cell sags. At this drain the cell's internal resistance grows near end of life, so the input collapses at a loaded ~0.9–1.0 V and much of the remaining energy is stranded | **~4.75–6.25 h** |
| **Panasonic eneloop AA** | The cell holds a flat ~1.2–1.25 V for most of the discharge, so current stays near ~320 mA. Low internal resistance (~20–30 mΩ) means little sag | **~5.75–6.25 h** |

Because the converter regulates, the LEDs stay at full brightness for the
whole run. They don't fade gradually. Near the end the badge drops out,
and an alkaline cell may let it blink or restart a few times as it recovers.
For predictable behavior, swap the cell when that starts.

At this ~320–450 mA drain, the eneloop delivers about as much energy as a
disposable alkaline, or slightly more, and its runtime varies less from cell to
cell. This is the normal result for moderate- to high-drain loads. Cheap
zinc-carbon ("heavy duty") cells are poorly suited to this load. Expect
roughly a third of the alkaline runtime or less.

**Eneloop note:** the converter keeps running far below 1.0 V. If the badge is
left on, it will drain the NiMH cell deeply. That doesn't harm a single cell
much, but switch the badge off once it dims or quits, and recharge promptly.

## Off state

With SW2 off, the cell is open-circuit. The only drain is the cell's own
self-discharge: a few % per year for alkaline, and the eneloop is rated
to keep ~70 % of its charge after 10 years.

## Component stress and thermal check

| Part | Worst case | Rating | Comment |
| --- | --- | --- | --- |
| **SW2, PCM12SMTR** | **244–454 mA** carried | **0.3 A at 6 V DC**, 70 mΩ max | **Above rating** once V<sub>bat</sub> drops below ~1.27 V. This covers the whole eneloop discharge (even a fresh cell) and most of an alkaline discharge. Contact loss is only ~14 mW at 454 mA, so it isn't a thermal problem. However, the switch is used beyond its datasheet rating, which may shorten contact life. Consider a switch rated ≥ 0.5 A |
| U1 TPS613222A | ~90 mW loss at 0.9 V (part in L1) | R<sub>θJA</sub> 190 °C/W | < +17 °C rise. Fine |
| L1 | ~0.56 A peak | I<sub>sat</sub> 2 A | Fine |
| C2 22 µF / 25 V X5R 0805 | 5 V bias | ≥ 10 µF effective required for 4.7 µH | A 25 V-rated 0805 part should keep roughly 12–15 µF at 5 V. That meets the minimum, but TI's table pairs 4.7 µH with 22 µF effective (2× 22 µF at heavy load). Check output ripple on the scope |
| Each 1 kΩ 0805 resistor | 5.4 mW (white), 6.5 mW (green) | 125 mW | Fine |
| Each LED | ~6.2 mW; 2.32 mA (white), 2.55 mA (green) | 20 mA | Fine |

Nothing on the board needs thermal attention. The one rating to watch is
SW2's current.

## How to verify on hardware

1. Measure the +5V rail. It should be 4.85–5.15 V.
2. Measure the voltage across a few 1 kΩ resistors, both white and green.
   1 V across the resistor means 1 mA. With a 5.0 V rail, expect ~2.32 V
   across white-LED resistors and ~2.55 V across green-LED resistors.
3. Put an ammeter in series with the cell (for example, a bench supply in
   place of the cell). Measure battery current at 1.5 V, 1.2 V and 1.0 V and
   compare it with the battery-current table. Use a short, low-resistance
   meter range: a 300–450 mA draw through a meter's shunt will pull the input
   down noticeably.
4. Run the badge from a fresh alkaline cell and from a fully charged eneloop
   until it drops out, to get real runtimes.
