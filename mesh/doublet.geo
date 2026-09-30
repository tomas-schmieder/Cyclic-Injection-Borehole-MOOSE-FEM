// === Fractured horizontal doublet: one stimulation stage, plan view ===
//
// Geometry for the in-reservoir storage study (FervoFlex-style charge /
// discharge cycling). A horizontal injector and producer run parallel in the
// x direction, 365 ft apart; one 150 ft stimulation stage with 6 perforation
// clusters (25 ft apart) connects them through 6 transverse hydraulic
// fractures. Those are the Project Red design numbers reported by Norbeck &
// Latimer (2023), Stanford Geothermal Workshop.
//
// The section is horizontal, through both laterals. Transverse fractures are
// vertical planes perpendicular to the laterals, so in this plane they are
// lines crossing from one well to the other; the out-of-plane thickness of
// the model is the fracture height. (A section *perpendicular* to the
// laterals would lie inside a fracture plane, which is why this mesh is not a
// variant of cycle1.geo with a crack between two circular wells.)
//
// The x extent is one stage, with fractures at cluster centres and half a
// cluster spacing to each side wall, so the side walls are symmetry planes
// between repeating stages. y runs to 150 m beyond each well.
//
// Mixed-dimensional and conforming: fractures and wells are 1D line elements
// sharing nodes with the 2D matrix triangles, which is what MOOSE PorousFlow
// needs for explicit fracture flow without MultiApps. libMesh keeps a 1D
// physical group as a block of elements (instead of turning it into a
// sideset) only if its $PhysicalNames line carries the tag
// "lower_dimensional_block"; scripts/make_doublet_mesh.sh adds that tag to the
// fracture, injector and producer groups after gmsh writes the file.
//
// Regenerate with scripts/make_doublet_mesh.sh (gmsh 4.13.1).

// --- Design parameters (SI; 1 ft = 0.3048 m) ---
ft = 0.3048;
S = 365 * ft;       // injector-producer spacing, 111.25 m
dc = 25 * ft;       // perforation-cluster (fracture) spacing, 7.62 m
nc = 6;             // clusters per stage
Lx = nc * dc;       // stage length, 45.72 m (= 150 ft)
ext = 30;           // fracture reach beyond each well, m (assumed; not reported)
Ly = 150;           // far-field margin beyond each well, m

// --- Mesh sizing ---
// Leak-off from a fracture into k ~ 1e-18 m^2 rock penetrates only
// ~sqrt(c t) ~ 0.4 m in a 12 h charge half-cycle, so elements next to the
// fractures must be well below that.
lc_frac = 0.25;     // at fractures and wells
lc_far = 15;        // far field
d_fine = 0.5;       // keep lc_frac out to this distance, m
d_coarse = 60;      // reach lc_far at this distance, m

// --- Points on the two laterals ---
// Column j = 0 is the left wall, j = 1..nc the fractures, j = nc+1 the right wall.
For j In {0:nc+1}
  If (j == 0)
    xj = 0;
  ElseIf (j == nc + 1)
    xj = Lx;
  Else
    xj = dc / 2 + (j - 1) * dc;
  EndIf
  pI[j] = newp; Point(pI[j]) = {xj, 0, 0, lc_far};   // injector, y = 0
  pP[j] = newp; Point(pP[j]) = {xj, S, 0, lc_far};   // producer, y = S
  If (j >= 1 && j <= nc)
    tB[j] = newp; Point(tB[j]) = {xj, -ext, 0, lc_far};    // tip beyond injector
    tT[j] = newp; Point(tT[j]) = {xj, S + ext, 0, lc_far}; // tip beyond producer
  EndIf
EndFor

c1 = newp; Point(c1) = {0, -Ly, 0, lc_far};
c2 = newp; Point(c2) = {Lx, -Ly, 0, lc_far};
c3 = newp; Point(c3) = {Lx, S + Ly, 0, lc_far};
c4 = newp; Point(c4) = {0, S + Ly, 0, lc_far};

// --- Laterals, split at every fracture ---
For j In {0:nc}
  wI[j] = newl; Line(wI[j]) = {pI[j], pI[j + 1]};
  wP[j] = newl; Line(wP[j]) = {pP[j], pP[j + 1]};
EndFor

// --- Verticals between the laterals: side walls (j = 0, nc+1) and fractures ---
For j In {0:nc+1}
  v[j] = newl; Line(v[j]) = {pI[j], pP[j]};
EndFor

// --- Fracture segments outside the well pair ---
For j In {1:nc}
  fB[j - 1] = newl; Line(fB[j - 1]) = {tB[j], pI[j]};
  fT[j - 1] = newl; Line(fT[j - 1]) = {pP[j], tT[j]};
EndFor

// --- Outer boundary ---
bot = newl;  Line(bot)  = {c1, c2};
rLow = newl; Line(rLow) = {c2, pI[nc + 1]};
rUp = newl;  Line(rUp)  = {pP[nc + 1], c3};
top = newl;  Line(top)  = {c3, c4};
lUp = newl;  Line(lUp)  = {c4, pP[0]};
lLow = newl; Line(lLow) = {pI[0], c1};

// --- Surfaces ---
// Between the laterals the fractures cross the whole strip, so it is split
// into nc+1 rectangles with the fractures as shared edges. Outside the
// laterals the fracture segments end in the rock and are embedded instead.
For k In {0:nc}
  cl = newll; Curve Loop(cl) = {wI[k], v[k + 1], -wP[k], -v[k]};
  sM[k] = news; Plane Surface(sM[k]) = {cl};
EndFor

loopB[] = {bot, rLow};
For j In {nc:0:-1}
  loopB[] += {-wI[j]};
EndFor
loopB[] += {lLow};
cl = newll; Curve Loop(cl) = loopB[];
sB = news; Plane Surface(sB) = {cl};
Curve{fB[]} In Surface{sB};

loopT[] = {};
For j In {0:nc}
  loopT[] += {wP[j]};
EndFor
loopT[] += {rUp, top, lUp};
cl = newll; Curve Loop(cl) = loopT[];
sT = news; Plane Surface(sT) = {cl};
Curve{fT[]} In Surface{sT};

// --- Physical groups (explicit tags; libMesh uses them as block / boundary IDs) ---
frac[] = {fB[], fT[]};
For j In {1:nc}
  frac[] += {v[j]};
EndFor
perfI[] = {};
perfP[] = {};
For j In {1:nc}
  perfI[] += {pI[j]};
  perfP[] += {pP[j]};
EndFor

Physical Surface("matrix", 1) = {sB, sM[], sT};
Physical Curve("fracture", 2) = {frac[]};
Physical Curve("injector", 3) = {wI[]};
Physical Curve("producer", 4) = {wP[]};
Physical Curve("bottom", 11) = {bot};
Physical Curve("top", 12) = {top};
Physical Curve("left", 13) = {lLow, v[0], lUp};
Physical Curve("right", 14) = {rLow, v[nc + 1], rUp};
Physical Point("inj_perfs", 21) = {perfI[]};
Physical Point("prod_perfs", 22) = {perfP[]};

// --- Refinement toward fractures and wells ---
Field[1] = Distance;
Field[1].CurvesList = {frac[], wI[], wP[]};
Field[1].Sampling = 400;

Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = lc_frac;
Field[2].SizeMax = lc_far;
Field[2].DistMin = d_fine;
Field[2].DistMax = d_coarse;
Background Field = 2;

Mesh.MeshSizeExtendFromBoundary = 0;
Mesh.MeshSizeFromPoints = 0;
Mesh.MeshSizeFromCurvature = 0;

// === Final mesh settings ===
Mesh.MshFileVersion = 2.2;
Mesh.Algorithm = 6;
Mesh 2;
