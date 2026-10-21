# Power analysis

This is an estimate of the back board's (`nametag_back`, schematic Rev 2)
current draw and battery life, worked out from the schematic. The LEDs have
no manufacturer part numbers in the schematic, and I haven't measured a built
board, so the figures below are calculated from typical part values. Measure a
real board to confirm them.

## Circuit summary

```
AAA cell ─ SW2 ─ L1 4.7 µH ─ U1 TPS613221A (boost) ─ +3V3 ─┬─ 27× (LED + 1 kΩ) ─ LIGHT_CTRL ─ Q1 BSS138 ─ GND
                                                           └─ RV1 10 kΩ pot ─ GND   (wiper → Q1 gate, CTRL)
```

- **Source:** one AAA cell (BT1). SW2 is an SPDT switch: when it is off, it
  disconnects the cell and ties the converter input to GND.
- **Regulator:** a TI TPS613221A synchronous boost converter with a fixed
  3.3 V output. TI specifies 0.9–5.5 V input, 6.5 µA quiescent current into
  VOUT, and a 0.75 A minimum switch peak current limit.
- **Load:** 27 LED/resistor branches in parallel (22 yellow for the name area,
  5 green for the wrench). Each branch is +3V3 → LED → 1 kΩ → `LIGHT_CTRL`. All
  branches share one BSS138 low-side MOSFET.
- **Brightness:** RV1 is wired across +3V3/GND and its wiper drives Q1's gate,
  so Q1 works as a variable resistor. It is fully on when the wiper is near
  3.3 V and off when the wiper is below the BSS138's gate threshold (about
  0.8–1.5 V).

## Assumptions

| Parameter | Value used | Notes |
| --- | --- | --- |
| Yellow LED Vf at ~1.4 mA | 1.85 V | Typical AlInGaP at low current |
| Green LED Vf at ~1 mA | 2.7 V (InGaN) or 1.95 V (AlInGaP yellow-green) | The part's chemistry decides which applies |
| Q1 R<sub>DS(on)</sub> at V<sub>GS</sub> = 3.3 V | 2 Ω | BSS138 typical. The drop is under 80 mV, so this barely matters |
| Boost efficiency | 87 % at 1.5 V, 85 % at 1.2 V, 80 % at 1.0 V, 78 % at 0.9 V | Estimated for a ~110–130 mW load. Not read from the datasheet curves |
| Alkaline AAA usable energy | 1.0–1.2 Wh | At ~130–150 mW constant power down to 0.9 V |
| NiMH AAA usable energy | ~0.96 Wh | 800 mAh × 1.2 V |

## Maximum brightness (Q1 fully on)

Per-branch current is `(3.3 V − Vf − V_DS) / 1 kΩ`.

| Case | Yellow, each | Green, each | LED total | + Pot | 3V3 rail load |
| --- | --- | --- | --- | --- | --- |
| Green = InGaN (Vf 2.7 V) | 1.38 mA | 0.53 mA | 33.1 mA | 0.33 mA | **33.4 mA / 110 mW** |
| Green = AlInGaP (Vf 1.95 V) | 1.38 mA | 1.28 mA | 36.7 mA | 0.33 mA | **37.0 mA / 122 mW** |
| Low-Vf corner (1.75 / 1.85 V) | 1.47 mA | 1.37 mA | 39.2 mA | 0.33 mA | **39.6 mA / 131 mW** |

Here is where the power goes in the first two cases: about 44–50 mW in the 1 kΩ
resistors, about 2–3 mW in Q1, about 1 mW in RV1, and the rest in the LEDs.

If the wrench uses true green (InGaN) LEDs, they run at about 40 % of the
yellow LEDs' current. With only 3.3 V and a 1 kΩ resistor, there is little
headroom above their ~2.7 V forward voltage. Unless the parts are yellow-green
AlInGaP, expect the wrench to look noticeably dimmer than the name area. Using
a lower resistor value on R21–R25 (e.g. 330–470 Ω) would even them out.

## Battery current at maximum brightness

Because the boost converter holds a constant 3.3 V, the load draws constant
*power*. Battery current therefore rises as the cell discharges.

Battery current = P<sub>out</sub> / (η × V<sub>bat</sub>), using the 110–122 mW
nominal range:

| V<sub>bat</sub> | Fresh alkaline 1.5 V | 1.2 V (NiMH / mid-life alkaline) | 1.0 V | 0.9 V (near end) |
| --- | --- | --- | --- | --- |
| Battery current | 85–94 mA | 108–120 mA | 138–153 mA | 157–174 mA |
| Battery power | 127–140 mW | 130–144 mW | 138–153 mW | 141–157 mW |

Even in the low-Vf corner, these currents are well under the TPS613221A's
0.75 A minimum switch current limit. A rough estimate of the output capability
at 0.9 V input is above 100 mA, which leaves about 2.5× margin over the LED
load.

## Estimated runtime

| Battery | Max brightness | ~50 % LED current |
| --- | --- | --- |
| Alkaline AAA | **~7–9 h** | ~14–18 h |
| NiMH AAA (800 mAh) | **~6.5–7.5 h** | ~13–15 h |

Dimming with RV1 doesn't waste power: the rail stays at 3.3 V, so input power
scales roughly with LED current. Battery life also improves a little at lower
drain, because alkaline cells deliver more energy at lower currents.

The converter stops starting below about 0.9 V, so in practice the badge will
dim and then quit at the end of a cell's useful life.

## Dimmed and off states

- **Pot fully down (LEDs off, switch on):** the only loads are RV1 (3.3 V /
  10 kΩ = 330 µA) and the converter's ~6.5 µA quiescent current. That's
  about 1.1 mW, or ~1 mA from the cell. A fresh alkaline AAA would last on
  the order of a month in this state. **RV1 is the main standby load**, so a
  higher-value pot (e.g. 100 kΩ) would cut it 10×.
- **Switch off:** SW2 fully disconnects the cell, so the drain is effectively
  zero (only cell self-discharge).

## Thermal check

| Part | Worst-case dissipation | Comment |
| --- | --- | --- |
| Q1 BSS138, fully on | ~3 mW | Negligible |
| Q1 BSS138, half-dimmed (linear region) | ~12–15 mW | Peak occurs at V<sub>DS</sub> ≈ (3.3 − Vf)/2. This is far below the SOT-23's ~350 mW rating |
| Each 1 kΩ 0805 resistor | ~2 mW | 0805 parts are rated 125 mW |
| Each LED | ~2.5–3 mW | Running at under 10 % of a typical 1206 LED's 20 mA rating |

Nothing on the board needs thermal attention.

## How to verify on hardware

1. Put an ammeter in series with the AAA cell (break the circuit at SW2 or at
   the battery clip). Measure at full and minimum brightness with a fresh cell
   and a ~1.2 V cell. Compare the readings with the battery-current table
   above.
2. Measure the voltage across one yellow and one green 1 kΩ resistor at full
   brightness. 1 V across the resistor means 1 mA, which confirms each color's
   per-LED current.
3. Run the badge from a fresh cell at full brightness to get the real runtime.
