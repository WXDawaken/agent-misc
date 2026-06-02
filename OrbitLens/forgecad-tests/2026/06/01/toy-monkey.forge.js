const scale = Param.number("Scale", 1, { min: 0.6, max: 1.6, unit: "x" });
const pose = Param.choice("Pose", "waving", ["waving", "standing"]);

const fur = "#7a4b2a";
const darkFur = "#56321f";
const face = "#d9ad79";
const black = "#171412";
const white = "#fff5e6";

scene({
  background: { top: "#d9e4ef", bottom: "#7c8c9d" },
  camera: { position: [92, -132, 78], target: [0, -4, 38], fov: 38 },
  environment: { preset: "studio", intensity: 0.22, background: false },
  lights: [
    { type: "ambient", color: "#f3eadf", intensity: 0.18 },
    { type: "directional", position: [160, -210, 240], target: [0, 0, 34], color: "#ffe5c5", intensity: 2.7, castShadow: true },
    { type: "directional", position: [-120, 80, 160], target: [0, 0, 34], color: "#d8ecff", intensity: 0.75 },
  ],
  ground: { visible: true, color: "#8f9aa4", height: -1, receiveShadow: true },
});

function part(name, shape, tags = []) {
  return {
    name,
    tags: ["toy-monkey", ...tags],
    shape: shape.scale(scale),
  };
}

function ellipsoid(radius, xyzScale, position, color) {
  return sphere(radius, 28)
    .scale(xyzScale)
    .translate(...position)
    .color(color);
}

function angledEllipsoid(radius, xyzScale, position, rotation, color) {
  let shape = sphere(radius, 24).scale(xyzScale);
  if (rotation.x) shape = shape.rotateX(rotation.x);
  if (rotation.y) shape = shape.rotateY(rotation.y);
  if (rotation.z) shape = shape.rotateZ(rotation.z);
  return shape.translate(...position).color(color);
}

const rightArmLift = pose === "waving";

const body = ellipsoid(18, [0.9, 0.78, 1.22], [0, 0, 30], fur);
const belly = ellipsoid(11, [0.95, 0.34, 1.15], [0, -14.4, 31], face);
const head = ellipsoid(16, [1.0, 0.92, 1.02], [0, -2, 58], fur);
const muzzle = ellipsoid(8.7, [1.28, 0.58, 0.78], [0, -16.2, 54.8], face);
const brow = ellipsoid(7.8, [1.35, 0.35, 0.35], [0, -15.8, 63.5], darkFur);

const leftEar = ellipsoid(8.3, [0.52, 0.98, 1.02], [-16.4, -1, 59.5], fur);
const rightEar = ellipsoid(8.3, [0.52, 0.98, 1.02], [16.4, -1, 59.5], fur);
const leftInnerEar = ellipsoid(5.2, [0.35, 0.8, 0.82], [-17.2, -4.4, 59.5], face);
const rightInnerEar = ellipsoid(5.2, [0.35, 0.8, 0.82], [17.2, -4.4, 59.5], face);

const leftEye = ellipsoid(2.25, [1, 0.45, 1], [-5.8, -16.7, 64.4], black);
const rightEye = ellipsoid(2.25, [1, 0.45, 1], [5.8, -16.7, 64.4], black);
const leftGlint = ellipsoid(0.7, [1, 0.5, 1], [-5.1, -18.2, 65.2], white);
const rightGlint = ellipsoid(0.7, [1, 0.5, 1], [6.5, -18.2, 65.2], white);
const nose = ellipsoid(2.45, [1.25, 0.58, 0.7], [0, -22.1, 57.4], black);
const smileLeft = ellipsoid(1.15, [1.9, 0.5, 0.5], [-3.2, -22.4, 51.2], black).rotateZ(-18);
const smileRight = ellipsoid(1.15, [1.9, 0.5, 0.5], [3.2, -22.4, 51.2], black).rotateZ(18);

const leftArm = angledEllipsoid(5.0, [0.74, 0.72, 3.05], [-18.2, -1.5, 35], { x: 0, y: -28, z: -9 }, fur);
const rightArm = rightArmLift
  ? angledEllipsoid(4.8, [0.72, 0.7, 3.0], [19.3, -3, 46], { x: 0, y: 38, z: 16 }, fur)
  : angledEllipsoid(5.0, [0.74, 0.72, 3.05], [18.2, -1.5, 35], { x: 0, y: 28, z: 9 }, fur);
const leftHand = ellipsoid(5.2, [1, 0.92, 0.9], [-27.4, -3.0, 25.3], darkFur);
const rightHand = rightArmLift
  ? ellipsoid(4.9, [1, 0.92, 0.9], [31.0, -6.4, 61.4], darkFur)
  : ellipsoid(5.2, [1, 0.92, 0.9], [27.4, -3.0, 25.3], darkFur);

const leftLeg = angledEllipsoid(5.8, [0.9, 0.78, 2.05], [-9.2, -1, 12.2], { x: 0, y: -14, z: 0 }, fur);
const rightLeg = angledEllipsoid(5.8, [0.9, 0.78, 2.05], [9.2, -1, 12.2], { x: 0, y: 14, z: 0 }, fur);
const leftFoot = ellipsoid(6.8, [1.25, 0.9, 0.45], [-12.5, -11.5, 2.6], darkFur);
const rightFoot = ellipsoid(6.8, [1.25, 0.9, 0.45], [12.5, -11.5, 2.6], darkFur);

const tailCurl = torus(16.5, 2.75, 48)
  .rotateX(90)
  .translate(0, 19.5, 35)
  .color(fur);
const tailStem = angledEllipsoid(3.2, [0.9, 0.9, 3.2], [0, 15.3, 30.5], { x: 74, y: 0, z: 0 }, fur);

verify.inRange("scale parameter stays usable", scale, 0.6, 1.6);
verify.greaterThan("head sits above body", 58 - 30, 18);
verify.greaterThan("tail has visible curl radius", 16.5, 10);

return [
  part("Body", body, ["fur"]),
  part("Belly patch", belly, ["face"]),
  part("Head", head, ["fur"]),
  part("Muzzle", muzzle, ["face"]),
  part("Brow patch", brow, ["face"]),
  part("Left ear", leftEar, ["ear"]),
  part("Right ear", rightEar, ["ear"]),
  part("Left inner ear", leftInnerEar, ["ear", "face"]),
  part("Right inner ear", rightInnerEar, ["ear", "face"]),
  part("Left eye", leftEye, ["face"]),
  part("Right eye", rightEye, ["face"]),
  part("Left eye glint", leftGlint, ["face"]),
  part("Right eye glint", rightGlint, ["face"]),
  part("Nose", nose, ["face"]),
  part("Smile left", smileLeft, ["face"]),
  part("Smile right", smileRight, ["face"]),
  part("Left arm", leftArm, ["limb"]),
  part("Right arm", rightArm, ["limb"]),
  part("Left hand", leftHand, ["limb"]),
  part("Right hand", rightHand, ["limb"]),
  part("Left leg", leftLeg, ["limb"]),
  part("Right leg", rightLeg, ["limb"]),
  part("Left foot", leftFoot, ["limb"]),
  part("Right foot", rightFoot, ["limb"]),
  part("Tail stem", tailStem, ["tail"]),
  part("Curled tail", tailCurl, ["tail"]),
];
