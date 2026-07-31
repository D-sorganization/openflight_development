# Launch Monitor Technology Review

A comprehensive LaTeX technology review of how commercial golf launch monitors
work — radar physics, camera photogrammetry, patent landscape, and the
club/ball parameter calculations — written to guide OpenFlight development.

- **[main.pdf](main.pdf)** — the compiled report (~37 pages)
- `main.tex` + `sections/` — LaTeX source (10 chapters + bibliography)
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
10. Implications for OpenFlight — phased roadmap (radar hardening → optical spin/impact module → fusion)
