# Screw Theory Applied to Launch Monitors: A Research Outline

**Purpose.** A research-grade map of how screw-axis theory (twists, instantaneous
screw axes, Plücker line geometry) can improve launch monitor measurement —
radar-based and camera-based — with emphasis on **club data accuracy** and, in
particular, **determining clubface orientation without inverting an impact
model**. Technical benefits only. This outline seeds future sections of the
tech-review document and future experiments; each numbered idea is written so it
can be picked up independently.

**Companion material.** Appendix E of `tech-review/` (screw-theoretic clubhead
kinematics) establishes notation and the core result used throughout: a Doppler
detection is the reciprocal product of the sight line with the club's twist,
hence *linear* in the twist coordinates. The directness hierarchy (tech-review
Table 2.3) frames the goal: move parameters up the hierarchy, from
estimated → derived → measured.

---

## 1. Problem framing: why club data is the frontier

1.1. Ball data is solved to first order. Every architecture measures ball
speed/launch angles well; camera systems measure spin directly; validation
literature (Leach 2017; TrackMan 4 reliability 2024) confirms ball parameters
agree across devices while club parameters diverge.

1.2. The three structural deficiencies of current club data:
- **(D1) Reference-point ambiguity** — "club speed" depends on which point of
  the head is tracked; point-trackers follow glints, which wander. This is a
  *definitional* variance, not sensor noise.
- **(D2) Face orientation is inferred, not measured** on all radar-only devices
  (D-plane inversion of ball launch + path) and on camera devices only measured
  with fiducial stickers or overhead geometry. The inversion inherits
  launch-direction bias amplified ~1.15×, and is blind to gear effect.
- **(D3) No uncertainty reporting** — all vendors report naked numbers; the
  measured/derived boundary is invisible to the user.

1.3. Thesis: a screw-theoretic estimation layer directly addresses D1 (twist =
full velocity field → any declared reference point) and D3 (linear estimator →
true covariances), and *enables* several routes to D2 (Sections 5–6) by
providing the propagation machinery that lets a face-orientation *anchor*
measured at any time be carried to the impact instant.

---

## 2. The unifying mathematical object: one continuous-time twist trajectory

2.1. **Representation.** Model the club's motion over the final ~150 ms as a
continuous-time trajectory on SE(3): pose T(t), body twist ξ(t) = (ω, v). All
sensors — radar detections, camera frames, event streams, on-club IMU samples —
contribute residuals against this *single* trajectory at their own native
timestamps. No resampling, no per-sensor pipelines that meet only at the end.

2.2. **Parameterization options**, in order of implementation maturity:
- (a) Discrete EKF/RTS on SE(3) at the fastest sensor rate (tech-review App. E).
- (b) Cumulative B-splines on SE(3) (continuous-time SLAM machinery; Sommer et
  al., Lovegrove et al.) — the natural choice once sensors are asynchronous:
  radar rows at ~300 Hz, camera at 60 fps, events at µs, IMU at kHz.
- (c) Dual-quaternion interpolation for pose composition where numerical
  elegance matters.

2.3. **Why this is the right ledger for the face problem.** Face orientation at
impact = (face orientation at any anchor time t₀) ∘ (integrated rotation from t₀
to impact). The twist trajectory *is* that integral, with covariance. Every
face-measurement idea in Section 5 reduces to "produce an anchor"; screw theory
turns one anchor plus continuously measured ω into face angle at impact. Anchor
error and propagation error add in quadrature:
σ²_face(t_impact) ≈ σ²_anchor + ∫ σ²_ω dt — so the design rule is *anchor as
late as geometry allows, measure ω as well as possible throughout*.

2.4. **Physically structured priors** (all screw-native):
- Low pitch: downswing ≈ pure rotation (pitch h = ω·v/|ω|² small).
- Hub proximity: ISA passes near the hands (Vena et al. verified ≥71% of marker
  velocity is ISA-rotational).
- Smoothness of the ISA path (skilled-swing characteristic — usable as a prior
  *and*, inverted, as a skill metric).
- Data-driven: a low-dimensional swing-manifold prior learned from logged twist
  trajectories (thousands of swings) to regularize the weakly observed
  components. Keep priors weak enough to be data-overrulable; validate with the
  pendulum rig where the true twist is analytic.

---

## 3. Radar-side program

3.1. **Twist-native estimation (baseline).** Per-detection Doppler rows →
weighted linear LS per frame → SE(3) smoothing. Fully specified in tech-review
Appendix E. Benefits: D1 solved (declared reference point), closure rate and ISA
swing plane as free projections, honest covariances. Hardware: IWR6843-class
FMCW with custom chirps (~300 Hz frames, 3.75 cm range cells).

3.2. **Rotational ISAR imaging of the clubhead.** The head rotates ~15–25°
through the observable window; rotation is exactly what inverse synthetic
aperture radar needs. Cross-range resolution δ = λ/(2Δθ): at 60 GHz with 20° of
observed rotation, δ ≈ 7 mm — clubhead-feature scale. The blocker for ISAR is
always motion compensation; **the twist trajectory is the motion compensation**,
computed by the Section 3.1 estimator. Pipeline: estimate twist → re-focus the
coherent detection history into the rotating body frame → a sparse 2D/3D image
of persistent scatterers (hosel, toe, sole edges). Payoff: scattering-center
geometry identifies *where* on the head each Doppler row originated, breaking
the glint-migration error floor, and yields a crude head-frame model without any
CAD input. Research questions: coherence time of head returns at 60 GHz;
scatterer persistence across aspect; minimum SNR per chirp.

3.3. **Specular-flash timing as an orientation anchor.** A clubface is a large,
nearly flat conductor: its RCS has a strong specular lobe about the face normal.
As the face closes through the downswing, the normal sweeps through space; at
the instant it crosses the radar's direction, the return spikes ("glint flash").
That timestamp is a *direct orientation fix*: face normal ∥ line of sight at
t_flash, to within the lobe width. One radar node gives one anchor; the twist
trajectory propagates it to impact (Section 2.3). Multiple nodes (3.4) give
multiple anchors, over-determining the propagation. Modeling needs: flat-plate
RCS lobe width at 24/60 GHz for real head geometries (bulge/roll curvature
broadens the lobe — curvature is knowable per club); discrimination of face
flash from crown/sole flashes (range gating + timing logic).

3.4. **Multistatic geometry as an observability instrument.** The per-frame
twist system's weak directions are set by sight-line diversity. Cheap 24/60 GHz
nodes are ~$20–50; placing a second node down-target or overhead is the highest
leverage accuracy purchase available. Method: optimal experiment design on the
measurement matrix — place node k to maximize the smallest singular value of the
stacked A over the swing window. This converts "where do I put the sensor?" from
folklore into arithmetic. Synchronization at the µs level via shared trigger
(the sound trigger already exists) or RF sync.

3.5. **Polarimetric normal estimation (exploratory).** Reflection from a flat
conducting plate transforms polarization in an orientation-dependent way.
Dual-pol TX/RX could constrain the face normal continuously, not only at flash
instants. Open questions: sensitivity at consumer SNR; separating face returns
from shaft (a thin cylinder — strongly polarizing, which is itself useful: the
shaft's polarization signature helps segment it out, and the shaft axis is one
of the two lines defining club presentation).

3.6. **Groove-scale effects (speculative, catalogued for completeness).** Iron
score-lines are sub-wavelength even at 60 GHz (0.5–1 mm spacing vs 5 mm λ) — no
Bragg regime. At 120+ GHz automotive bands this changes; note and park.

3.7. **Passive RF tags (the radar analog of fiducials).** A millimeter-scale
corner reflector or van-Atta patch at a known location on the head gives a
persistent, non-migrating scattering center — one perfect row in the twist
system per frame per tag; three non-collinear tags = full 6-DOF pose by
closed-form (Kabsch on Doppler-consistent positions), i.e., *radar-measured face
orientation* with sticker-level intrusiveness. Precedent: Titleist RCT balls
embed radar-visible markers; nobody has done the club. Design questions: tag RCS
vs head clutter; mounting that survives impact shock.

---

## 4. Camera-side program

4.1. **Lines, not points: Plücker-native club tracking.** A golf club is
geometrically a bundle of high-contrast *lines*: shaft axis, topline, leading
edge, groove set. Lines are the native objects of screw theory (Plücker
coordinates; the reciprocal product used for Doppler rows is the same algebra).
Line-based pose estimation is better conditioned than point-based for elongated
objects, and the shaft is visible in nearly every frame from nearly every angle.
Program: detect shaft + leading edge as line segments per frame; each line
correspondence contributes two constraints on T(t); fuse into the Section 2
trajectory. No stickers, works at modest frame rates because the trajectory
prior carries information between frames.

4.2. **Grooves as natural fiducials → direct face orientation.** The score
lines are a manufactured, regulation-controlled set of parallel coplanar lines
*on the face itself*. If a camera resolves even two grooves for even one frame,
the projective geometry of parallel lines (their vanishing point + spacing
foreshortening) yields the face plane's orientation directly — a markerless,
per-club-calibration-free face anchor. Geometry favors: overhead cameras
(Uneekor-style) for irons at address→impact; down-target cameras during release.
Combine with 2.3: one groove-resolved frame anywhere in the last 50 ms suffices,
propagated by the twist. Research: minimum resolution/illumination for groove
detection at swing speed (IR + short strobe); driver faces (faint or no grooves
— fall back to topline + face outline model fit).

4.3. **Deflectometry: the face as a mirror.** Polished/semi-specular faces
reflect structured illumination; observing a *known pattern's reflection* in the
face measures the surface normal field directly — this is deflectometry,
standard in industrial specular-surface metrology, and it is the most direct
face-orientation measurement physically possible: no markers, no model, the
normal itself is the observable. Implementation sketch: an IR LED constellation
(or the existing strobe array patterned) + high-speed camera; the constellation's
reflected image position in the face maps to normal orientation. Works best
face-on (down-target camera) in the last frames before impact — exactly where an
anchor is worth most (σ²_anchor delivered at minimal propagation time).
Research: which face finishes are specular enough at 850 nm (milled putters ≫
irons > matte drivers); grooves as deflectometric disturbance vs. bonus
structure.

4.4. **Model-based silhouette tracking on SE(3).** With a per-club 3D model
(one-time photogrammetry scan of the user's club — a 2-minute phone procedure),
fit the model to per-frame silhouettes/edges with the twist-trajectory prior.
This is how markerless overhead systems work; the screw contribution is the
continuous-time prior, which lets *fewer, noisier* frames yield a stable pose —
i.e., commodity 200–500 fps sensors instead of 3000+ fps, because information is
integrated along the trajectory instead of demanded per frame.

4.5. **Event cameras (neuromorphic) — the sophisticated option.** DVS sensors
report per-pixel brightness changes with µs timestamps and no motion blur; a
swinging club is close to their ideal stimulus. Event-based motion estimation is
naturally continuous-time and pairs with the SE(3) spline ledger; edge events
from shaft/topline feed line-based twist constraints (4.1) at effectively 10 kHz
equivalent rates for tens of dollars of sensor (embedded DVS pricing is
collapsing). Research program: event-line association at clubhead speeds;
event+strobe hybrid (events for motion, one strobed frame for the groove/
deflectometric anchor).

4.6. **Impact-adjacent acoustics (auxiliary, already-owned hardware).** Impact
location audibly changes the strike sound (players diagnose toe/heel by ear).
The sound trigger already digitizes this. A small classifier on the impact
transient (spectral centroid, ring-down of the face's modal response) gives a
coarse impact-location estimate — evidence to condition the gear-effect term
when no optical impact measurement exists. Strictly auxiliary; flag as
estimated.

---

## 5. Face orientation without impact-model inversion: the taxonomy

Ranked by directness of the face-normal observable; all combinable via the
anchor-and-propagate principle (2.3).

| # | Method | Observable | Modality | Anchor time | Maturity |
|---|--------|-----------|----------|-------------|----------|
| F1 | Fiducial stickers on face | marker constellation pose | camera | continuous | commercial (Foresight; expired Acushnet art) |
| F2 | Groove-line projective geometry (4.2) | face-plane orientation | camera | any groove-resolved frame | novel, near-term |
| F3 | Deflectometry (4.3) | surface normal directly | camera + structured IR | late downswing | novel, medium-term |
| F4 | Model-based silhouette fit (4.4) | full head pose | camera | continuous | commercial-adjacent (overhead); screw prior is the upgrade |
| F5 | Specular flash timing (3.3) | normal ∥ LOS at t_flash | radar | flash instants | novel, near-term |
| F6 | Passive RF tags (3.7) | 3-tag pose | radar | continuous | novel, medium-term |
| F7 | Rotational ISAR scatterer map (3.2) | head-frame geometry → pose | radar | continuous | novel, long-term |
| F8 | On-club IMU (6.1) | body-frame ω (+ orientation w/ calibration) | inertial | continuous | commercial in training aids; fusion is the upgrade |
| F9 | Polarimetric normal (3.5) | normal-dependent pol. transform | radar | continuous | exploratory |
| F10 | Well-posed inversion (fallback) | ball launch + *measured impact location* → face | model | impact | upgrade of status quo: with impact location known, gear effect is corrected and the inversion becomes well-conditioned; retain as cross-check |

Design principle: **the impact model (D-plane) should be demoted from primary
face source to consistency check.** When F2/F3/F5 supply a measured face angle,
predicting ball launch through the forward D-plane and comparing against the
measured ball launch becomes a per-shot self-test of the whole instrument — a
closed loop no commercial unit currently exposes.

---

## 6. Cross-modality and on-club sensing

6.1. **IMU-in-grip fusion.** A gyro measures the angular part of the body twist
directly at kHz rates — precisely the component radar observes worst. The
complementarity is exact in screw coordinates: radar rows constrain spatial
linear projections; the gyro constrains body ω; the spline ledger (2.1) fuses
both trivially. Grip-mounted avoids impact shock; shaft flex (grip-to-head
misalignment, several degrees dynamic) must be modeled — either via a calibrated
2-mode flex model or by treating grip and head as two twist-linked bodies with a
compliance prior. For a training-context product this is the cheapest route to
continuous ω truth.

6.2. **Ball-side niche: putting and roll state.** A rolling ball's ISA lies in
the ground contact; a skidding ball's passes through the CG. Skid→roll
transition = ISA migrating from center height to surface — so *true roll
percentage* is a direct screw observable from any sensor that resolves both v
and ω early in the putt (camera dimple tracking does). Novel measurand;
putter-fitting relevance; distinct from bounce/slide/roll *classification*
approaches.

6.3. **Swing-side extension.** The same ISA machinery applied to the hands/arms
(Vena's domain) with wearable or vision input shares the estimation stack;
club-ISA vs body-ISA relative geometry ("release" quantified as the ISA
separation dynamics) is an untapped coaching measurand family.

---

## 7. Error budgets and observability engineering

7.1. Publish per-parameter error budgets in the anchor+propagate form:
σ²(param at impact) = anchor term + propagation term + projection term. Make
every proposed method (F1–F10) enter the same budget so they compete on equal
footing.

7.2. Use the twist measurement matrix as a *design tool*: sensor placement,
chirp allocation, and frame-rate choices evaluated by their effect on the
smallest singular values over the swing window (3.4). Report designs with the
predicted, not just achieved, covariance.

7.3. Conditioning pitfalls to carry through all work (from App. E): never invert
per-frame weak directions; robust losses for glint/feature migration; rigidity
ends at first contact; priors must be pendulum-validated.

---

## 8. Ranked experimental program

| Rank | Experiment | Hardware delta | Answers |
|------|-----------|----------------|---------|
| E1 | Synthetic twist-estimation study (simulated scatterers on CAD head + recorded swing trajectories) | none | validates App. E pipeline; quantifies observability claims; tunes priors |
| E2 | OPS243-A velocity-distribution club analytics | none | D1 mitigation on current hardware; spread↔ω correlation |
| E3 | Pendulum rig with club | rig only | end-to-end bias test (analytic twist truth) |
| E4 | IWR6843 custom chirp bring-up + per-bin monopulse | firmware effort | the enabling dataset for everything radar-side |
| E5 | Specular-flash detection (3.3) on E4 data | none beyond E4 | is the face flash detectable/timeable at consumer SNR? |
| E6 | Groove-anchor feasibility: strobed GS camera, overhead, irons (4.2) | Pi GS cam + strobe (~$100) | minimum resolution/lighting for a groove-resolved frame |
| E7 | Twist-propagated face angle: fuse E5/E6 anchor with E4 twist; compare vs D-plane-inverted face on the same shots | none beyond above | the headline result: measured-vs-inferred face angle discrepancy distribution |
| E8 | Deflectometry bench test on club faces at 850 nm (4.3) | LED array + camera | which faces/finishes support direct normal measurement |
| E9 | ISAR focusing of E4 coherent data (3.2) | none | scatterer persistence; achievable cross-range resolution |
| E10 | Grip IMU fusion (6.1) | ~$30 IMU | ω truth for validating radar ω; shaft-flex magnitude data |
| E11 | Acoustic impact-location classifier (4.6) | none | auxiliary impact evidence from existing microphone |
| E12 | Putting ISA / roll-state measurement (6.2) | camera pointing down-line | novel measurand demo |

E1–E3 need no new hardware and de-risk everything else. E7 is the
proof-of-concept that would demonstrate, on one dataset, face angle measured two
independent ways plus the model-inverted value — the clearest possible evidence
of what the industry's inversion practice actually costs.

---

## 9. What screw theory contributes, stated precisely

- **Unification**: one motion object (the twist trajectory) that every sensor
  modality writes into and every reported parameter projects out of.
- **Linearity where it counts**: Doppler and line observables are linear/
  bilinear in twist coordinates → tractable estimators with honest covariance.
- **Reference-point invariance**: eliminates the largest definitional variance
  in club data (D1).
- **The anchor-and-propagate principle**: converts the face-orientation problem
  from "see the face at impact" (nearly impossible from behind) into "fix the
  face once, integrate ω" — which every method family in Section 5 plugs into.
- **New measurands**: closure rate from radar, ISA swing plane, ISA pitch and
  smoothness, hub path, gear-effect recoil, true roll percentage.
- **Design mathematics**: observability-driven sensor placement and chirp/frame
  budgeting instead of folklore.
- What it does **not** do: add information the sensors don't collect, or
  substitute for SNR, aperture, or resolution.
