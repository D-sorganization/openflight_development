# NOTEBOOK_LM_CONTEXT: OpenFlight Development (Launch Monitor, Force Plate & MoCap)

> **Agent Context Directive**: This notebook serves as the master knowledge base and context pack for AI agents and NotebookLM writing systems generating technical content, documentation, or articles for the **OpenFlight Development** ecosystem, specifically feeding launch monitor sensors, tri-axial force plate dynamics, and 3D motion capture articles.

---

## 1. Domain & Project Architecture

**OpenFlight Development** is an open-hardware and software telemetry suite integrating high-speed optical vision, FMCW Doppler radar, tri-axial force plate arrays, and 3D optical motion capture for athletic impact and movement analysis.

### Core Telemetry Subsystems:
```
                       +-----------------------------------+
                       |    Impact Event & Athlete Motion  |
                       +-----------------+-----------------+
                                         |
            +----------------------------+----------------------------+
            |                            |                            |
            v                            v                            v
 +----------------------+    +-----------------------+    +-----------------------+
 | Launch Monitor Optics|    |    Doppler Radar      |    | Force Plate Hardware  |
 | Stereo High-Speed    |    | 24/60 GHz FMCW        |    | Tri-Axial Strain Gauge|
 | Impact & Spin Axis   |    | Velocity & Range FFT  |    | GRF Vectors & COP     |
 +----------+-----------+    +-----------+-----------+    +-----------+-----------+
            |                            |                            |
            +----------------------------+----------------------------+
                                         |
                                         v
                       +-----------------------------------+
                       | Synchronized Telemetry Engine     |
                       +-----------------------------------+
```

---

## 2. Sensor Physics & Mathematical Derivations

### 2.1 Launch Monitor Sensor Physics
1. **High-Speed Optical Stereoscopic Imaging**:
   - Stereo pair intrinsic parameters matrix $K$ and extrinsic rotation/translation $[R | \mathbf{t}]$.
   - 3D marker centroid reconstruction from 2D pixel coordinates $(u, v)$ via epipolar geometry and triangulation.
   - Ball launch angle $\theta_{launch}$, azimuth $\phi_{az}$, ball speed $v_0$, and 3D spin vector $\boldsymbol{\omega}$ estimation.

2. **Doppler Radar (FMCW / Continuous Wave)**:
   - Baseband beat frequency $f_b = \frac{2 B R}{c T_c} + \frac{2 f_0 v}{c}$.
   - FFT range-Doppler processing for velocity tracking ($v_{club}, v_{ball}$) pre- and post-impact.

### 2.2 Force Plate Dynamics & Center of Pressure (COP)
Tri-axial force sensors measure Ground Reaction Force (GRF) vector components $\mathbf{F} = (F_x, F_y, F_z)^T$ and moments $\mathbf{M} = (M_x, M_y, M_z)^T$.

- **Center of Pressure (COP)**:
  $$
  x_{COP} = \frac{-M_y + F_x z_0}{F_z}, \quad y_{COP} = \frac{M_x + F_y z_0}{F_z}
  $$
  where $z_0$ is the vertical distance from sensor origin to the top plate surface.

- **Free Moment (Torque about vertical axis $T_z$)**:
  $$
  T_z = M_z - x_{COP} F_y + y_{COP} F_x
  $$

- **Shear Forces & Loading Rate**:
  - $F_x$: Lateral (side-to-side) shear force.
  - $F_y$: Anterior-Posterior (toe-to-heel) shear force.
  - Vertical Loading Rate: $dF_z / dt$ during transition from backswing to downswing.

### 2.3 3D Motion Capture & Kinematic Alignment
- **Segment Coordinate Systems (SCS)**: Defined for pelvis, thorax, lead upper arm, lead forearm, and club.
- **Euler / Cardan Angle Rotations**: $Z-Y'-X''$ sequence (Flexion/Extension, Abduction/Adduction, Internal/External Rotation).
- **Temporal Synchronization**: Triggering frame $t_0$ across optical cameras ($1000\text{ fps}$), Doppler radar ($100\text{ Hz}$ update), force plates ($1000\text{ Hz}$), and optical mocap ($250\text{ Hz}$).

---

## 3. Technical Article Drafting Frameworks

Use the structured context below to feed technical writing articles:

### Article Feeder 1: Launch Monitor Physics & Hardware Architecture
- **Focus**: Comparing optical high-speed vision vs FMCW radar for measuring launch parameters.
- **Key Points**: Photogrammetric error bounds, shutter speed requirements ($1/10,000\text{ s}$), rolling vs global shutter distortion, and spin axis vector calculation.

### Article Feeder 2: Ground Reaction Force (GRF) & COP Trajectory Analysis
- **Focus**: Biomechanics of ground force generation in explosive rotary athletic movements.
- **Key Points**: Lead vs trail foot vertical force distribution, COP trace path during downswing, peak vertical force timing relative to arm uncocking, and free moment $T_z$ torque creation.

### Article Feeder 3: Integrated 3D Motion Capture & Sensor Fusion
- **Focus**: Synchronizing force vectors with kinematic body segment movements.
- **Key Points**: Mapping GRF force vectors to joint moment centers, kinetic sequence energy transfer, and multi-sensor calibration protocols.

---

## 4. Key Terminology & Index for AI Agents

| Term | Definition | Context Usage |
| :--- | :--- | :--- |
| **GRF** | Ground Reaction Force 3D vector $(F_x, F_y, F_z)$ | Tri-axial force plate kinetics |
| **COP** | Center of Pressure $(x_{COP}, y_{COP})$ | Force centroid location on footbed/plate |
| **Smash Factor** | Ratio $v_{ball} / v_{club}$ | Impact efficiency parameter |
| **Free Moment ($T_z$)** | Pure rotational torque about vertical axis | Foot-ground friction interaction |
| **FMCW Radar** | Frequency-Modulated Continuous-Wave Radar | Ball & club velocity tracking |
