// === Bulletproof Step 3 Mesh with Refinement Near Wells ===

// --- Mesh sizing parameters ---
lc_outer = 2.0;     // Coarse mesh away from wells
lc_inner = 0.25;    // Fine mesh near wells

// --- Domain parameters ---
W = 50;             // Width
H = 25;             // Height
Rw = 1;             // Well radius
xc1 = 15;           // Inj well x
xc2 = 35;           // Abs well x
yc = H/2;           // Vertical center

// === Outer rectangle ===
Point(1) = {0, 0, 0, lc_outer};
Point(2) = {W, 0, 0, lc_outer};
Point(3) = {W, H, 0, lc_outer};
Point(4) = {0, H, 0, lc_outer};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};

// === Injection well arcs ===
Point(10) = {xc1 - Rw, yc, 0, lc_inner};
Point(11) = {xc1, yc + Rw, 0, lc_inner};
Point(12) = {xc1 + Rw, yc, 0, lc_inner};
Point(13) = {xc1, yc - Rw, 0, lc_inner};
Point(14) = {xc1, yc, 0, lc_inner};  // center
Circle(10) = {10, 14, 11};
Circle(11) = {11, 14, 12};
Circle(12) = {12, 14, 13};
Circle(13) = {13, 14, 10};

// === Abstraction well arcs ===
Point(20) = {xc2 - Rw, yc, 0, lc_inner};
Point(21) = {xc2, yc + Rw, 0, lc_inner};
Point(22) = {xc2 + Rw, yc, 0, lc_inner};
Point(23) = {xc2, yc - Rw, 0, lc_inner};
Point(24) = {xc2, yc, 0, lc_inner};  // center
Circle(20) = {20, 24, 21};
Circle(21) = {21, 24, 22};
Circle(22) = {22, 24, 23};
Circle(23) = {23, 24, 20};

// === Surface with holes ===
Line Loop(30) = {1, 2, 3, 4};              // outer box
Line Loop(31) = {10, 11, 12, 13};          // inj well
Line Loop(32) = {20, 21, 22, 23};          // abs well
Plane Surface(100) = {30, 31, 32};         // domain with two holes

// === Physical groups ===
Physical Surface("domain") = {100};
Physical Curve("bottom") = {1};
Physical Curve("right")  = {2};
Physical Curve("top")    = {3};
Physical Curve("left")   = {4};
Physical Curve("inj_well") = {10, 11, 12, 13};
Physical Curve("abs_well") = {20, 21, 22, 23};

// === Refinement field ===
Field[1] = Distance;
Field[1].CurvesList = {10, 11, 12, 13, 20, 21, 22, 23};

Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = lc_inner;
Field[2].SizeMax = lc_outer;
Field[2].DistMin = 1.0;
Field[2].DistMax = 5.0;
Background Field = 2;

// === Final mesh settings ===
Mesh.MshFileVersion = 2.2;
Mesh.Algorithm = 6;
Mesh 2;
