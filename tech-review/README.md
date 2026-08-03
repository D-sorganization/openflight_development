# Launch Monitor Technology Review

A comprehensive LaTeX technology review of how commercial golf launch monitors
work — radar physics, camera photogrammetry, patent landscape, and the
club/ball parameter calculations — a vendor-neutral technical reference.

> **Contributing?** Read **[CONVENTIONS.md](CONVENTIONS.md)** first — it covers file
> layout, labels, citation keys, prose style, and the build. This document is
> designed to grow toward a textbook-scale reference edited by many hands.

- **[main.pdf](main.pdf)** — the compiled report (~65 pages)
- `main.tex` + `sections/` — LaTeX source (10 chapters + 5 appendices), one file per chapter
- `references.bib` — the bibliography database (80 entries, grouped by source category)
- `build.ps1` — local build; CI builds every PR via `.github/workflows/tech-review.yml`
- `research/` — the four raw research dossiers the report was synthesized from
  (radar systems, camera systems, patents, physics/algorithms), with source
  URLs for every claim
- `build.ps1` — compile script (MiKTeX pdflatex, 3 passes)

## Report contents

1. Introduction — sensing families, market convergence
2. Parameter definitions — TrackMan conventions, the measured/derived/estimated hierarchy
3. Impact physics — D-plane, face/path weighting, smash factor, spin generation, gear effect
4. Doppler radar systems — CW/FMCW, phase interferometry, harmonic-sideband spin, spin-axis inversion, OERT
5. Photometric systems — stereo photogrammetry, dimple-registration spin, fiducial club tracking, PiTrac
6. Commercial survey — architecture table for every major device
7. Patent landscape — TrackMan/Tuxen, Foresight/Wintriss, FlightScope/EDH, Acushnet, with freedom-to-operate map
8. Ball flight models — Smits–Smith / Quintavalla aerodynamics, EKF trajectory estimation
9. Accuracy — Leach 2017 and the validation literature
10. Design guidance for implementers — capability tiers (radar hardening → optical spin/impact module → fusion → measured club delivery)

Appendix A — Live reference library: every source as a clickable link, organized by category (patents, FCC filings, manufacturer docs, peer-reviewed literature, engineering references, DIY projects, comparative testing)

Appendix C — Sensor hardware and integration reference: OPS243-A specs/API/rolling buffer + the AN-029 vendor golf recipe (a vendor-published golf configuration), K-LD7 datasheet + UART protocol, IWR6843 FMCW specifics, Pi Global Shutter XTR triggering, the full GSPro Open Connect schema, USGA equipment constants, and CFAR selection guidance

Appendix D — Patent portfolio compendium: every identified US patent for TrackMan (all 45 on their legal page + 7 more), Topgolf Sweden/Toptracer, FlightScope/EDH, Full Swing (US11311789 grant), Garmin, Rapsodo, Foresight/Wintriss, Creatz/Uneekor, Golfzon, Acushnet (back to the ancestral 1977 US4136387), plus prior art (Sports Sensors, Weibel, Stalker) — each number hotlinked to Google Patents, with two attribution corrections (US10596416 family = Toptracer, not TrackMan)

Appendix E — Clubhead kinematics from radar velocities: a screw-theoretic how-to — why Doppler measurements are exactly linear in the club's twist (reciprocal product of sight line and screw), what each OpenFlight sensor can observe (OPS243-A = 1D velocity distribution only; K-LD7 = wrong envelope; IWR6843 = full rigid-body estimation with custom chirps), a seven-step estimation recipe (OS-CFAR → segmentation → per-frame twist least squares → observability/SVD truncation → SE(3) smoothing with low-pitch and hub priors → impact-time evaluation → parameter projections including closure rate and ISA swing plane), and a four-stage validation plan; notes that ISA theory is established in golf biomechanics (Vena et al.) but no vendor publicly uses the screw formalism

Appendix B — Detailed implementation guidance: OPS243-A DSP parameters (Doppler scaling, window/chirp trade-offs, comb spin estimation), K-LD7 interferometry + EKF/RTS smoother design, alignment calibration procedures, D-plane inversion with priors and gear-effect bounds, Phase-2 optical module design parameters (strobe timing, dimple registration), and the MLM2PRO validation protocol
