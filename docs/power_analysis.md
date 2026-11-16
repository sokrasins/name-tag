# Power analysis

This is an estimate of the back board's (`nametag_back`) current draw and
battery life. It is worked out from the current schematic, the BOM, the
TPS61322 datasheet (`docs/datasheets/tps61322.pdf`, SLVSDY5E) and the
manufacturer listings for the LEDs and switch. I haven't measured a built board,
so treat these figures as calculated estimates and confirm them on hardware.

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
| LED V<sub>f</sub> at ~2.25 mA | 2.75 V (range 2.6–2.9 V) | Typical InGaN at ~10 % of rated current. The listing gives only 3.4 V at 20 mA |
| Output voltage | 5.0 V | Datasheet typical |
| Boost efficiency at ~61 mA out | 87 % at 1.5 V, 83.5 % at 1.2 V, 80 % at 1.0 V, 78 % at 0.9 V | Read from datasheet Fig. 6-5 (TPS613222A). That curve was measured with a 2.2 µH inductor. This board uses 4.7 µH, which has lower ripple, so efficiency is likely similar or slightly better |
| Alkaline AA usable energy | 1.8–2.3 Wh | Premium alkaline at ~350–390 mW constant power, down to ~0.9–1.0 V. The cell delivers noticeably less than its ~3 Wh low-drain rating at this load |
| Eneloop AA usable energy | 2.2–2.4 Wh | Panasonic eneloop standard (BK-3MCC) is 1900 mAh min / 2000 mAh typ × ~1.2 V. At this ~0.15 C rate, nearly all of the rated capacity is available |

## LED load (5 V rail)

Per-branch current is `(5.0 V − Vf) / 1 kΩ`. Both colors use the same
chemistry, so they run at about the same current.

| Case | Per LED | 27 LEDs | 5 V rail power | Lost in resistors | In LEDs |
| --- | --- | --- | --- | --- | --- |
| Low V<sub>f</sub> (2.6 V) | 2.40 mA | 64.8 mA | 324 mW | 156 mW | 168 mW |
| **Nominal (2.75 V)** | **2.25 mA** | **60.8 mA** | **304 mW** | **137 mW** | **167 mW** |
| High V<sub>f</sub> (2.9 V) | 2.10 mA | 56.7 mA | 284 mW | 119 mW | 164 mW |

U1's quiescent current (6.5 µA × 5 V ≈ 33 µW) is negligible.

The 1 kΩ resistors drop more than half of the rail voltage, so about 45 % of
the output power is turned into heat in the resistors. In exchange, LED
current varies only ±7% across the V<sub>f</sub> spread, and the white and
green LEDs come out evenly matched. At ~2.25 mA each, the LEDs run at about 
11% of their 20 mA rating.

## Battery current

The boost converter holds a constant 5 V, so the board draws constant
*power* from the cell. As the cell voltage falls, the battery current rises:

`I_bat = P_out / (η × V_bat)`, with P<sub>out</sub> = 304 mW

| V<sub>bat</sub> | 1.5 V (fresh alkaline) | 1.3 V (fresh eneloop) | 1.2 V (eneloop plateau / mid alkaline) | 1.0 V | 0.9 V |
| --- | --- | --- | --- | --- | --- |
| η | 87 % | 85 % | 83.5 % | 80 % | 78 % |
| Battery power | 349 mW | 357 mW | 364 mW | 380 mW | 389 mW |
| **Battery current** | **233 mA** | **275 mA** | **303 mA** | **380 mA** | **433 mA** |
| U1 + L1 loss | 45 mW | 54 mW | 60 mW | 76 mW | 86 mW |

### Converter headroom

Datasheet Eq. 1 gives the worst-case output capability:
`I_OUT(max) = V_IN × (I_LIM − I_LH/2) × η / V_OUT`. With V<sub>IN</sub> =
0.9 V, I<sub>LIM</sub> = 1.10 A (minimum), I<sub>LH</sub> = 200 mA and
η = 70 %, the result is **≈ 126 mA**. That is about twice the 61 mA load.
Fig. 6-5 shows the same thing: the 0.9 V curve runs out at roughly 110 mA.
The converter can therefore hold the load down to the end of a cell's
useful life.

Peak inductor current at 0.9 V is about 0.43 A + 0.1 A of ripple, or
≈ 0.55 A. L1 (Murata DFE252012P-4R7M, I<sub>sat</sub> 2 A, I<sub>rated</sub> 1.4 A) has
plenty of margin.

## Estimated runtime (switch on, continuous)

| Battery | Behavior during discharge | Estimated runtime |
| --- | --- | --- |
| **Alkaline AA** (e.g. Energizer / Duracell) | Starts at ~233 mA. Current climbs past 400 mA as the cell sags. At this drain the cell's internal resistance grows near end of life, so the input collapses at a loaded ~0.9–1.0 V and much of the remaining energy is stranded | **~5–6.5 h** |
| **Panasonic eneloop AA** | The cell holds a flat ~1.2–1.25 V for most of the discharge, so current stays near ~300 mA. Low internal resistance (~20–30 mΩ) means little sag | **~6–6.5 h** |

Because the converter regulates, the LEDs stay at full brightness for the
whole run. They don't fade gradually. Near the end the badge drops out,
and an alkaline cell may let it blink or restart a few times as it recovers.
For predictable behavior, swap the cell when that starts.

At this ~300–400 mA drain, the eneloop delivers about as much energy as a
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
| **SW2, PCM12SMTR** | **233–433 mA** carried | **0.3 A at 6 V DC**, 70 mΩ max | **Above rating** once V<sub>bat</sub> drops below ~1.2 V. This covers the whole eneloop discharge and the second half of an alkaline discharge. Contact loss is only ~13 mW at 433 mA, so it isn't a thermal problem. However, the switch is used beyond its datasheet rating, which may shorten contact life. Consider a switch rated ≥ 0.5 A |
| U1 TPS613222A | ~86 mW loss at 0.9 V (part in L1) | R<sub>θJA</sub> 190 °C/W | < +16 °C rise. Fine |
| L1 | ~0.55 A peak | I<sub>sat</sub> 2 A | Fine |
| C2 22 µF / 25 V X5R 0805 | 5 V bias | ≥ 10 µF effective required for 4.7 µH | A 25 V-rated 0805 part should keep roughly 12–15 µF at 5 V. That meets the minimum, but TI's table pairs 4.7 µH with 22 µF effective (2× 22 µF at heavy load). Check output ripple on the scope |
| Each 1 kΩ 0805 resistor | ~5 mW | 125 mW | Fine |
| Each LED | ~6 mW, 2.25 mA | 20 mA | Fine |

Nothing on the board needs thermal attention. The one rating to watch is
SW2's current.

## How to verify on hardware

1. Measure the +5V rail. It should be 4.85–5.15 V.
2. Measure the voltage across a few 1 kΩ resistors, both white and green.
   1 V across the resistor means 1 mA. Expect ~2.1–2.4 V across each
   resistor, which confirms the V<sub>f</sub> assumption.
3. Put an ammeter in series with the cell (for example, a bench supply in
   place of the cell). Measure battery current at 1.5 V, 1.2 V and 1.0 V and
   compare it with the battery-current table. Use a short, low-resistance
   meter range: a 300–400 mA draw through a meter's shunt will pull the input
   down noticeably.
4. Run the badge from a fresh alkaline cell and from a fully charged eneloop
   until it drops out, to get real runtimes.
