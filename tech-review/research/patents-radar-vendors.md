# Golf Launch-Monitor Radar Patent Dossier (radar-side vendors + Doppler prior art)

Method: Google Patents structured queries (assignee + inventor), cross-checked against Justia. Status from Google Patents legal-status fields.

## 1. FlightScope / EDH (Henri Johnson)

| Number | Title | Priority | Method / status |
|---|---|---|---|
| WO2003032006A1 (GB2380682A) | Golf ball tracking device | 2001 | Foundational FlightScope filing: Doppler + antenna array, 3D phase-monopulse tracking. No US grant; expired art. |
| US8189857B2 | Detecting mark on playing surface, tracking object | 2007 | Bounce-mark detection + tracking (cricket adjudication). Active. |
| US9036864B2 | Ball trajectory and bounce position detection | 2011 | Trajectory + bounce from combined sensor track fitting. Active–Reinstated. |
| US9868044B2 | Ball spin rate measurement | 2013 | Spin from instantaneous phase modulation (dielectric lens). Active–Reinstated. |
| US10775492B2 | Golf ball spin axis measurement | 2013 | Axis from multi-antenna phase analysis. |
| US10338209B2 | Systems to track a moving sports object | 2015 | Multi-receiver Doppler 3D tracking (Fusion Tracking). |
| US11016188B2 | (continuation) | 2015 | Extends array-tracking claims. |
| US11573082B2 (+US20240085178A1 pending) | Tracking in varied environmental conditions | 2019 | Weather/lighting-robust sensor fusion. |
| US12528005B2 | Weather-based range prediction, club selector | 2023 | Live-weather ballistic prediction. |
| US20260091289A1 | Intelligent club recommendation (pending) | 2024 | ML club recommendation. |
| US20160306036A1 | Tracking ball to and on putting green | 2013 | **Abandoned** — citable published art. |
| US20180239012A1 | Antenna with boresight optical system | 2013 | Fusion hardware (co-boresighted camera). **Abandoned**. |

No US patents for the 1990s Speedball cricket radar or 2001 tennis radar (product firsts, unpatented in US).

## 2. Full Swing Golf

**US2020/0147470 granted as US11311789B2** (App 16/678,322, filed 2019-11-08, DeLeon/Nicora/Wang; expiration ~2039-11-08).

| Number | Title | Priority | Method |
|---|---|---|---|
| US11311789B2 | Launch monitor | 2018 | CW Doppler (speed/spin) + FMCW (range) time-multiplexed, non-uniform TX/RX array. Active. |
| US11844990B2 | Launch monitor (continuation) | 2018 | Further CW+FMCW hybrid claims. |
| USD1049104S1 | Launch monitor (design) | 2020 | KIT housing. |
| US11875517B2 / US12354282B2 | Golf ball tracking system | 2020 | Frame-difference ball pixel tracking; screen impact point. |
| US8926416B2 / US10058733B2 | Sports simulator | 2007 | Spin via image analysis + velocity vector. |
| US8758103B2 / US9616346B2 / US11033826B2 | Sports simulation | 2009 | **Light-curtain claims**: IR emitter/sensor arrays for translation + imaging for rotation. |
| US8414408B2 / US8834284B2 | Golf simulation apparatus | 2009 | Ball-permeable screen, ball return. |
| US9440134B2, US9764213B2, US11207581B2 | Simulated golf | 2010 | Simulator + exercise device, depth camera. |
| US10596442B2 | Golf simulation system | 2013 | Architecture claims. |

Disambiguation: US10605910B2/US11086008B2 = **Alphawave Golf (Pty) Ltd**; US11565166B2 = individual inventor. NOT Full Swing.

## 3. Garmin

| Number | Title | Priority | Method |
|---|---|---|---|
| US11351436B2 | Hybrid golf launch monitor | 2019 | The R10 patent: Doppler radar + camera supplement/correction. Active. |
| US8647214B2 | Analyzing golf swings | 2008 | Motion-sensor swing analysis. |
| US20150328523A1 | Swing analysis (TruSwing) | 2014 | Abandoned. |
| US7467060B2 / US7827000B2 / US8055469B2 | Estimating a motion parameter | 2006 | Wearable motion estimation (background). |

Garmin's golf-radar estate is essentially the single US11351436 family.

## 4. Rapsodo Pte. Ltd.

| Number | Title | Priority | Method |
|---|---|---|---|
| US9955126B2 | Analyzing moving objects | 2015 | Core camera+radar unit patent. |
| US11170513B2 | Object surface matching with template | 2016 | **Marked-ball spin**: template matching of surface markers across frames. |
| US11747461B2 | Radar and camera-based data fusion | 2018 | Doppler track + camera observations fused. |
| US20210299540A1 | 3D reconstruction of launching scene | 2018 | Club+ball scene reconstruction. |
| US20230343001A1 | Object trajectory simulation | 2019 | Trajectory extension from measured segment. |
| US20230065614A1 | Detection and estimation of spin | 2021 | Spin pipeline. |
| US20230364468A1 / US20230070986A1 | Deep-learning ball/club parameters from radar+image | 2021 | Joint NN inference. |
| US12169941B1 | Position object crosses target plane | 2024 | Impact-screen localization. |
| US12586248B2 / US12548194B2 | Camera+radar fusion position/speed | 2024 | Newest fusion grants. |
| US12158517B1 | Range-gated imager | 2024 | Range-gated optical ball imaging. |
| EP4695780A1 etc. | Spin rate & axis in flight; marked-object spin | 2023-24 | Ongoing filings. |
| JP6104464B2 | Launch parameter measurement | 2013 | Earliest Rapsodo filing (JP only). |

## 5. Ernest Sports / Voice Caddie

**Ernest Sports: no patents found** (quad-Doppler claims unpatented/trade secret). Voice Caddie = Ucomm Technology Co., Ltd.: US10338212B2 (2014, Swing Caddie portable Doppler swing/ball analyzer — only US grant); KR20160105179A; KR20170133804A (FMCW moving-target core).

## 6. Sports Sensors / Albert Dilz (foundational expired radar art)

| Number | Title | Priority | Status |
|---|---|---|---|
| US6079269A | Miniature sports radar speed measuring device (Swing Speed Radar) | 1997 | Expired — free art |
| US6898971B2 | (continuation) | 2000 | Expired |
| WO2000037964A1 / WO2000039591A1 (Glove Radar) / USD425435S | siblings | 1998 | Expired |
| US8007367B2 | Radar for club head speed and tempo | 2005 | Expired (fee) — free art |
| US10071296B2 | Radar-instrumented batting tee | 2015 | Active |
| US20210349214A1 | Side-looking speed measuring (cosine-error) | 2020 | Application |

## 7. Doppler prior art

**Weibel Scientific A/S** (TrackMan founders' origin): EP1735637B1 (2004, multi-antenna CW Doppler object detection/tracking), WO2006094510A1 (FM-CW radar), ES2832051T3/ES2764463T3 (2014, MFCW multi-frequency range estimation + frequency-set quality), EP4720720A1 (2023 radar imaging).

**Applied Concepts (Stalker)**: US10935657B2 (2019, baseball spin via Doppler micro-modulation), US20240411020A1 (spin via autocorrelation), US20260110790A1 (spin normalization across aspect), US7049999B1/US7057550B1/US7864102B2 (traffic Doppler DSP fundamentals).

### Cross-cutting notes
- Full Swing US11311789/US11844990 are the only US patents claiming CW+FMCW dual-mode golf launch monitor with non-uniform array.
- EDH abandonments (US20160306036, US20180239012) and reinstatements (US9036864, US9868044) are notable prosecution details.
- Free art: entire Sports Sensors family, EDH 2001 WO/GB golf tracking, pre-2006 Weibel/Applied Concepts.
- Citation traps: Alphawave Golf and individual-owned patents mimic Full Swing in text search.

URLs: https://patents.google.com/patent/<number>/en throughout.
