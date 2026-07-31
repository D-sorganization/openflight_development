# OpenFlight Building-Blocks Technical Dossier

## 1. OmniPreSense OPS243-A (24 GHz CW Doppler, primary speed sensor)

**Core specs** (OPS243 Product Brief OPS-PB-004-F, https://omnipresense.com/wp-content/uploads/2024/01/OPS243-Product-Brief_004-F.pdf; product page https://omnipresense.com/product/ops243-doppler-radar-sensor/):
- Operating frequency: 24.00–24.25 GHz ISM; **transmit power 11 dBm** (conducted; FCC/IC 2ALLL243A / 24107-243-A, CE modular approval)
- Antenna: **20° azimuth × 24° elevation** (−3 dB); FoV footprint ~0.4 m wide at 1 m, 1.8 m at 5 m, 3.5 m at 10 m (AN-029 Table 2)
- Detection: 1–100 m motion; speed reporting to 348 mph (at 50 ksps); speed accuracy "within 0.5%"
- Interfaces: USB CDC, UART (3.3 V, default 19,200 8N1, `In` up to 230,400), RS-232/WiFi variants; 5–24 V; 1.7 W active / 0.7 W idle; 75×90×12 mm, 15 g; −40…+85 °C

**API (AN-010-AD, https://omnipresense.com/wp-content/uploads/2025/10/AN-010-AD_API_Interface.pdf)** — key commands:
- Sample rate: `SI`=1k, `SV`=5k, `SX`/`S1`=10k (default), `S2`=20k, `SL`=50k, `SC`=100k, `S=n` arbitrary ksps, max 1,000 ksps. Max speed / resolution (1024 buffer): 10 ksps→31.1 m/s @0.061 m/s; 20→62.2 @0.121; 50→155.4 m/s (347.7 mph) @0.304; 100→310.8 @0.608. Resolution degrades 2×/4×/8× at 512/256/128 buffer.
- Buffer size: `S>`=1024 (default), `S<`=512, `S[`=256, `S(`=128. Zero-padding: `Xn` (1,2,4,8), `X=16`/`X=32` — pads FFT to 4096 (e.g., 128 samples + X=32 → 0.1 mph resolution at ~200 Hz report rate).
- Output: `OJ` JSON, `OT` timestamps, `OM` magnitude, `ON`/`O=n` multi-object (up to 16), `OV` largest-first, `OF` post-FFT, **`OR` raw I/Q ADC output**, `OP` phase (243-C only).
- Filters: speed `R>n`/`R<n`, direction `R+`/`R-`/`R|`, magnitude `M>n`/`M<n` (default M>20), peak averaging `K+`, blank reporting `BZ/BL/BS/BC/BT`, cosine-error correction `^/+n.n` / `^/-n.n` (0–89°).
- Units `US/UK/UM/UC/UF`; precision `Fn`; power `PA`; persist `A!`; info `??`; counters `N?`/`N!`/`N>n`/`N<n`.
- **HOST_INT**: J3 pin 3. Output mode (`IG`): high = no motion, low = motion. Input mode: rolling-buffer hardware trigger.

**Rolling buffer (AN-027-A, https://omnipresense.com/wp-content/uploads/2025/06/AN-027-A_Rolling-Buffer-1.pdf)** — OPS243-A-only:
- `G1` enter, `G0` exit, `PA` re-arm. Fixed **4096-sample I/Q buffer = 32 segments × 128 samples**.
- Trigger: software `S!` or **3.3 V rising edge on J3 pin 3**. `S#n` (0–32) pre/post split; default n=8 → 1024 pre + 3072 post samples. Output: I & Q arrays + buffer-start and trigger timestamps.
- Sampling-time table: 30 ksps → 136.5 ms buffer, max 93.2 m/s (208.5 mph) — the "golf ball setting"; 50 ksps → 81.9 ms, 347 mph; 500 ksps → 8.2 ms.
- Reference Python (OmniPreSense GitHub): per-128-sample Hann-windowed complex FFT zero-padded to 4096 → 32 speed reports/buffer, top-5 magnitudes per block, JSON.
- **AN-027 shows a SparkFun SEN-14262 wired to HOST_INT** (Gate → pin 3). Acoustic latency: sound at 2 m arrives ~6.6 ms late; budget pre-trigger accordingly (example `S#18`).

**Sports/golf app note AN-029-A (June 2026, https://omnipresense.com/wp-content/uploads/2026/06/AN-029-A_OPS243-for-Sports_260621.pdf)** — golf recipe: `S=30` (209 mph max), `S(` 128 samples, `X=32` (4096 FFT, 0.1 mph), `US`, `R>10` (mask waggle), `M>10`, `O2` (ball + club → smash 1.0–1.50), `K+`; sensor 2–3 m behind ball; golf ball reflectivity "High", detectable 5–10 m; ~200 Hz report rate. **AN-029 cites the OpenFlight GitHub project by name as the reference OPS243-A golf launch monitor code.**

## 2. RFbeam K-LD7 (24 GHz FSK Doppler, angle via dual-RX phase)

Datasheet Rev A 09/2019: https://rfbeam.ch/product/k-ld7-radar-transceiver/ (PDF mirror: https://efo.ru/storage/pdf/RFbeam/Datasheet_K-LD7.pdf)

- **RF**: 24.050–24.250 GHz, FSK (two discrete freqs A/B); EIRP **6 dBm**; antenna gain 8.6 dBi; 1 TX + **2 I/Q RX** (spacing **6.223 mm** ≈ λ/2); 3×4 patch, **80° H × 34° V** −3 dB; sidelobes −12…−20 dB; sensitivity −127 dBc; person (σ=1 m²) 15 m, cars 30 m.
- **Processing**: 256-point complex FFT/frame. Speed 0.1–100 km/h, resolution 0.1–0.8 km/h by range setting; distance 0.005–100 m via FSK phase difference (5/10/30/100 cm resolution at 5/10/30/100 m settings); **angle ±90°, 1° resolution, from Rx1–Rx2 phase difference**; tracking to 30 m (single target). Frame: 12.5 km/h→229 ms; 25→114 ms; 50→57 ms; **100 km/h→29 ms (~34 Hz)**. NOTE: 100 km/h = 62 mph ceiling → K-LD7 only viable for club-head/angle work, not direct ball speed.
- **Supply** 3.2–5.5 V; 38×25×13.5 mm; four configurable digital outputs.
- **UART protocol**: default **115200 8E1**; `INIT` selects up to 3 Mbaud; `GBYE` reverts. Packet = 4-ASCII header + UINT32 LE payload length + payload (≤3072 B). `RESP` ack codes 0–5.
  - **RADC** (3072 B): 256 I + 256 Q UINT16 for Rx1@fA, Rx2@fA, Rx1@fB — raw ADC streaming.
  - **RFFT** (1024 B): 256 spectrum + 256 threshold UINT16.
  - **PDAT** (0–96 B): per raw target {Distance cm UINT16, Speed km/h×100 INT16, Angle deg×100 INT16, Magnitude UINT16} — up to 12 targets.
  - **TDAT** (0–8 B): same struct, single tracked target. **DDAT** (6 B): flags. **DONE** (4 B): frame counter.
  - Request via `GNFD` bitfield (0x01 RADC … 0x20 DONE).
  - Config: `GRPS`/`SRPS` (42-B structure) or singles: `RBFR` base freq (3 channels), `RSPI` max speed, `RRAI` max range, `THOF` threshold offset 10–60 dB, `TRFT` tracking filter, `VISU` vibration suppression, MIRA/MARA/MIAN/MAAN/MISP/MASP detection window, DEDI direction, RATH/ANTH/SPTH thresholds, DIG1-3, HOLD, MIDE/MIDS micro-detection.
- Sign convention: positive speed = receding; tangential motion needs cos(α) correction.

## 3. TI IWR6843 / EVMs (60–64 GHz FMCW MIMO)

- **Datasheet** (SWRS219, https://www.ti.com/lit/ds/symlink/iwr6843.pdf; https://www.ti.com/product/IWR6843): 60–64 GHz, **4 GHz chirp bandwidth** (~3.75 cm native range resolution), **3 TX / 4 RX = 12 virtual antennas** (TDM/BPM-MIMO). On-chip: Cortex-R4F MSS, C674x DSP, radar HW accelerator (FFT/log-mag/CFAR), 1.75 MB RAM incl. 768 KB radar cube. Complex-baseband ADC to 12.5 Msps.
- **EVMs**: IWR6843ISK (https://www.ti.com/tool/IWR6843ISK) — ~120° az / 30° el FoV, 8 virtual az antennas (~15° az resolution, coarse elevation), XDS110 dual UART. IWR6843ISK-ODS — wide FoV, square virtual array (equal az/el). IWR6843AOPEVM (https://www.ti.com/tool/IWR6843AOPEVM) — antenna-on-package ~130°×130°. IWR6843LEVM user guide: https://www.mouser.com/datasheet/2/405/1/swru585_pdf_3fts_3d1685695215835_26ref_url_3dhttps-2930530.pdf
- **Software**: mmWave SDK OOB demo streams TLV point cloud (x,y,z,doppler) over 921600-baud UART after CLI chirp profile; mmWave Studio + DCA1000 for raw ADC. Radar Toolbox labs: 3D people tracking, TIDEP-01000, TIDEP-01010 (trajectory). Placement app note SWRA758: https://www.ti.com/document-viewer/lit/html/SWRA758. EVM comparison: https://mmwave-radar.dev/ti-mmwave-evm-comparison.html
- **Golf precedent**: TI E2E "Golf Swing Analyzer with mmWave Radar" (no tailored lab; start from OOB): https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/1116424/iwr6843aop-golf-swing-analyzer-with-mmwave-radar; mmWave golf-tracking write-ups: https://linpowave.com/blog/golf-ball-tracking-mmwave-radar. Implication: OOB point cloud (~10–20 Hz) is marginal for 3 ms launch windows — custom chirp config + low-level processing needed.

## 4. Raspberry Pi Global Shutter Camera (IMX296)

- Sony **IMX296LQR-C**, 1/2.9", **1456×1088 (1.58 MP)**, 3.45 µm pixels, global shutter, C/CS-mount; **max ~60 fps** full-res; exposure down to ~30 µs. Docs: https://www.raspberrypi.com/documentation/accessories/camera.html
- **External trigger (XTR pad)**: pulse XTR low; **exposure = low-pulse width + 14.26 µs**; frame rate = pulse frequency; multiple cameras on one trigger line = hardware sync. Enable: `v4l2-ctl -d /dev/v4l-subdev0 -c trigger_mode=1`. Early boards: if Q2 fitted, **remove R11** or trigger mode fails. Forums: https://forums.raspberrypi.com/viewtopic.php?t=353039, t=349260, t=375454
- Third-party IMX296 trigger variants: https://www.inno-maker.com/product/cam-mipi296raw-trigger/, Arducam IMX296 M12. Note: 60 fps << 2000+ fps commercial — GS camera is for strobed multi-exposure stills (spin/impact), not continuous flight capture.

## 5. Simulator integration protocols

**GSPro Open Connect v1** (https://gsprogolf.com/GSProConnectV1.html):
- JSON over **TCP port 0921, 127.0.0.1** (GSPro Connect = server; LM = client; bidirectional, no auth).
- Shot root: `DeviceID` (req), `Units` ("Yards"), `ShotNumber` (req, increment), `APIversion` ("1"), `BallData` (req), `ClubData` (opt), `ShotDataOptions` (req).
- **BallData**: `Speed` (mph, req), `SpinAxis` (deg, req; negative = draw tilt), `TotalSpin` (rpm) OR `BackSpin`+`SideSpin`, `HLA` (deg, req), `VLA` (deg, req), `CarryDistance` (opt).
- **ClubData**: `Speed`, `AngleOfAttack`, `FaceToTarget`, `Lie`, `Loft`, `Path`, `SpeedAtImpact`, `VerticalFaceImpact`, `HorizontalFaceImpact`, `ClosureRate`.
- **ShotDataOptions**: `ContainsBallData` (req), `ContainsClubData` (req), `LaunchMonitorIsReady`, `LaunchMonitorBallDetected`, `IsHeartBeat`.
- Responses: 200 shot ack; `{"Code":201,"Player":{"Handed":"RH","Club":"DR"}}` push; 501/5xx errors. Feedback/gotchas: https://github.com/tnbozman/gspro-interface/blob/main/OpenAPI-Documentation-Feedback.MD; reference impls: https://github.com/travislang/gspro-garmin-connect-v2, https://github.com/kenjdavidson/gspro-connector
- **E6 Connect (TruGolf)**: closed SDK, per-device licensing; PiTrac got in via partnership. https://trugolf.com/pages/e6-connect. **Foresight FSX**: no public LM-input API. **Awesome Golf**: supported-device model. Conclusion: **GSPro Open Connect is the only documented open protocol — make it OpenFlight's native output.**

## 6. Ball & equipment constants

- **Ball** (USGA/R&A): mass **≤ 45.93 g**; diameter **≥ 42.67 mm**; spherical symmetry. **Initial velocity ≤ 250 ft/s +2%** (TPX3007: https://www.usga.org/content/dam/usga/pdf/Equipment/TPX3007-initial-velocity-test-procedure.pdf). **ODS: 317 yd + 3 yd** at ALC — 120 mph clubhead, 10°, 2520 rpm; **from Jan 2028: 125 mph (~183 mph ball), 11°, 2200 rpm** (TPX3006; https://www.usga.org/content/usga/home-page/articles/2023/12/revised-golf-ball-testing-conditions-to-take-effect-in-2028.html).
- **Clubhead**: **CT = 239 µs + 18 µs tolerance** ≈ COR 0.830 (TPX3004; https://www.randa.org/en/articles/spring-effect-and-dynamic-properties). **MOI ≤ 5900 + 100 g·cm²** vertical axis (TPX3005). Volume ≤ 460 + 10 cc. Typical driver: 195–205 g head, CG 35–40 mm behind face, Izz 4500–5900 g·cm². Smash ceiling ~1.50 (AN-029 gates 1.0–1.50).

## 7. Micro-Doppler / tracking literature, CFAR

- Spin via micro-Doppler: spinning ball spreads the Doppler line ±ωr about translation; periodic modulation from dimples/seams/inhomogeneity. Densest technical descriptions are the TrackMan patents (US20140191896, US10393870/US11143754, US10850179/US11446546/US11938375).
- Papers: "Simulation of Golf Realtime Tracking Based on Doppler Radar" (https://www.scientific.net/AMM.743.828); "Drag on sports balls using Doppler radar" (https://www.researchgate.net/publication/257724512); LM validation vs radar/optical (https://www.researchgate.net/publication/319147118); mmWave table-tennis agility (https://doi.org/10.3390/computers15010028); tennis-ball radar detectability (https://www.cambridgewireless.co.uk/resource/can-radar-detect-tennis-balls-news-article-4598.html).
- **CFAR**: MATLAB tutorial (CA/GO/SO/OS, Pfa math): https://www.mathworks.com/help/phased/ug/constant-false-alarm-rate-cfar-detection.html; Purdue notes: https://engineering.purdue.edu/~mrb/resources/AltLectureF/Session_21.pdf; practical series: https://medium.com/@itberrios6/adaptive-radar-detection-part-1-ec3c318d5da1. CA-CFAR = mean of training cells + guard cells, threshold α·P̂n; OS-CFAR (k-th order statistic) better for closely spaced targets (club+ball) at ~0.5–1 dB loss.

**Cross-cutting notes**: (a) AN-029 blesses the exact OpenFlight architecture and links the project; (b) K-LD7 100 km/h ceiling → angle/club only; (c) IWR6843 needs custom chirps for launch windows; (d) GSPro Open Connect = the open output; Speed/SpinAxis/TotalSpin/HLA/VLA is the minimum viable tuple.
