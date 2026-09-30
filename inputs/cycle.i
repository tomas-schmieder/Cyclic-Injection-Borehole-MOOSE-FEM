# Cyclic injection / abstraction in a poroelastic aquifer.
#
# This is the ONLY input file in the study. Every case is this model with a
# different permeability tensor, applied from the command line rather than by
# copying the file:
#
#   ./borehole1-opt -i inputs/cycle.i \
#       Materials/perm/permeability='1E-10 0 0   0 1E-10 0   0 0 0' \
#       Outputs/file_base=results/high_gravel/output
#
# Command-line overrides are exact -- they produce byte-identical output to
# editing the value in place. scripts/run.sh drives this from cases.csv.
#
# The permeability below is the base (mildly cross-coupled) case, used when no
# override is given.
#
# Revised September 2026 (docs/CORRECTIONS.md, items 7-10): the in-situ stress
# is now initialised in equilibrium with the initial pore pressure, the well
# flux signs follow PorousFlowSink's convention (positive = out of the rock),
# and the samplers record the true ground surface and the well walls.

[Mesh]
  file = '../mesh/cycle1.msh'
  construct_side_list_from_node_list = true
[]

[GlobalParams]
  displacements = 'disp_x disp_y'
  gravity = '0 0 0'
  biot_coefficient = 1.0
  PorousFlowDictator = dictator
[]

[Variables]
  [porepressure]
    initial_condition = 1e6
  []
  [disp_x]
    initial_condition = 0
    scaling = 1e-5
    order = FIRST
    family = LAGRANGE
  []
  [disp_y]
    initial_condition = 0
    scaling = 1e-5
    order = FIRST
    family = LAGRANGE
  []
[]

[Functions]
  # 500 s cycle, wells in antiphase. PorousFlowSink's flux is measured OUT of
  # the rock (kg m^-2 s^-1): positive is a sink, negative a source. The
  # injection well therefore carries the negative sign, so it injects during
  # the first half-cycle while the abstraction well withdraws.
  [one_cycle_injection]
    type = ParsedFunction
    expression = '-10000 * (315e-6 / (2 * pi * 1 * 20)) * sin(2 * pi * t / 500)'
  []
  [one_cycle_withdrawal]
    type = ParsedFunction
    expression = '10000 * (315e-6 / (2 * pi * 1 * 20)) * sin(2 * pi * t / 500)'
  []
[]

[FluidProperties]
  [water]
    type = SimpleFluidProperties
    viscosity = 1e-3
    bulk_modulus = 2.1e9
    density0 = 1000
  []
[]

[PorousFlowFullySaturated]
  coupling_type = HydroMechanical
  porepressure = porepressure
  displacements = 'disp_x disp_y'
  fp = water
[]

[Materials]
  # The one block every case overrides.
  [perm]
    type = PorousFlowPermeabilityConst
    permeability = '1E-13 5E-14 0   5E-14 1E-13 0   0 0 1E-13'
  []
  [elasticity]
    type = ComputeIsotropicElasticityTensor
    youngs_modulus = 5E9
    poissons_ratio = 0.3
  []
  [strain]
    type = ComputeSmallStrain
    eigenstrain_names = ini_stress
  []
  # In-situ state. The pore pressure starts at 1 MPa, and total stress is
  # sigma = sigma' - alpha p I. Without an initial effective stress the free
  # boundaries (ground surface, well walls) see an unbalanced 1 MPa at t = 0, so
  # the first step is a sudden, spurious 1.4-1.9 mm mid-depth uplift and an
  # undrained pressure drop of up to 0.23 MPa that never recovers in the tight
  # cases. Setting sigma'_0 = alpha p_0 I = +1 MPa I (tension positive) puts
  # the reference state in equilibrium, so displacement is measured from the
  # in-situ state and only the injection cycle moves the ground.
  [ini_stress]
    type = ComputeEigenstrainFromInitialStress
    eigenstrain_name = ini_stress
    initial_stress = '1e6 0 0   0 1e6 0   0 0 1e6'
  []
  [stress]
    type = ComputeLinearElasticStress
  []
  [porosity]
    type = PorousFlowPorosityConst
    porosity = 0.2
  []
[]

[Kernels]
  [stress_x]
    type = StressDivergenceTensors
    variable = disp_x
    component = 0
    use_displaced_mesh = false
  []
  [stress_y]
    type = StressDivergenceTensors
    variable = disp_y
    component = 1
    use_displaced_mesh = false
  []
  [poro_x]
    type = PorousFlowEffectiveStressCoupling
    variable = disp_x
    component = 0
    use_displaced_mesh = false
  []
  [poro_y]
    type = PorousFlowEffectiveStressCoupling
    variable = disp_y
    component = 1
    use_displaced_mesh = false
  []
[]

[BCs]
  [injection_cycle]
    type = PorousFlowSink
    variable = porepressure
    boundary = inj_well
    flux_function = one_cycle_injection
  []
  [withdrawal_cycle]
    type = PorousFlowSink
    variable = porepressure
    boundary = abs_well
    flux_function = one_cycle_withdrawal
  []
  [constant_output_porepressure]
    type = DirichletBC
    variable = porepressure
    value = 1e6
    boundary = 'left right'
  []
  [fixed_x_displacement]
    type = DirichletBC
    variable = disp_x
    value = 0
    boundary = 'left right'
  []
  [fixed_y_displacement]
    type = DirichletBC
    variable = disp_y
    value = 0
    boundary = bottom
  []
[]

[Executioner]
  type = Transient
  scheme = implicit-euler
  start_time = 0.0
  end_time = 1000
  dt = 0.5
  nl_abs_tol = 1e-5
  solve_type = newton
  nl_max_its = 100
[]

[Preconditioning]
  # Default SMP, as used for the published results. A direct solve
  # (petsc_options_iname='-pc_type' petsc_options_value='lu') cuts linear
  # iterations ~87x but changes total wall time by only ~6% -- the cost of this
  # model is PorousFlow material evaluation, not the linear solve -- so it is
  # left off by default to keep results bit-identical to the report.
  active = basic
  [basic]
    type = SMP
    full = true
  []
[]

# Line samplers, 30 points in each of three x-windows (left of, between, and
# right of the wells). Pore pressure and vertical displacement are sampled at
# mid-depth (y = 12.5 m), through the wells; vertical displacement is also
# sampled at the ground surface (y = 25 m), which is what "surface
# displacement" means in the figures. The original study sampled displacement
# only at mid-depth and named the windows inconsistently between fields; both
# are fixed here (docs/CORRECTIONS.md, items 6 and 9).
[VectorPostprocessors]
  [pressure_left]
    type = LineValueSampler
    start_point = '0 12.5 0'
    end_point   = '13.5 12.5 0'
    num_points = 30
    variable = porepressure
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [pressure_between]
    type = LineValueSampler
    start_point = '16.5 12.5 0'
    end_point   = '33.5 12.5 0'
    num_points = 30
    variable = porepressure
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [pressure_right]
    type = LineValueSampler
    start_point = '36.5 12.5 0'
    end_point   = '50 12.5 0'
    num_points = 30
    variable = porepressure
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [disp_left]
    type = LineValueSampler
    start_point = '0 12.5 0'
    end_point   = '13.5 12.5 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [disp_between]
    type = LineValueSampler
    start_point = '16.5 12.5 0'
    end_point   = '33.5 12.5 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [disp_right]
    type = LineValueSampler
    start_point = '36.5 12.5 0'
    end_point   = '50 12.5 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [surface_left]
    type = LineValueSampler
    start_point = '0 25 0'
    end_point   = '13.5 25 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [surface_between]
    type = LineValueSampler
    start_point = '16.5 25 0'
    end_point   = '33.5 25 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [surface_right]
    type = LineValueSampler
    start_point = '36.5 25 0'
    end_point   = '50 25 0'
    num_points = 30
    variable = disp_y
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
[]

# Pressure on the well walls. The mid-depth samplers stop 0.5 m short of each
# wall, and in tight rock the cyclic pressure signal decays over less than that
# (diffusion length ~0.3 m per half-cycle for k = 1e-16, ~3 mm for k = 1e-20).
# These record the pressure the wells actually impose, which is what a
# reservoir engineer would compare against a fracture-pressure limit.
[Postprocessors]
  [inj_wall_p_max]
    type = NodalExtremeValue
    variable = porepressure
    boundary = inj_well
    value_type = max
    execute_on = timestep_end
  []
  [inj_wall_p_min]
    type = NodalExtremeValue
    variable = porepressure
    boundary = inj_well
    value_type = min
    execute_on = timestep_end
  []
  [inj_wall_p_avg]
    type = SideAverageValue
    variable = porepressure
    boundary = inj_well
    execute_on = timestep_end
  []
  [abs_wall_p_max]
    type = NodalExtremeValue
    variable = porepressure
    boundary = abs_well
    value_type = max
    execute_on = timestep_end
  []
  [abs_wall_p_min]
    type = NodalExtremeValue
    variable = porepressure
    boundary = abs_well
    value_type = min
    execute_on = timestep_end
  []
  [abs_wall_p_avg]
    type = SideAverageValue
    variable = porepressure
    boundary = abs_well
    execute_on = timestep_end
  []
[]

[Outputs]
  file_base = 'results/base/output'

  # Sampler and well-wall data. Written every timestep, then folded into a
  # single .npz by scripts/archive.py and deleted. Nothing here is kept
  # long-term.
  [csv]
    type = CSV
    execute_on = timestep_end
  []

  # Field output for ParaView. OFF by default: it is 97% of the data volume and
  # is not needed for any figure in the study. Enable with
  #   Outputs/exodus/enable=true
  # `show` drops the 12 auto-generated elemental variables (9 stress components
  # + 3 Darcy velocities, five of which are identically zero in 2D plane
  # strain); they are 16.4 MB of an 18.7 MB file. Combined with interval, this
  # takes the Exodus from 693 MB to about 18 MB for a full case.
  [exodus]
    type = Exodus
    enable = false
    show = 'disp_x disp_y porepressure'
    interval = 10
  []
[]
