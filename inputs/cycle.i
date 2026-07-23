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
  # 500 s cycle: the wells run in antiphase, injection positive.
  [one_cycle_injection]
    type = ParsedFunction
    expression = '10000 * (315e-6 / (2 * pi * 1 * 20)) * sin(2 * pi * t / 500)'
  []
  [one_cycle_withdrawal]
    type = ParsedFunction
    expression = '-10000 * (315e-6 / (2 * pi * 1 * 20)) * sin(2 * pi * t / 500)'
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

# Six line samplers at mid-depth (y = 12.5 m), 30 points each, covering the
# three x-windows between and outside the wells. NOTE: the region names are
# inconsistent between the two fields -- for porepressure, "right" is the
# 16.5-33.5 window and "middle" is 36.5-50; for disp_y they are swapped. This is
# preserved from the original study. The x coordinate in the output is always
# correct, so scripts/archive.py keys on x and ignores the region name.
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
  [pressure_right]
    type = LineValueSampler
    start_point = '16.5 12.5 0'
    end_point   = '33.5 12.5 0'
    num_points = 30
    variable = porepressure
    warn_discontinuous_face_values = false
    sort_by = x
    execute_on = timestep_end
  []
  [pressure_middle]
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
  [disp_middle]
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
[]

[Outputs]
  file_base = 'results/base/output'

  # Sampler data. Written every timestep, then folded into a single ~2.6 MB
  # .npz by scripts/archive.py and deleted. Nothing here is kept long-term.
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
