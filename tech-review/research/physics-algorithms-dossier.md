# Launch Monitor Physics & Algorithms — Research Dossier

Prepared for the OpenFlight open-source launch monitor project. Coordinate convention used throughout (TrackMan-style, right-handed golfer): x = toward target along target line, y = up, z = right of target. Angles positive right/up unless noted.

---

## 1. Standard Parameter Definitions (TrackMan conventions — the de facto industry standard)

Exact wording from TrackMan's parameter documentation ([TrackMan: 40+ parameters explained](https://www.trackman.com/blog/golf/40-trackman-parameters), [club data definitions](https://www.trackman.com/blog/golf/club-data-definitions)). The critical subtlety is *when* each quantity is defined: club-delivery numbers at **time of maximum compression**; ball numbers **immediately after separation from the face**.

### Club delivery (at max compression unless noted)
| Parameter | Definition | Notes |
|---|---|---|
| **Club speed** | Linear speed of the club head's *geometric center* just **prior to first contact** | Not the impact-point speed; toe travels faster than heel |
| **Attack angle** (AoA) | Up/down movement of geometric center at max compression | + = hitting up. Driver PGA Tour avg ≈ −1.3°, LPGA ≈ +3° up |
| **Club path** | In-to-out (+) or out-to-in (−) horizontal direction of geometric center at max compression | Measured relative to target line |
| **Face angle** | Horizontal direction the face points at the *center-point of contact* at max compression | + = open (right) |
| **Face to path** | Face angle − club path | Sign controls curvature direction |
| **Dynamic loft** | Vertical angle of the face at the contact point at max compression | Differs from static loft via shaft lean, shaft bend, face roll, impact height |
| **Spin loft** | 3-D angle between club head *movement direction* (path + AoA) and *face orientation* (face angle + dynamic loft) | Often approximated as dynamic loft − attack angle; degrades as face-to-path grows |
| **Swing plane** | Vertical angle between the plane traced by the geometric center's motion and the horizon | |
| **Swing direction** | Angle between the base of that swing plane and the target line | Club path = f(swing direction, swing plane, attack angle, low point) |
| **Low point** | Distance from geometric center to the lowest point of the swing arc at max compression | + = low point still ahead (ball-first contact for irons) |
| **Impact height / impact offset** | Vertical / horizontal strike location relative to face center | Drives gear effect (§3) |
| **Dynamic lie** | Shaft angle vs. horizontal at impact | |

### Ball launch (immediately after separation)
| Parameter | Definition |
|---|---|
| **Ball speed** | Speed of the ball's CG immediately after separation |
| **Smash factor** | Ball speed / club speed |
| **Launch angle** | Vertical takeoff angle vs. horizon |
| **Launch direction** | Horizontal takeoff angle vs. target line |
| **Spin rate** | Rotation rate about the spin axis at separation (rpm) |
| **Spin axis** | Angle of the rotation axis **relative to the horizon** (− = tilted left → draw). A golf ball has a single rotation vector; "backspin" and "sidespin" are components, not separate spins ([Mitchell Golf](https://www.mitchellgolf.com/tilt-axis-spin-vs-sidespin/)) |
| **Curve / Side / Carry / Total / Apex / Landing angle** | Trajectory descriptors; carry is measured to the point at launch elevation |

Component conversion used by simulators ([GolfWRX conversion thread](https://forums.golfwrx.com/topic/1742438-conversion-between-spin-axis-and-side-spin-rpm/)):

```
sidespin = S_total · sin(θ_axis)       backspin = S_total · cos(θ_axis)
θ_axis  = atan2(sidespin, backspin)
```

Rule of thumb (Tuxen/TrackMan): 1° of spin-axis tilt ⇒ ≈ 0.7% side-curve (0.7 yd per 100 yd of carry) ([perfectgolfswingreview ball flight laws](https://www.perfectgolfswingreview.net/ballflight.htm)).

---

## 2. The D-Plane Model

Origin: Theodore Jorgensen, *The Physics of Golf* (2nd ed., 1999) — he named the "D" (descriptive) plane of the collision. The model: two 3-D unit vectors at impact,

- **û_N** — face normal (built from face angle φ_f and dynamic loft λ_d),
- **û_P** — club-head velocity direction (built from club path φ_p and attack angle α),

span a wedge-shaped plane (the D-plane). For a **center strike**:

1. **Launch direction** lies *in* the D-plane, between û_N and û_P, much closer to the face normal.
2. **Spin axis is normal to the D-plane**: ω̂ ∝ û_P × û_N. Hence the ball curves *away from the path, around the face* — the "new ball flight laws" ([GolfWRX: Understanding the D-Plane](https://www.golfwrx.com/29138/the-d-plane/), [DIY Golfer D-plane](https://www.thediygolfer.com/blog/d-plane-golf)).

### The face/path launch-direction weighting
Empirically (TrackMan robot + player data):

```
Launch direction ≈ 0.85·(face angle) + 0.15·(club path)     [driver ≈ 0.87/0.13]
                 ≈ 0.75·(face angle) + 0.25·(club path)     [short irons/wedges]
```

The weight is **loft- and friction-dependent**: more loft ⇒ more oblique impact ⇒ larger tangential (friction-driven) momentum transfer along the path direction ⇒ path gains influence. Sources: [Fulcria](https://fulcria.com/blog/club-path-face-angle-ball-flight/), [perfectgolfswingreview](https://www.perfectgolfswingreview.net/ballflight.htm), and peer-reviewed treatments: *The Influence of Face Angle and Club Path on the Resultant Launch Angle of a Golf Ball* ([ResearchGate](https://www.researchgate.net/publication/323373897_The_Influence_of_Face_Angle_and_Club_Path_on_the_Resultant_Launch_Angle_of_a_Golf_Ball)) and *The Role of Friction and Tangential Compliance on the Resultant Launch Angle of a Golf Ball* (MDPI Proceedings 49(1):27, [doi:10.3390/proceedings2020049027](https://doi.org/10.3390/proceedings2020049027)) — the latter models the oblique impact with normal COR plus friction/tangential compliance (Maw–Barber–Fawcett-style) and reproduces the ~75–85% face dominance, showing the split follows directly from the ratio of normal to tangential impulse.

A clean analytic version (Tutelman, "3-Dimensional Launch Conditions from Impact Conditions", [tutelman.com/golf/ballflight/3dlaunch.php](https://www.tutelman.com/golf/ballflight/3dlaunch.php)). Define total obliqueness Φ from face-to-path angle A and dynamic loft L:

```
cos Φ = cos A · cos L
f(Φ)  = 0.96 − 0.0071·Φ          (Φ in degrees; empirical launch fraction)

Departure angles (relative to club path):
  DA_vert = L · f(Φ)               DA_horiz = A · f(Φ)
Launch (relative to target):
  LA_vert = DA_vert + AoA          LA_horiz = DA_horiz + path
```

Note f(Φ) ≈ 0.85 at Φ ≈ 15° (driver) and ≈ 0.75 at Φ ≈ 30° (short iron) — reproducing the 85/15 and 75/25 rules from one friction-calibrated function.

### Spin-axis tilt from face-to-path
Tilt of the spin axis for a center hit is approximately

```
tan(θ_axis) ≈ tan(face-to-path) / tan(spin loft)     ≈ (F2P)/(spin loft) for small angles
```

so the same 1° of face-to-path tilts the axis ≈ **4°** with a driver but only ≈ **2°** with a mid-iron (lower spin loft ⇒ bigger tilt per degree) ([perfectgolfswingreview](https://www.perfectgolfswingreview.net/ballflight.htm)). Tuxen's shot-shaping design rule for a shot that curves back to the target line: `spin axis ≈ −2.5 × horizontal launch angle`.

### Vertical D-plane
Identical geometry in the vertical plane: launch angle sits ~75–85% toward dynamic loft from attack angle, and **spin loft** sets spin magnitude. For a down-and-in strike the true path at impact points outward by ≈ AoA·tan(swing-plane complement); e.g., 5° down on a 60° plane ⇒ path ≈ 2.9° in-to-out even with square swing direction — why irons need swing direction left of target to zero the path.

---

## 3. Impact Mechanics

### 3.1 Normal (ball-speed) model — oblique elastic collision
Standard two-body collision along the face normal with effective loft (Cochran & Stobbs 1968 *Search for the Perfect Swing*, [archive.org](https://archive.org/details/searchforperfect0000coch); Penner's review *The physics of golf*, Rep. Prog. Phys. 66 (2003) 131–171, [IOPscience](https://iopscience.iop.org/article/10.1088/0034-4885/66/2/202)):

```
v_ball = v_club · (1 + e) / (1 + m/M) · cos Φ · (1 − 0.14·miss_inches)
```

- e = COR ≈ 0.83 (USGA limit region for drivers; falls with loft and impact speed)
- m = 45.93 g (ball), M ≈ 200 g (driver head) ⇒ (1+e)/(1+m/M) ≈ 1.49
- cos Φ = obliqueness loss; last factor = empirical off-center loss (Tutelman, [smashfactor.php](https://www.tutelman.com/golf/ballflight/smashfactor.php))

Smash factor vs. loft (same source): 0° → 1.488, 10° → 1.465, 20° → 1.398, 30° → 1.288. Theoretical ceiling 2.0 (e=1, M→∞, loft 0). Practical driver max ≈ 1.47–1.50; a wedge at 1.0–1.1 is *normal physics*. This table doubles as a launch-monitor sanity check: measured smash above the loft-appropriate ceiling ⇒ measurement error (common with radar misreading club speed).

### 3.2 Spin generation (center strike)
Friction during the oblique compression drives tangential surface velocity v_club·sin Φ into rotation. Rigid-body sliding→rolling gives ω ≈ v_t/(r·(1+2/5)) style caps, but real impacts show **tangential compliance** (face–cover shear spring): the contact patch sticks, stretches, and can overshoot (super-spin) — analyzed for golf in the MDPI friction/compliance paper above and generally by Cross (oblique bounce with grip, [physics.usyd.edu.au](https://www.physics.usyd.edu.au/~cross/GOLF/GOLF.htm); Cross & Nathan ball–bat analysis, [arXiv:1610.03464](https://arxiv.org/pdf/1610.03464)). Practical engineering fit (Tutelman 3dlaunch, calibrated to TrackMan data):

```
S_total [rpm] ≈ 160 · v_club[mph] · sin Φ        (Φ = spin loft)
d = tan A / tan L ;  S_back = S/√(1+d²) ;  S_side = d·S_back
```

Cross-checks: ~200–300 rpm per degree of spin loft for a driver ([TrackMan spin loft](https://www.trackman.com/blog/golf/spin-loft)); the "loft × 200" rule matches PGA Tour iron spin averages. TrackMan lists spin drivers as club speed × spin loft × friction ([TrackMan spin rate](https://www.trackman.com/blog/golf/spin-rate)); friction saturates ("spin loft cliff" ≈ 45–50°, wet/grassy contact reduces spin at fixed spin loft).

### 3.3 Gear effect (off-center strike)
Off-center impact at distance x from the CG-line torques the head about its CG; the rotating face "gears" the ball the opposite way. Tutelman's model ([gearEffect1.php](https://www.tutelman.com/golf/ballflight/gearEffect1.php)):

```
ω_head = x·m·v_ball / I_h                     (angular impulse / MOI)
s [rpm] = 58,830 · v_ball[mph] · C[in] · x[in] / I_h[g·cm²]
        ≈ 16.4 · v_ball[mph] · x[in]·100      (simplified; modern drivers, ±2.5%)
```

C = CG depth behind face (32–47 mm measured on OEM drivers), I_h = 4000–5800 g·cm² about the vertical axis; I/C nearly constant across modern drivers (R²=0.92), which is why the "16.4·v·x" shortcut works. Toe hit ⇒ head opens ⇒ **hook** gear-spin (and starts right off the bulge); heel ⇒ slice spin. Vertical gear effect (high face = less backspin, low face = more) uses the same equation with roll radius and vertical CG ([Titleist gear effect](https://www.titleist.com/learning-lab/performance/golf-gear-effect), [GOLFTEC bulge & roll](https://www.golftec.com/blog-posts/golf-science-the-influence-of-bulge-and-roll-and-gear-effect-on-ball-flight)).

**Bulge compensation**: face bulge radius (10–13", typ. 12") aims the toe-miss launch right so gear-effect hook curves it back. Worked example (Tutelman): 1" toe miss, 150 mph ball: bulge slice-spin +1354 rpm vs gear hook −2192 rpm ⇒ net 838 rpm hook, 10 yd left — vs 61 yd offline for a flat face. Spin-axis sensitivity: a strike 1 dimple (0.14") off-center tilts the axis ~6° on a driver, ~2° on a 6-iron. Irons have shallow CG ⇒ weak gear effect (hence no bulge). Penner analyzed convex-face optimization explicitly (*The physics of golf: the convex face of a driver*, raypenner.com/golf-convex.pdf) and optimal dynamic loft vs. club speed: 16.5°/13.1°/10.7° at 35/45/55 m/s ([Penner, optimum loft](https://www.researchgate.net/publication/243492348_The_physics_of_golf_The_optimum_loft_of_a_driver)).

Modeling review: *A review of dynamic models and measurements in golf*, Sports Engineering 25 (2022) ([Springer](https://link.springer.com/article/10.1007/s12283-022-00387-0)).

---

## 4. The Inverse Problems Launch Monitors Solve

### 4.1 Radar: face angle is *derived*, not measured
Doppler radar measures ball launch (speed, direction, spin) and club-head kinematics (speed, path, AoA), but cannot see face orientation. **Face angle and dynamic loft are computed by inverting the D-plane/impact model**: given launch direction, path, and the empirical weighting, solve `face = (launch − w_p·path)/w_f` (and similarly dynamic loft from launch angle + AoA). TrackMan confirms these are "derived numbers from direct measurements and a collision model," validated by robot testing ([Brian Manzella forum citing TrackMan](https://forum.brianmanzellagolf.com/threads/how-does-trackman-flightscope-measure-the-club-face-angle.16591/), [PARennial](https://parennialgolf.com/blog/face-angle-explained)). Consequence for OpenFlight: any consistent bias in launch-direction measurement propagates ~1.15× into reported face angle.

### 4.2 Camera systems: club data needs fiducials
Photometric units directly measure the *ball* (stereo dimple imaging) but cannot resolve the unmarked clubface; the GCQuad requires **four reflective fiducial dots** on the face, on the vertical centerline and equidistant from the horizontal centerline, to reconstruct face angle, loft/lie, path, AoA, impact location, and closure rate stereoscopically ([Foresight marker guide](https://help.foresightsports.com/hc/en-us/articles/4408197030035-How-to-Apply-and-Maintain-Club-Markers-for-Foresight-Sports-Devices), [What we measure](https://foresightsports.eu/what-we-measure/)). Conversely, camera units *infer downrange flight*: they measure launch over the first ~30 cm and integrate a trajectory model for carry — the mirror image of radar.

### 4.3 Ball flight model (both architectures need it)
Equations of motion with drag, Magnus lift, gravity:

```
m dv/dt = −½ρ A C_D |v_a| v_a  +  ½ρ A C_L |v_a|² (ω̂ × v̂_a)  +  m g
A = πR², R = 21.34 mm, m = 45.93 g;  v_a = v − v_wind
Spin ratio S = Rω/|v_a|;  Re = 2R|v_a|/ν
```

Integrate (RK4 is ample) until y returns to launch elevation → carry; lateral offset → side. ([Three-dimensional golf ball flight](https://www.researchgate.net/publication/318276568_THREE_DIMENSIONAL_GOLF_BALL_FLIGHT), [IJIMT trajectory paper](https://www.ijimt.org/papers/419-D0260.pdf)).

**Aerodynamic data:**
- **Bearman & Harvey (Aeronautical Quarterly 27, 1976)** — canonical wind-tunnel dataset: dimples drop critical Re to ~5×10⁴; post-critical C_D ≈ 0.25 nearly Re-independent; C_L rises with spin ratio (≈0.08→0.25 over S ≈ 0.02→0.3); hex dimples beat round ([Cambridge Core](https://www.cambridge.org/core/journals/aeronautical-quarterly/article/abs/golf-ball-aerodynamics/67FE0903DB1CC12001F1ED1B1261C4B9), [COMSOL summary](https://www.comsol.com/blogs/why-do-golf-balls-have-dimples)).
- **Smits & Smith (Science and Golf II, 1994)** — parameterized model widely used in simulators: C_D = C_D1 + C_D2·S + C_D3·sin(π(Re−A1)/A2) with C_D1=0.24, C_D2=0.18, C_D3=0.06, C_L1=0.54·(spin term), R1=2×10⁻⁵, A1=90,000, A2=200,000; plus **spin decay** dω/dt with time constant ≈ 24 s at 100 mph (~4%/s early) ([ResearchGate](https://www.researchgate.net/publication/284037213_A_new_aerodynamic_model_of_a_golf_ball_in_flight), [Tutelman spin decay](https://www.tutelman.com/golf/ballflight/spinDecay.php)).
- **USGA Indoor Test Range / Quintavalla (2002, Science and Golf IV)** — trajectory-derived **six-term Cd/Cl models** (polynomials in Re and S) fitted from ITR ball-flight photography; basis of USGA ODS conformance testing ([USGA ITR conditions PDF](https://www.usga.org/content/dam/usga/images/equipment-standards/ITR-test-conditions-2028-ODS.pdf), method patent [US6186002B1](https://patents.google.com/patent/US6186002B1/en) — determining Cd/Cl from measured trajectories, a useful template for calibrating OpenFlight's model).
- Modern references: MDPI *Aerodynamics of Golf Balls in Still Air* ([mdpi.com](https://www.mdpi.com/2504-3900/2/6/238)); Stanford LES, Sports Engineering 2019 ([PDF](http://aero-comlab.stanford.edu/Papers/golf_ball_sports_engineering_2019.pdf)).

**Curvature from spin axis:** tilting ω by θ rotates the Magnus force off vertical: lateral accel = (F_M/m)·sinθ. Hence the 0.7%-per-degree side-curve rule and `sidespin = S sinθ`.

### 4.4 Indoor→outdoor extrapolation
Short-flight systems fit measured launch + a ball model; radar indoors does the same with partial trajectories — the main source of inter-device carry disagreement ([Cero Golf](https://www.cerogolf.com/post/how-launch-monitors-compensate-for-indoor-ball-flight)).

---

## 5. Spin Measurement Algorithms

### 5.1 Radar spectral method (TrackMan-style)
A spinning ball is not a point target: dimples, logo/paint, core asymmetry, and the cover's **dielectric-lens effect** periodically modulate the RCS/phase at the spin period. The Doppler return is phase/amplitude modulated at f_spin, producing **sidebands spaced at exact integer multiples of the spin frequency, symmetric about the main Doppler line**:

```
f_sidebands = f_Doppler ± n·f_spin,  n = 1,2,3,…   ⇒  spin[rpm] = 60·Δf_sideband
```

Algorithm: STFT of the Doppler channel → detect the translational Doppler ridge → measure harmonic comb spacing (cepstrum/harmonic-product-spectrum works well) → spin rate. ([US2014/0191896](https://patents.google.com/patent/US20140191896), [US10393870](https://patents.google.com/patent/US10393870B2/en)); micro-Doppler background: [Micro-Doppler modulation of spinning projectile on CW radar](https://www.researchgate.net/publication/317119893_A_Micro-Doppler_Modulation_of_Spin_Projectile_on_CW_Radar). Practical gotchas: sideband SNR depends on ball asymmetry (clean range balls read weakly — hence "marked ball" modes), and only spin *rate* comes from the comb. **Spin axis** must come separately — trajectory curvature inversion ([US10850179](https://patents.google.com/patent/US10850179B2/en)): fit θ_axis so the Magnus model reproduces measured lateral/vertical acceleration.

### 5.2 Camera dimple-tracking (Foresight-style)
Capture N high-speed frames. Per frame: segment the ball, reconstruct 3-D pose; then estimate the **rotation R between frames from the dimple pattern via spherical correlation / feature registration on S²** — maximize correlation of back-projected surface texture over SO(3); the argmax gives axis (eigenvector of R with eigenvalue 1) and per-frame angle θ = arccos((tr R−1)/2), so ω = θ/Δt. Accuracy 1–3% of true spin, independent of ball speed ([Foresight](https://foresightsports.eu/foresight-life/different-types-of-launch-monitor/), image-processing patent [US9171211](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9171211)). Failure mode: dimple aliasing at high spin/low frame rate — resolve with trajectory-consistency prior or multi-hypothesis over n·2π ambiguities. Academic analogues: [SpinDOE](https://arxiv.org/pdf/2303.03879), ["Measuring Ball Spin by Image Registration"](https://www.researchgate.net/publication/2881136_Measuring_Ball_Spin_by_Image_Registration).

### 5.3 Marked-ball methods
Retro-reflective or printed markers give unambiguous correspondences between two flash exposures — the budget path (SkyTrak-class and DIY GSA-style systems, [GSA Golf simulator theory](https://www.golf-simulators.com/GolfSimulatorTheory.html); reflective-marking patent [US9199153](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9199153)). With ≥3 non-collinear marks visible in both frames, R follows in closed form from Kabsch/Horn.

---

## 6. Estimation & Filtering Math

### 6.1 Radar 3-D tracking: Doppler + phase interferometry
TrackMan-class units are MFCW Doppler radars with an antenna array. Range rate from Doppler; **angles from phase differences between receive antennas**: wavefront delay τ = (d·û)/c between antennas with baseline d, seen as phase shift Δφ = 2π f τ (mod 2π), so direction cosine u = λΔφ/(2πd). Three-plus antennas spanning a plane perpendicular to boresight give azimuth and elevation; **2π ambiguities resolved by >3 antennas cleverly spaced in a 2-D grid** (TrackMan US9,958,527; [US12186643](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12186643)). Multi-frequency CW phase differences across transmit tones give absolute range. Result: (r, az, el, ṙ) per epoch → 3-D track. Background: [WSU thesis on Doppler-radar ball tracking](https://baseball.physics.illinois.edu/trackman/JasonMartinThesisWSU.pdf).

### 6.2 Kalman/EKF trajectory estimation
State x = (p, v, ω or S,θ_axis); process model = flight ODE (nonlinear ⇒ EKF/UKF). Measurement models: radar h(x) = (range, az, el, ṙ) with ṙ = v·p̂; camera h(x) = pixel projections. Launch parameters are then a **smoothing/back-extrapolation** problem: fit the whole observed arc and evaluate the state at face separation. Commercial hybrids fuse camera + radar with an EKF weighted by per-measurement confidence and a 6-DOF flight model. Spin-axis-from-curvature drops naturally out of including θ_axis in the EKF state.

### 6.3 Stereo triangulation (camera systems)
Calibrated pair (K₁,K₂; [R|t]). For matched pixels: back-project rays, solve least-squares midpoint or DLT; refine by reprojection error. Depth error σ_Z = Z²σ_px/(f·B) — short baselines are why photometric units only measure the first ~30 cm and use ball-diameter-in-pixels as an extra range cue. Ball center from the projected conic rather than blob centroid avoids a systematic bias up to R·Z/f.

---

## 7. Academic Literature Map

**Books / foundational:** Cochran & Stobbs, *Search for the Perfect Swing* (1968); Jorgensen, *The Physics of Golf* (2nd ed. 1999); Penner, "The physics of golf," *Rep. Prog. Phys.* 66:131 (2003) + companions (optimum driver loft, convex face, run of the ball).

**Aerodynamics:** Bearman & Harvey (1976); Smits & Smith (Science and Golf II, 1994); Quintavalla (Science and Golf IV, 2002); Stanford LES (Sports Engineering 2019); MDPI still-air survey.

**Impact / launch direction:** MDPI Proceedings 49:27 (2020); face/path influence study (ResearchGate); Cross oblique-impact experiments; Cross & Nathan (arXiv:1610.03464); dynamic-models review, Sports Engineering 25 (2022).

**Launch-monitor validation:**
- **Leach, Forrester, Mears & Roberts (2017)**, *Measurement* 112:125–136 — TrackMan Pro IIIe vs GC2+HMT vs 4×5400 fps camera criterion, 240 shots. Verdict: **ball parameters trustworthy on both; club parameters need caution** ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0263224117305079)).
- TrackMan 4 reliability, *J. Sports Sci.* (2024): ICC 0.99 club speed, 0.97–0.99 ball speed, but **spin rate ICC 0.02–0.60 indoors** — spin is the fragile channel ([T&F](https://www.tandfonline.com/doi/full/10.1080/02640414.2024.2314864)).
- Robot testing (Golf Laboratories): GCQuad spin σ ≈ 82 rpm vs TrackMan ≈ 175 rpm on center strikes.
- *Science and Golf* proceedings (I–VI) — richest single venue.

### Key takeaways for OpenFlight
1. Implement the D-plane forward model (Tutelman's Φ-based equations are a complete, calibrated, closed-form set) — it serves both simulation and the **inverse face-angle solve** that radar-style sensing requires.
2. Ball flight: Smits–Smith coefficients + spin decay as default; structure code to swap in Quintavalla-style six-term fits; calibrate via the US6186002 trajectory-fitting approach.
3. Spin: camera dimple registration on SO(3) if optical; harmonic-comb spectral estimation if Doppler; either way put spin axis in the trajectory EKF state so curvature evidence refines it.
4. Report parameters with TrackMan's exact timing semantics (max compression vs. post-separation) and flag derived vs. measured quantities — validation literature shows club-side numbers are where all systems are weakest.
