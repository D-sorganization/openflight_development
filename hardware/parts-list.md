# OpenFlight Build — Parts List & Procurement Status

**Date:** 2026-07-30
**Sources:** upstream [docs/PARTS.md](https://github.com/jewbetcha/openflight/blob/main/docs/PARTS.md), [IWR6843 Operator Guide](https://github.com/jewbetcha/openflight/blob/main/docs/iwr6843/README.md), [sound-trigger wiring guide](https://github.com/jewbetcha/openflight/blob/main/docs/sound-trigger-wiring.md), `cad/IARC_case/`.

Target build: **current-generation stack** — OPS243 (speed/spin) + IWR6843LEVM (angles/club path) + SEN-14262 sound trigger on a Raspberry Pi 5. The K-LD7 path is deprecated upstream; do not buy K-LD7 hardware.

## Already have

| Item | Qty | Notes / action needed |
|------|-----|----------------------|
| OPS243 Doppler radar | 2 | ⚠️ **Verify variant.** Upstream requires the standard USB **OPS243** (57600 baud CDC-ACM). The **OPS243-A-W (WiFi)** locks serial to 19200 baud — too slow for I/Q transfer; PARTS.md calls it incompatible, and the IWR guide only allows it via a powered USB hub (Layout B) with degraded assumptions. Check the board for the WiFi module / "-W" marking. Two non-WiFi units = one for the build + one bench/dev unit (very useful for replay + driver work without touching the build). |
| SparkFun SEN-14262 sound detector | 1 | Needs the **R17 gain-mod resistor soldered** before use (see consumables below). |
| Rapsodo MLM2 Pro | 1 | Reference instrument for validation — not part of the build. Needs RPT balls for measured (not estimated) spin. |

## On order

| Item | Qty | Notes / action needed |
|------|-----|----------------------|
| TI IWR6843LEVM mmWave radar | 1 | ✅ **Variant confirmed 2026-07-31:** Digi-Key **296-IWR6843LEVM-ND**, MFG Texas Instruments **IWR6843LEVM** — exactly the board upstream targets (~$150, 60 GHz, 3 TX × 4 RX, CP2105 dual-UART USB bridge; firmware image, `.cfg`, S1 flash procedure, and enclosure geometry are all LEVM-specific). On arrival: verify silkscreen, identify USB connector type (data-capable cable), confirm S1 boot switch + RESET access — tracked in issue #8. |

## Need to buy — core (blocks the build)

| # | Item | Spec | Ref price | Why |
|---|------|------|-----------|-----|
| 1 | Raspberry Pi 5 | 4 GB+ RAM (8 GB is fine) | ~$130 | Main compute. Upstream setup targets Pi 5 explicitly (UART0 on `/dev/ttyAMA0`, lgpio pin factory). |
| 2 | 7" touchscreen | Either HMTECH 7" 1024×600 IPS (HDMI/USB, ~$46) **or** Raspberry Pi Touch Display 2 (DSI, ~$60) | ~$46–60 | Kiosk UI. Note: the IARC case has dedicated STLs for each display — pick the display **before** printing the case (`monitor_shell.stl` vs `Touch_Display2_*.stl`). |
| 3 | 27 W USB-C power supply | Official Pi 5 PSU, 5V/5A | ~$14 | Pi 5 + two radars is power-hungry; don't cheap out here. Upstream: treat intermittent USB disconnects as power problems first. |
| 4 | microSD card | 32 GB+ Class 10 / A2 | ~$10 | Pi OS (64-bit). Debug-mode IWR dumps are ~550 KB/shot — 64 GB is cheap insurance for long sessions. |
| 5 | USB-A → micro-USB cable | Data-capable | ~$5 | OPS243 connection (initial USB phase, and permanently if using Layout B). |
| 6 | USB cable for IWR6843LEVM | **Data-capable** (charge-only cables won't enumerate); check the connector on the board revision when it arrives | ~$5 | CP2105 serial bridge → Pi. |
| 7 | Dupont jumper wires, F-F | Assorted pack (need ≥8: 3× sound trigger, 4× OPS UART migration, 1× GATE→BCM17) | ~$7 | Sound trigger wiring + OPS GPIO-UART migration (Layout A). |
| 8 | Resistors, through-hole | **47 kΩ** (start) and **33 kΩ** (backup, noisy environments) | ~$2 | R17 gain mod on SEN-14262 — mandatory at 3.3 V or GATE sticks high. |

**Core subtotal: ~$220–235**

## Need to buy — conditional

| # | Item | Condition | Ref price |
|---|------|-----------|-----------|
| 9 | Powered USB hub (own external supply, e.g. Acer 4-port) | **Only if** an OPS turns out to be the WiFi variant, or you choose Layout B (both radars on USB) instead of the validated Layout A (OPS on GPIO UART). The Pi cannot power both radars over USB alone. | ~$20 |

## Need to buy / make — recommended extras

| # | Item | Why | Ref price |
|---|------|-----|-----------|
| 10 | 3D-printed IARC case v3 | `cad/IARC_case/` has the full STL/3MF set (monitor shell, OPS mount, sensor housing, feet). No printer → print service or a friend. ⚠️ **Gap:** the IARC case predates the IWR6843 — it has K-LD7 mounts but **no IWR6843LEVM mount** in `cad/IARC_case/stl/`. Check upstream for a newer mount; otherwise this is a contribution opportunity (design one). The IWR guide says the validated enclosure holds the board rotated so the vertical virtual array is physically vertical — replicate that constraint in any DIY mount. | ~$15 filament |
| 11 | Tripod / mount, 1/4"-20 | Positioning behind the tee (3–5 ft). A rigid mount matters: "small mechanical shifts can appear as angle bias." | ~$10 |
| 12 | Digital inclinometer or phone app | Measuring `--iwr6843-tilt-deg` (antenna-face tilt). Upstream is emphatic: **set tilt by physical measurement**, the calibration sweep cannot recommend one. A phone clinometer app on a flat reference surface works. | $0–15 |
| 13 | Tape measure (metric) | All IWR geometry flags are in meters (tee slant distance, net distance, radar height, ball height). Wrong values silently bias launch angle. | have? |
| 14 | Soldering iron + solder + heat-shrink | R17 resistor mod; the GATE three-way splice (detector GATE → OPS HOST_INT + Pi BCM17) must be soldered/secure, not twisted wires. A lever/Wago 3-way connector is an acceptable alternative for the splice. | tool |
| 15 | Callaway Chrome Soft X **RPT balls** (3+) | MLM2 Pro only *measures* spin with RPT-marked balls; otherwise it estimates. Without them the validation of OpenFlight's hardest metric (spin) has no ground truth. | ~$25/3-pack |
| 16 | Corner reflector (DIY foil or small trihedral) | Optional: verifies IWR horizontal aim on the target line during setup. | ~$0 DIY |
| 17 | Hitting net + mat | Presumably already owned with the MLM2 Pro. Remember: net distance is a measured input (`--iwr6843-net-m`), and ball height off mat (0.021 m) vs tee (0.040 m) ≈ 0.8° of launch angle. | have? |

## Explicitly do NOT buy

- **K-LD7 radars / FTDI adapters** — deprecated upstream, no further development.
- **OPS243-A-W (WiFi)** — incompatible baud rate for I/Q.
- **K-LD7 EVAL boards** — never needed even for legacy builds.
- **TI toolchain / UniFlash requirements** — the prebuilt firmware image flashes from the Pi via the checked-in `firmware/flash_iwr6843.py`; UniFlash is only a fallback.
- **DCA1000EVM / MMWAVEICBOOST carrier boards** — the LEVM's own CP2105 USB serial is the supported data path (verify against upstream docs when the board arrives; the operator guide references only the LEVM + USB).

## Ball-marking note (spin vs angles trade-off)

Upstream README: reflective stickers/dots improve angle-radar returns but wreck radar spin detection (specular pulse ≠ seam modulation); a thin painted stripe is the compromise. For validation sessions, decide per-session what's being validated — use RPT balls (MLM2 spin truth) with no extra reflective patches when validating OpenFlight spin.

## Budget summary

| Bucket | Est. cost |
|--------|-----------|
| Core remaining (items 1–8) | ~$220–235 |
| Conditional hub (item 9) | $0–20 |
| Extras (case, mount, RPT balls, misc) | ~$50–65 |
| **Total remaining spend** | **~$270–320** |
| Already sunk (2× OPS243, SEN-14262, IWR6843 on order) | ~$650 |

## Open verification tasks (tracked as issues)

1. Inspect both OPS243 units — confirm neither is the `-W` WiFi variant; label them A (build) and B (bench).
2. ~~Confirm the IWR6843 order line-item is **IWR6843LEVM**.~~ ✅ Done 2026-07-31 — Digi-Key 296-IWR6843LEVM-ND confirmed.
3. When the LEVM arrives: identify its USB connector type, buy the matching data cable if not on hand.
4. Decide display (HMTECH vs Touch Display 2) before printing case parts.
5. Check upstream `cad/` and issues for an IWR6843 case mount; if absent, plan to design one.
