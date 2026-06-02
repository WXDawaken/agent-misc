const width = Param.number("Width", 92, { min: 60, max: 140, unit: "mm" });
const depth = Param.number("Depth", 56, { min: 36, max: 90, unit: "mm" });
const baseThickness = Param.number("Base Thickness", 8, { min: 5, max: 14, unit: "mm" });
const wallThickness = Param.number("Wall Thickness", 7, { min: 4, max: 12, unit: "mm" });
const uprightHeight = Param.number("Upright Height", 58, { min: 36, max: 95, unit: "mm" });
const holeRadius = Param.number("Mount Hole Radius", 4.2, { min: 2.5, max: 6, unit: "mm" });

const ribThickness = 7;
const ribDepth = depth * 0.55;
const ribHeight = uprightHeight * 0.52;
const holeInsetX = width * 0.32;
const holeInsetY = depth * 0.27;

scene({
  background: { top: "#d8dee6", bottom: "#606a75" },
  camera: { position: [120, -130, 90], target: [0, 6, 22], fov: 42 },
  environment: { preset: "studio", intensity: 0.18, background: false },
  lights: [
    { type: "ambient", color: "#f0ece4", intensity: 0.18 },
    { type: "directional", position: [180, -220, 260], target: [0, 0, 18], color: "#ffe4c4", intensity: 2.7, castShadow: true },
    { type: "directional", position: [-160, 120, 180], target: [0, 0, 18], color: "#d9ebff", intensity: 0.8 },
  ],
  ground: { visible: true, color: "#8d98a6", height: -2, receiveShadow: true },
});

const base = box(width, depth, baseThickness);
const upright = box(width, wallThickness, uprightHeight)
  .translate(0, depth / 2 - wallThickness / 2, baseThickness);

function rib(x) {
  return box(ribThickness, ribDepth, ribHeight)
    .translate(x, depth / 2 - wallThickness - ribDepth / 2, baseThickness);
}

const holeCutters = [];
for (const x of [-holeInsetX, holeInsetX]) {
  for (const y of [-holeInsetY, holeInsetY]) {
    holeCutters.push(cylinder(baseThickness * 3, holeRadius, undefined, 48).translate(x, y, -baseThickness));
  }
}

const bracket = union(base, upright, rib(-width * 0.28), rib(width * 0.28))
  .subtract(...holeCutters)
  .color("#53616f");

verify.greaterThan("base has material between left holes", width / 2 - holeInsetX - holeRadius, 12);
verify.greaterThan("front hole edge margin", depth / 2 - holeInsetY - holeRadius, 8);
verify.boundingBoxSize("overall bracket size", bracket, [width, depth, uprightHeight + baseThickness], 0.25);

return [
  {
    name: "Single-piece L bracket with ribbed web and four mounting holes",
    tags: ["forgecad", "orbitlens-test", "bracket"],
    shape: bracket,
  },
];
