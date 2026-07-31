# Golf Launch Monitor Patent Landscape — Research Dossier

Compiled 2026-07-30 from Google Patents, USPTO, Justia, and trade press. All patent pages verified via patents.google.com unless noted. Expiry estimates: US utility patents ≈ 20 years from earliest non-provisional priority, plus patent-term adjustment (PTA); Google Patents "anticipated expiration" used where shown.

**Correction to the research brief:** US7864103 is *not* a TrackMan patent — it is "Device and method for 3D height-finding avian radar" (Accipiter Radar Technologies, bird radar). The TrackMan spin patent family is **US8845442 / US10393870** (US national members of the famous **EP 1 698 380** family).

---

## 1. TrackMan A/S (originally Interactive Sports Games A/S) — Fredrik Tuxen

TrackMan's public patent list (https://www.trackman.com/legal/patents) enumerates **45 US patents**, from US8,085,188 to US12,539,454. Claimed patented capabilities: full-trajectory radar tracking, club delivery data (path/plane/attack angle), radar spin rate and spin axis, markerless clubface impact location, and OERT (Optically Enhanced Radar Tracking = radar + optical fusion, used in TrackMan 4 and TrackMan iO).

### US8845442B2 — "Determination of spin parameters of a sports ball" ⭐ THE crown-jewel spin patent
- URL: https://patents.google.com/patent/US8845442B2/en
- Assignee: TrackMan A/S. Inventor: Fredrik Tuxen.
- Priority: **March 3, 2005** (filed Feb 28, 2006). Status: active, listed expiry **May 18, 2029** (PTA-extended).
- **Method — spin rate from Doppler harmonics:** a CW Doppler radar receives reflections from the rotating ball. Rotation frequency-modulates the return, producing **equally spaced harmonic sidebands symmetric around the central Doppler (velocity) frequency**. The algorithm: identify the central velocity trace, detect candidate sidebands, track them over time as "spectral traces," qualify harmonics by verifying constant equal spacing, and divide sideband offset by harmonic number → spin frequency.
- **Method — spin axis from trajectory:** from the measured 3D trajectory, compute total acceleration, subtract gravity and drag; the residual is Magnus lift, always perpendicular to the spin axis (L·ω = 0). Solving that constraint across multiple trajectory points by linear least squares yields spin-axis orientation. (Note: TrackMan's spin *axis* is inferred aerodynamically, not measured directly.)
- **Litigation pedigree:** the European sibling **EP 1 698 380** (DE 60 2006 009 719) was upheld by Germany's Federal Court of Justice and was the basis of TrackMan's 2013 Düsseldorf infringement win against the distributor of FlightScope's X2.
- **OpenFlight relevance:** this is the single most important patent for any radar-based DIY monitor. The harmonic-sideband spin-rate method and trajectory-derived spin axis are both claimed. The US member carries PTA to ~2029 and continuation **US10393870** runs to Dec 2026 — check claim-by-claim before shipping a radar spin extractor commercially; post-2029 (and already for expired EP members, verify per-country) this becomes the canonical public-domain recipe.

### US10393870B2 — same title, continuation
- URL: https://patents.google.com/patent/US10393870B2/en
- Same disclosure (priority Mar 3, 2005); expiry listed **Dec 21, 2026**. Restates spin frequency via equally spaced sidebands and spin axis via lift-vector perpendicularity.

### US8085188B2 / US9857459B2 / US10473778B2 — "Method... for determining a deviation between an actual direction of a launched projectile and a predetermined direction" (radar+camera family)
- URLs: https://patents.google.com/patent/US8085188B2/en , https://patents.google.com/patent/US9857459B2/en , https://patents.google.com/patent/US10473778B2/en
- Assignee: TrackMan (orig. Interactive Sports Games). Inventor: Tuxen. Priority: **July 2, 2004**.
- Status: US9857459 expired Nov 2022 (fee related); US10473778 expires Sep 2026; US8085188 listed to Jun 2027.
- **Method:** camera rigidly mounted to the radar images the range/target area; user taps a target in the image; system correlates image position → world coordinates; radar measures actual launch position, flight path, landing; system computes intended line (launch→target) and reports angular/distance deviation, with automatic transforms among radar, camera, and "golfer" coordinate systems (no mechanical re-aiming). Target distance can be derived from the angular extent of a known pattern.
- **OpenFlight relevance:** covers the ubiquitous "aim at a target in a camera view, score dispersion" UX for radar units. Family is expired/near-expiry — a safe pattern to adopt soon.

### US10315093B2 — "Systems and methods for illustrating the flight of a projectile"
- URL: https://patents.google.com/patent/US10315093B2/en
- Inventors: Tuxen, Frederik Ettrup Brink. Priority Jan 29, 2009; expires Sep 2030.
- **Method:** correlate radar-tracked trajectory with camera imagery via calibration; render the tracer/trajectory line into the video frame (the "TrackMan tracer" broadcast overlay); also impact-point identification, post-impact spin, 3D impact vectors, velocity-adaptive replay.
- **OpenFlight relevance:** claims the radar-data-drawn-into-video tracer overlay. Relevant if OpenFlight adds video tracers driven by sensor data.

### US11086005B2 — "Device, system, and method for tracking multiple projectiles"
- URL: https://patents.google.com/patent/US11086005B2/en
- Priority Jul 11, 2016; expires ~2036. **Method:** one or more radars covering many hitting bays (Toptracer-Range-style); tracks are extrapolated backward in time to a launch location to assign each shot to a bay/user (with GPS-phone user association); multi-radar coordinate fusion, Doppler-spectrum peak detection, trajectory smoothing.
- Relevance: driving-range/multi-bay architecture — long-lived patent; avoid multi-bay back-extrapolation attribution schemes.

### Club data / impact location (TrackMan)
TrackMan states club delivery (path, attack angle, face-related numbers), **markerless impact location**, and **OERT radar+optical fusion** are patented processes; specific numbers sit within the 45-patent list (e.g., US10444339, US11291902, US11951372 "System and method for tracking sports balls," US12036465, etc. — not individually verified here). Trade press confirms "dual radar" (separate club radar + ball radar) in TrackMan 4. For OpenFlight: measuring club path/attack angle from a Doppler club return is old physics, but the specific fused radar+camera impact-location pipeline is actively protected into the late 2030s–2040s. Radar+image 3D tracking family: US 10,596,416 / 11,697,046 / 12,128,275; spin-axis family US 10,850,179 / 11,446,546 / 11,938,375; full Tuxen portfolio: https://patents.justia.com/inventor/fredrik-tuxen.

---

## 2. Foresight Sports (WAWGD, Inc.; patents held via Wawgd Newco LLC) + the Wintriss Engineering lineage

Key structural finding: **Foresight Sports = WAWGD, Inc.**, and the foundational single-camera photometric patents it now owns were invented at **Wintriss Engineering Corp (San Diego)** by **Christopher Kiraly** (Foresight co-founder) — current assignee "Wawgd Newco LLC." These same patents (US7292711, US7324663, US7497780, US7641565) appear on **Uneekor's license list**, matching the Sep 2024 Foresight↔Uneekor license of "portable golf launch monitor screen technology" patents (https://www.businesswire.com/news/home/20240930838753/en/).

### US7292711B2 — "Flight parameter measurement system" ⭐ foundational camera launch monitor patent
- URL: https://patents.google.com/patent/US7292711B2/en
- Inventors: Christopher M. Kiraly, George Victor Wintriss. Priority **June 6, 2002**. **Expired April 2025.**
- **Method:** single-camera photometric monitor. Factory calibration maps every pixel to a 3D direction vector; field leveling via accelerometer/inclinometer; trigger via microphone + small radar horn (joint impact/motion detection to kill false triggers); strobe-lit sequential images; ball center/diameter in each frame + known ball diameter → 3D position per frame → speed and launch angles. **Markerless spin:** track natural features ("non-precision marks, surface blemishes... dimples") by iterative rotation/scale/correlation of successive ball images, after glint removal and radial lighting normalization → spin axis and rate.
- **OpenFlight relevance:** *This is the blueprint for an open-source camera launch monitor, and it is now expired.* The whole pipeline — mono-camera 3D from known ball diameter, feature-correlation spin without stickers — is free to implement.

### US7324663B2 — "Flight parameter measurement system" (sibling, same spec)
- URL: https://patents.google.com/patent/US7324663B2/en — priority Jun 6, 2002; **expired Aug 2025**. Single "smart camera" (sensor+FPGA+CPU), self-triggering from motion in FOV, same markerless spin correlation. Also expired → public domain.

### US7497780B2 — "Integrated golf ball launch monitor"
- URL: https://patents.google.com/patent/US7497780B2/en
- Inventor: Kiraly. Priority **June 12, 2006**; expires ~Apr 2027.
- **Method:** the GC2-style user experience: optical ball-find in a trigger zone (roundness/dimples/reflectivity/size), LED indicators guiding ball placement into the strike zone (depth from image diameter), high-speed low-res trigger mode detecting launch via frame differencing (rejecting nudges), then mixed-mode capture (high-res frames for spin, fast frames for speed/direction), on-device computation and display.
- Relevance: covers the "put the ball where the light says, then just hit" integrated-device workflow until ~2027.

### US7641565B2 — "Method and apparatus for detecting the placement of a golf ball for a launch monitor"
- URL: https://patents.google.com/patent/US7641565B2/en — Kiraly/Wintriss lineage; ball-placement detection companion to the above (on Uneekor's license list). Filed ~2006/2007, expiry ~2027.

### Later Foresight (WAWGD) filings
Justia lists WAWGD, Inc. DBA Foresight Sports applications on measuring **club path and face orientation before/at/after impact** (the 4-dot GCQuad club-face fiducial system) — see https://patents.justia.com/inventor/wawgd-inc-dba-foresight-sports. The 2024 Uneekor license confirms Foresight also holds newer patents on portable-monitor *screen/display* configurations. Treat quad-camera + reflective-dot club-face measurement as actively protected.

---

## 3. FlightScope / EDH (Henri Johnson, Stellenbosch SA; US entity EDH US LLC)

History: EDH founded 1989 (muzzle-velocity Doppler radar); phased-array golf tracking patent filed 2002 but not aggressively prosecuted; FlightScope introduced at 2004 PGA Show. In Nov 2022 FlightScope **won at Germany's Federal Court of Justice against TrackMan** in a separate infringement matter (https://golfbusinessnews.com/news/innovation-centre/flightscope-wins-patent-infringement-case-against-trackman-in-germany/).

### US9868044B2 — "Ball spin rate measurement" ⭐ the dielectric-lens direct-spin patent
- URL: https://patents.google.com/patent/US9868044B2/en
- Assignee: EDH US LLC. Inventors: Henri Johnson, Thomas Johnson, Robert William Rust. Priority **Jan 10, 2013**; expires ~Apr 2034.
- **Method:** exploits the golf ball acting as a **dielectric lens (n≈1.8)** that magnifies far-side surface features in the microwave return. Receive → mix with TX-derived reference → demodulate phase (PLL) → time-varying signal showing **repeating bipolar pulses** as seams/features sweep the magnification zone; FFT extracts the periodicity; seam symmetry yields modulation at 2× spin rate, corrected in the computation. Direct spin measurement without markers or sideband harmonics — deliberately engineered around TrackMan's EP1698380 after the 2013 loss.
- **OpenFlight relevance:** the main *alternative* radar spin method; protected to 2034. An open implementation should be aware both major radar spin routes (harmonic sidebands, phase-demod lens pulses) are/were patented, with the TrackMan route expiring first.

### US10775492B2 — "Golf ball spin axis measurement"
- URL: https://patents.google.com/patent/US10775492B2/en
- EDH US LLC; Henri Johnson. Priority **Dec 3, 2013**; expires ~Mar 2035.
- **Method:** interferometric/phased receiver approach — ≥2 receiver pairs in perpendicular planes; demodulate Doppler returns; measure time delays between vertically and horizontally spaced pairs; spin-axis angle **PHI = arctan[S_H·T_H/(S_V·T_V)]**. Direct axis measurement (works indoors, short flights) vs TrackMan's aerodynamic inference.

### US10338209B2 — "Systems to track a moving sports object" (Fusion Tracking)
- URL: https://patents.google.com/patent/US10338209B2/en
- EDH US LLC; Henri Johnson. Priority Apr 28, 2015; expires ~Jul 2037.
- **Method:** radar+camera fusion: checkerboard camera calibration; radar alignment via a Doppler signal simulator; radar gives radial distance + angles, camera gives precise angular position via frame differencing/morphology; fusion removes inter-sensor systematic offsets by error minimization; radar predictions steer image search windows; outputs world-coordinate tracks and broadcast tracer overlays. Basis of FlightScope X3/Mevo+ "Fusion Tracking."

---

## 4. Acushnet (Titleist) — the photometric foundation (Gobush et al.)

The deepest prior art for any camera-based monitor. All the early ones are **expired**.

### US5501463A — "Method and apparatus to determine object striking instrument movement conditions" (1992) — EXPIRED
- URL: https://patents.google.com/patent/US5501463A/en
- Acushnet; William Gobush, Diane Pelletier, Charles Days. Priority Nov 20, 1992.
- **Method:** two shuttered cameras at ~22°, strobed twice ~800 µs apart; **3 retroreflective dots on the clubhead, 6 on the ball**; triangulation of dot positions across views/frames → 3D clubhead velocity, attack angle, path, orientation, and **contact location on the face** pre-impact.

### US6500073B1 — "Method and apparatus to determine golf ball trajectory and flight" (1992 priority) — EXPIRED
- URL: https://patents.google.com/patent/US6500073B1/en
- **Method:** dual-camera stereo, sound trigger, 6 retroreflective dots, run-length-encoded dot detection, triangulated position+orientation at two instants → velocity + angular velocity; then numerical flight integration (drag/Magnus/gravity, atmospheric inputs) → carry/roll. This is the classic tour "launch monitor + trajectory model" package.

### US6758759B2 — "Launch monitor system and a method for use thereof" (2001) — EXPIRED 2022
- URL: https://patents.google.com/patent/US6758759B2/en
- **Method:** dual two-camera monitors — one imaging club pre-impact, one ball post-impact, in vertically separated planes; magnetic fixture calibrates clubhead geometric center; club trigger + sound trigger; markers on club (3) and ball (6); outputs club speed, attack angle, face angle + ball speed, launch, spin.
- **OpenFlight relevance:** expired, complete recipe for a stereo, marker-based club+ball measurement rig — the cheapest scientifically validated route to *measured* (not inferred) face angle and impact location.

### US7143639B2 / US8556267B2 / US8500568B2 — "Launch monitor" (portable four-camera family, priority Jun 7, 2004)
- URLs: https://patents.google.com/patent/US7143639B2/en (expired Jun 2024), https://patents.google.com/patent/US8556267B2/en (to ~2031), https://patents.google.com/patent/US8500568B2/en (to ~2030)
- Acushnet; Gobush, Bissonnette, Pelletier, Toupin, Gribben, Lentz.
- **Method:** portable (<50–100 lb, battery) four-camera unit; dual-laser/optical/ultrasonic triggering with an FPGA lookup table timing strobes vs detected swing speed (30–150 mph); filtered xenon strobes + dichroic filters discriminating fluorescent/retro markers on club vs ball; sequential-image kinematics (club speed, attack angle, face, loft, ball speed, launch, spin); automatic club/ball ID via "optical fingerprinting"; results in <1 s on integrated display.
- Relevance: parent expired; watch the later continuations' specific claims (mostly hardware-integration claims) until ~2030–31.

### US10668350B2 — "Launch monitor using three-dimensional imaging" (2017)
- URL: https://patents.google.com/patent/US10668350B2/en
- Acushnet; Hightower, Amarant, Furze, Daprato. Priority Dec 22, 2017; runs to ~2038.
- **Method:** stereographic or **light-field (plenoptic) camera** capture at 1,000–10,000+ fps, sub-10 µs exposures; direct per-frame x,y,z measurement (no size-based depth inference); digital color filtering to reject background/false light; velocities from frame-to-frame 3D displacement.
- Relevance: claims the modern "true 3D imaging" monitor; an open stereo design should study its independent claims (stereo golf imaging per se has heavy prior art, so claims are likely narrower than the abstract suggests).

---

## 5. Korean camera ecosystem: Creatz/Uneekor, Golfzon

### Uneekor (licenses + Creatz patents)
Uneekor's own list (https://uneekor.com/legal/patents) mixes: **Creatz Inc.** patents (US10247553, US9752875, US9605960, US9448067, US10587797, US10776929, US11191998, US12008770) and, for the portable EYE MINI line, the **Foresight/Wintriss** patents US7497780, US7292711, US7641565, US7324663 (licensed per the 2024 settlement).

- **US10247553B2 — "Virtual sport system using start sensor for accurate simulation of movement of a ball"** — Creatz Inc.; Yong Ho Suk; priority Sep 23, 2011; to ~2032. URL: https://patents.google.com/patent/US10247553B2/en. **Method:** sectioned start-sensor (optical/weight) over the hitting area detects actual ball starting position (not an assumed tee spot); strike inferred when a section's return disappears; simulation uses true start position + swing-plate tilt for accurate launch geometry.
- Uneekor also markets patented **"Dimple Optix"** — spin from imaging the actual dimple pattern of any ball (no stickers) via overhead IR cameras — plus the overhead-mount EYE XO engine. (Individual numbers among the Creatz set above.)

### Golfzon Co., Ltd.
- **US9242158B2 — "Virtual golf simulation apparatus and method"** — URL: https://patents.google.com/patent/US9242158B2/en. Woo/Jang/Zo; priority Feb 11, 2011; to ~2032. **Method:** latency-hiding two-stage processing: fast "first ball information" (speed, direction, vertical angle, ~100 ms) starts the sim trajectory immediately; slower "second ball information" (spin, from club-image or ball-surface analysis, ~200 ms) refines the in-flight trajectory. Stereo camera sensing unit.
- Related: US8585477 (simulation device + flight sensor), US9514379 (sensing device/method), and applications on stereo impact-position-on-clubface detection (US20230347209).
- **OpenFlight relevance:** the two-stage "start rendering, refine with late spin" trick materially improves perceived sim responsiveness — but it is claimed until ~2032.

---

## 6. Other players

- **SkyTrak / SkyGolf:** built by ex-AccuSport developers; photometric, GC2-adjacent architecture. No standout independent patent surfaced under the SkyTrak name in this pass; its freedom-to-operate historically leaned on the expiring Wintriss/Acushnet art. (AccuSport itself is defunct.)
- **AccuSport Vector / Zelocity PureLaunch:** early-2000s photometric units; the relevant art is the Acushnet/Gobush and Wintriss families above; both companies gone, patents (where any) expired or lapsed.
- **Full Swing:** markets "patented Dual-Tracking" — overhead ION camera at impact + IR line-scan light-curtain arrays in flight (Pro 2.0 "Tri-Tracking": ION3 + 4 IR/blue-LED cameras). The KIT's CW+FMCW radar is US 2020/0147470. The IR light-curtain approach dates to the 1990s (older Sports Vision/Full Swing-era patents now expired).
- **aboutGolf 3Trak (ex-Deltec):** proprietary high-speed machine-vision photography ("3D vector at impact"); no specific numbers confirmed this pass.
- **Ernest Sports:** hybrid — 2 IR cameras + 4 Doppler radar sensors (ES Tour Plus); patents not individually surfaced.
- **Garmin (Approach R10):** three-receiver Doppler radar measuring club speed, ball speed, launch angle/direction directly; spin and apex largely model-derived. No golf-specific blocking patent surfaced in this pass — notable that a major player ships a $600 radar unit measuring only the "safe," long-public-domain primitives (velocity + angles) and modeling the rest.
- **Sports Sensors Swing Speed Radar:** founder Albert Dilz (ex-defense), company started 1998 on his Glove Radar patent; simple CW Doppler peak-speed measurement. Foundational-era, expired.

---

## 7. Synthesis for OpenFlight (freedom-to-operate map)

**Public domain now (expired):**
- Single-camera photometric monitor with per-pixel 3D calibration, ball-diameter depth, and **markerless dimple-correlation spin** — Wintriss **US7292711 / US7324663** (expired Apr/Aug 2025). The best starting blueprint.
- Stereo two-camera + retroreflective-dot club AND ball measurement incl. face angle, attack angle, impact location — Acushnet **US5501463, US6500073, US6758759, US7143639** (all expired).
- Radar target-deviation UX (tap target in camera image) — TrackMan US9857459 expired; siblings expire 2026–27.
- Basic CW Doppler speed measurement — ancient art.

**Danger zones (in force):**
- Radar spin via harmonic sidebands: TrackMan **US8845442 (to ~2029)**, US10393870 (to Dec 2026). Family expires soon; EP already litigated and time-limited.
- Radar spin via phase-demod dielectric-lens pulses: FlightScope **US9868044 (to ~2034)**.
- Direct radar spin-axis via perpendicular receiver pairs: FlightScope **US10775492 (to ~2035)**.
- Radar+camera fusion tracking: FlightScope **US10338209 (to ~2037)**; TrackMan OERT family (2030s–40s); TrackMan tracer-overlay US10315093 (to 2030).
- Integrated ball-find/placement-guide/trigger workflow: Foresight/Wintriss **US7497780/US7641565 (to ~2027)** — note Foresight enforced portable-monitor patents against Uneekor as recently as 2024.
- Multi-bay range attribution by back-extrapolation: TrackMan US11086005 (to ~2036).
- Sim latency-hiding two-stage refinement: Golfzon US9242158 (to ~2032); Creatz start-position sensing US10247553 (to ~2032).
- True-3D/light-field capture claims: Acushnet US10668350 (to ~2038); Acushnet portable-integration continuations US8500568/US8556267 (to ~2030–31).

**Strategic takeaways:** (1) A camera-first OpenFlight design has a wide-open expired-art foundation (Wintriss + Gobush) covering everything through markerless spin and measured club/face data. (2) Radar spin measurement is the most patent-encumbered corner until ~2029 (TrackMan) / ~2035 (FlightScope); pure speed/launch-angle radar (Garmin-style) is safe. (3) Radar+camera fusion is the most actively and recently patented area — the two giants litigated each other in both directions. (4) Watch assignee aliases: Foresight = WAWGD/Wawgd Newco (holds Wintriss portfolio); Uneekor's list mixes owned (Creatz) and licensed (Foresight) patents; TrackMan = ex-Interactive Sports Games.
