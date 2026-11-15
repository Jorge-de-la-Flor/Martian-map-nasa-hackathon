# Route-planning algorithm

## 1. Elevation model

The DEM represents terrain elevation as:

\[
Z = Z(x,y)
\]

where x and y are projected Martian coordinates in metres.

The raster must contain valid elevation values and an explicitly defined
NoData mask.

## 2. Slope

The gradient is:

\[
p = \frac{\partial Z}{\partial x},
\qquad
q = \frac{\partial Z}{\partial y}
\]

Slope angle:

\[
\theta = \arctan\left(\sqrt{p^2+q^2}\right)
\]

The implementation uses the Horn 3x3 operator.

The derivatives are initially calculated in raster pixel coordinates.
The affine transformation is then used to obtain derivatives in projected
world coordinates.

The outer raster border and cells without a complete valid neighborhood
do not receive a slope value. Such cells are not traversable.

## 3. Movement distance

For neighboring raster cells u and v, distance is calculated from their
projected cell-center coordinates:

\[
d(u,v) =
\sqrt{(x_v-x_u)^2+(y_v-y_u)^2}
\]

This supports horizontal, vertical, and diagonal movements.

The raster must use projected Martian coordinates in metres.

Haversine distance may be used separately for approximate geographic
checks, but it is not used as the grid movement metric.

## 4. Traversal cost

The implemented movement-cost model is:

\[
C(u,v)=d(u,v)
\left[
1+\lambda_s s^2+\lambda_h H+\lambda_u U
\right]
+\lambda_{\Delta h}|\Delta h|
\]

where:

- d is horizontal movement distance.
- s is the mean endpoint slope normalized by a reference slope.
- H is mean hazard severity.
- U is mean uncertainty.
- Δh is elevation difference.
- λ values are configurable weights.

The initial slope reference is 15 degrees.

Hazard and uncertainty values must be normalized between 0 and 1.

All weights are non-negative. Therefore:

\[
C(u,v)\geq d(u,v)
\]

This property is important for the A* heuristic.

## 5. Route profiles

### Direct

All terrain penalties are zero.

The objective is the shortest feasible path through traversable cells.

### Low Slope

Slope receives a positive penalty.

This profile can accept a longer route to reduce steep terrain.

### Conservative

Slope, hazards, uncertainty, and elevation change receive positive penalties.

Missing hazard information is not interpreted as evidence that no hazard exists.

When no uncertainty raster is supplied, uncertainty defaults to 1.0 over the entire DEM.

## 6. A*

The raster grid is an eight-connected graph.

A* evaluates:

\[
f(n)=g(n)+h(n)
\]

where:

- g(n) is accumulated movement cost.
- h(n) is Euclidean distance to the destination.
- f(n) is estimated total route cost.

The heuristic is admissible because every movement cost is at least
the corresponding horizontal distance.

Diagonal movement is rejected when either adjacent orthogonal cell
is not traversable. This prevents corner cutting.

## 7. Route metrics

The planner returns:

- Total horizontal distance.
- Accumulated ascent.
- Accumulated descent.
- Maximum slope.
- Distance-weighted mean slope.
- Total movement cost.
- Distance through cells with mean uncertainty >= 0.5.
- Distance through cells with mean hazard >= 0.5.
- Number of expanded A* nodes.

The uncertainty and hazard exposure distances are threshold-based
descriptive metrics, not biological or engineering risk estimates.

## 8. Optional duration

When a user explicitly supplies a constant walking speed v:

\[
T = \frac{D}{v}
\]

This is a scenario estimate only. It does not model fatigue, suit
constraints, terrain-dependent speed, rest periods, or environmental
conditions.

## 9. Limitations

This model does not prove astronaut safety or actual terrain traversability.

The quality and resolution of the selected DEM, hazard layers,
and uncertainty layers directly affect route results.
