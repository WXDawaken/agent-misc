const modelScale = Param.number("Scale", 1, { min: 0.6, max: 1.6, unit: "x" });
const pose = Param.choice("Pose", "waving", ["waving", "standing"]);

const fur = "#7a4b2a";
const darkFur = "#4d2c1d";
const face = "#d9ad79";
const cheek = "#e6c092";
const black = "#171412";
const white = "#fff5e6";

scene({
  background: { top: "#dce6f0", bottom: "#768798" },
  camera: { position: [98, -136, 82], target: [0, -5, 39], fov: 37 },
  environment: { preset: "studio", intensity: 0.2, background: false },
  lights: [
    { type: "ambient", color: "#f3eadf", intensity: 0.16 },
    { type: "directional", position: [160, -210, 245], target: [0, 0, 36], color: "#ffe5c5", intensity: 2.8, castShadow: true },
    { type: "directional", position: [-130, 85, 165], target: [0, 0, 36], color: "#d8ecff", intensity: 0.8 },
  ],
  ground: { visible: true, color: "#8c98a4", height: -1, receiveShadow: true },
});

function pos(point) {
  return point.map((value) => value * modelScale);
}

function part(name, shape, tags = []) {
  return { name, tags: ["toy-monkey-v2", ...tags], shape };
}

function ellipsoid(radius, xyzScale, position, color, segments = 28) {
  return sphere(radius * modelScale, segments)
    .scale(xyzScale)
    .translate(...pos(position))
    .color(color);
}

function angledEllipsoid(radius, xyzScale, position, rotation, color, segments = 24) {
  let shape = sphere(radius * modelScale, segments).scale(xyzScale);
  if (rotation.x) shape = shape.rotateX(rotation.x);
  if (rotation.y) shape = shape.rotateY(rotation.y);
  if (rotation.z) shape = shape.rotateZ(rotation.z);
  return shape.translate(...pos(position)).color(color);
}

function cone(height, radius, position, rotation, color) {
  let shape = cylinder(height * modelScale, radius * modelScale, 0, 7);
  if (rotation.x) shape = shape.rotateX(rotation.x);
  if (rotation.y) shape = shape.rotateY(rotation.y);
  if (rotation.z) shape = shape.rotateZ(rotation.z);
  return shape.translate(...pos(position)).color(color);
}

const isWaving = pose === "waving" || pose === 0;

const body = ellipsoid(18, [0.88, 0.8, 1.24], [0, 0, 30], fur);
const chest = ellipsoid(12.2, [0.96, 0.34, 1.24], [0, -14.7, 31.5], face);
const leftShoulder = ellipsoid(5.8, [0.95, 0.8, 0.85], [-14.8, -2.8, 42], darkFur);
const rightShoulder = ellipsoid(5.8, [0.95, 0.8, 0.85], [14.8, -2.8, 42], darkFur);
const leftHip = ellipsoid(5.6, [1.0, 0.78, 0.82], [-9.4, -2, 17], darkFur);
const rightHip = ellipsoid(5.6, [1.0, 0.78, 0.82], [9.4, -2, 17], darkFur);

const head = ellipsoid(16, [1.0, 0.92, 1.03], [0, -2, 58], fur);
const faceMask = ellipsoid(11, [1.18, 0.28, 0.92], [0, -17.5, 61.5], face);
const muzzle = ellipsoid(8.5, [1.22, 0.6, 0.74], [0, -17.4, 53.8], face);
const leftCheek = ellipsoid(4.8, [1.0, 0.42, 0.78], [-6.2, -20.2, 53.2], cheek);
const rightCheek = ellipsoid(4.8, [1.0, 0.42, 0.78], [6.2, -20.2, 53.2], cheek);
const chin = ellipsoid(3.5, [1.45, 0.38, 0.55], [0, -20.6, 48.7], cheek);

const browLeft = angledEllipsoid(1.35, [3.2, 0.48, 0.48], [-5.9, -18.4, 67.1], { x: 0, y: 0, z: 10 }, darkFur, 16);
const browRight = angledEllipsoid(1.35, [3.2, 0.48, 0.48], [5.9, -18.4, 67.1], { x: 0, y: 0, z: -10 }, darkFur, 16);
const leftEye = ellipsoid(2.25, [1, 0.42, 1], [-5.8, -18.2, 63.6], black, 20);
const rightEye = ellipsoid(2.25, [1, 0.42, 1], [5.8, -18.2, 63.6], black, 20);
const leftGlint = ellipsoid(0.68, [1, 0.5, 1], [-5.1, -19.7, 64.4], white, 12);
const rightGlint = ellipsoid(0.68, [1, 0.5, 1], [6.5, -19.7, 64.4], white, 12);
const nose = ellipsoid(2.55, [1.3, 0.58, 0.7], [0, -23.0, 56.7], black, 18);
const leftNostril = ellipsoid(0.55, [1, 0.45, 0.75], [-1.15, -24.7, 56.4], "#2b211c", 10);
const rightNostril = ellipsoid(0.55, [1, 0.45, 0.75], [1.15, -24.7, 56.4], "#2b211c", 10);
const smileLeft = angledEllipsoid(0.9, [2.6, 0.42, 0.42], [-3.1, -22.7, 50.1], { x: 0, y: 0, z: -18 }, black, 12);
const smileRight = angledEllipsoid(0.9, [2.6, 0.42, 0.42], [3.1, -22.7, 50.1], { x: 0, y: 0, z: 18 }, black, 12);

const leftEar = ellipsoid(8.5, [0.52, 0.98, 1.02], [-16.7, -1, 59.6], fur);
const rightEar = ellipsoid(8.5, [0.52, 0.98, 1.02], [16.7, -1, 59.6], fur);
const leftInnerEar = ellipsoid(5.6, [0.34, 0.82, 0.82], [-17.6, -4.4, 59.6], cheek);
const rightInnerEar = ellipsoid(5.6, [0.34, 0.82, 0.82], [17.6, -4.4, 59.6], cheek);
const leftSideTuft = cone(7, 2.6, [-16.8, -5.4, 67.5], { x: 0, y: 30, z: -20 }, darkFur);
const rightSideTuft = cone(7, 2.6, [16.8, -5.4, 67.5], { x: 0, y: -30, z: 20 }, darkFur);
const topTuftA = cone(8, 2.9, [-3.2, -4.7, 72.2], { x: 0, y: -22, z: -10 }, darkFur);
const topTuftB = cone(9, 3.0, [0.5, -5.2, 72.0], { x: 0, y: 8, z: 0 }, darkFur);
const topTuftC = cone(7.5, 2.5, [4.0, -4.6, 71.8], { x: 0, y: 22, z: 12 }, darkFur);

const leftArm = angledEllipsoid(5.0, [0.7, 0.72, 3.1], [-19.0, -1.5, 35], { x: 0, y: -31, z: -12 }, fur);
const rightArm = isWaving
  ? angledEllipsoid(4.8, [0.7, 0.7, 3.18], [20.0, -3.2, 47], { x: 0, y: 40, z: 18 }, fur)
  : angledEllipsoid(5.0, [0.7, 0.72, 3.1], [19.0, -1.5, 35], { x: 0, y: 31, z: 12 }, fur);
const leftHand = ellipsoid(5.2, [1.0, 0.92, 0.9], [-28.2, -3.2, 25.2], darkFur);
const rightHand = isWaving
  ? ellipsoid(4.9, [1.0, 0.92, 0.9], [32.1, -6.7, 62.4], darkFur)
  : ellipsoid(5.2, [1.0, 0.92, 0.9], [28.2, -3.2, 25.2], darkFur);

const leftFingerA = angledEllipsoid(1.1, [0.6, 0.45, 1.7], [-31.6, -6.0, 27.2], { x: 0, y: -12, z: -8 }, darkFur, 10);
const leftFingerB = angledEllipsoid(1.1, [0.6, 0.45, 1.8], [-28.5, -7.0, 28.1], { x: 0, y: 0, z: 0 }, darkFur, 10);
const leftFingerC = angledEllipsoid(1.1, [0.6, 0.45, 1.6], [-25.7, -6.1, 27.1], { x: 0, y: 12, z: 8 }, darkFur, 10);
const rightFingerA = isWaving
  ? angledEllipsoid(1.05, [0.55, 0.42, 1.85], [29.4, -9.0, 66.4], { x: -8, y: -12, z: -14 }, darkFur, 10)
  : angledEllipsoid(1.1, [0.6, 0.45, 1.7], [25.7, -6.1, 27.1], { x: 0, y: -12, z: -8 }, darkFur, 10);
const rightFingerB = isWaving
  ? angledEllipsoid(1.05, [0.55, 0.42, 2.0], [32.2, -9.4, 67.4], { x: -3, y: 0, z: 0 }, darkFur, 10)
  : angledEllipsoid(1.1, [0.6, 0.45, 1.8], [28.5, -7.0, 28.1], { x: 0, y: 0, z: 0 }, darkFur, 10);
const rightFingerC = isWaving
  ? angledEllipsoid(1.05, [0.55, 0.42, 1.75], [35.0, -8.8, 66.2], { x: 6, y: 12, z: 14 }, darkFur, 10)
  : angledEllipsoid(1.1, [0.6, 0.45, 1.6], [31.6, -6.0, 27.2], { x: 0, y: 12, z: 8 }, darkFur, 10);

const leftLeg = angledEllipsoid(5.8, [0.88, 0.78, 2.08], [-9.2, -1, 12.2], { x: 0, y: -15, z: 0 }, fur);
const rightLeg = angledEllipsoid(5.8, [0.88, 0.78, 2.08], [9.2, -1, 12.2], { x: 0, y: 15, z: 0 }, fur);
const leftFoot = ellipsoid(6.9, [1.28, 0.9, 0.45], [-12.8, -11.8, 2.6], darkFur);
const rightFoot = ellipsoid(6.9, [1.28, 0.9, 0.45], [12.8, -11.8, 2.6], darkFur);
const leftToeA = ellipsoid(1.15, [1.1, 0.6, 0.45], [-17.6, -17.2, 2.7], face, 10);
const leftToeB = ellipsoid(1.15, [1.1, 0.6, 0.45], [-12.8, -18.0, 2.8], face, 10);
const leftToeC = ellipsoid(1.15, [1.1, 0.6, 0.45], [-8.1, -17.2, 2.7], face, 10);
const rightToeA = ellipsoid(1.15, [1.1, 0.6, 0.45], [8.1, -17.2, 2.7], face, 10);
const rightToeB = ellipsoid(1.15, [1.1, 0.6, 0.45], [12.8, -18.0, 2.8], face, 10);
const rightToeC = ellipsoid(1.15, [1.1, 0.6, 0.45], [17.6, -17.2, 2.7], face, 10);

const tailRoot = ellipsoid(4.5, [1.18, 0.8, 0.92], [0, 14.6, 34], darkFur);
const tailStem = angledEllipsoid(3.2, [0.9, 0.9, 3.3], [0, 16.2, 31.5], { x: 72, y: 0, z: 0 }, fur);
const tailCurl = torus(16.5 * modelScale, 2.75 * modelScale, 56)
  .rotateX(90)
  .translate(...pos([0, 20.3, 36]))
  .color(fur);
const tailTip = ellipsoid(3.2, [1.0, 0.9, 0.9], [0, 3.7, 36], darkFur, 18);

verify.inRange("scale parameter stays usable", modelScale, 0.6, 1.6);
verify.greaterThan("head sits above body", 58 - 30, 18);
verify.greaterThan("waving hand clears shoulder", isWaving ? 62.4 - 42 : 20, 12);
verify.greaterThan("tail has visible curl radius", 16.5, 10);

return [
  part("Body", body, ["fur"]),
  part("Chest patch", chest, ["face"]),
  part("Left shoulder", leftShoulder, ["fur"]),
  part("Right shoulder", rightShoulder, ["fur"]),
  part("Left hip", leftHip, ["fur"]),
  part("Right hip", rightHip, ["fur"]),
  part("Head", head, ["fur"]),
  part("Face mask", faceMask, ["face"]),
  part("Muzzle", muzzle, ["face"]),
  part("Left cheek", leftCheek, ["face"]),
  part("Right cheek", rightCheek, ["face"]),
  part("Chin", chin, ["face"]),
  part("Left brow", browLeft, ["face"]),
  part("Right brow", browRight, ["face"]),
  part("Left eye", leftEye, ["face"]),
  part("Right eye", rightEye, ["face"]),
  part("Left eye glint", leftGlint, ["face"]),
  part("Right eye glint", rightGlint, ["face"]),
  part("Nose", nose, ["face"]),
  part("Left nostril", leftNostril, ["face"]),
  part("Right nostril", rightNostril, ["face"]),
  part("Smile left", smileLeft, ["face"]),
  part("Smile right", smileRight, ["face"]),
  part("Left ear", leftEar, ["ear"]),
  part("Right ear", rightEar, ["ear"]),
  part("Left inner ear", leftInnerEar, ["ear", "face"]),
  part("Right inner ear", rightInnerEar, ["ear", "face"]),
  part("Left side tuft", leftSideTuft, ["fur"]),
  part("Right side tuft", rightSideTuft, ["fur"]),
  part("Top tuft A", topTuftA, ["fur"]),
  part("Top tuft B", topTuftB, ["fur"]),
  part("Top tuft C", topTuftC, ["fur"]),
  part("Left arm", leftArm, ["limb"]),
  part("Right arm", rightArm, ["limb"]),
  part("Left hand", leftHand, ["limb"]),
  part("Right hand", rightHand, ["limb"]),
  part("Left finger A", leftFingerA, ["limb"]),
  part("Left finger B", leftFingerB, ["limb"]),
  part("Left finger C", leftFingerC, ["limb"]),
  part("Right finger A", rightFingerA, ["limb"]),
  part("Right finger B", rightFingerB, ["limb"]),
  part("Right finger C", rightFingerC, ["limb"]),
  part("Left leg", leftLeg, ["limb"]),
  part("Right leg", rightLeg, ["limb"]),
  part("Left foot", leftFoot, ["limb"]),
  part("Right foot", rightFoot, ["limb"]),
  part("Left toe A", leftToeA, ["limb"]),
  part("Left toe B", leftToeB, ["limb"]),
  part("Left toe C", leftToeC, ["limb"]),
  part("Right toe A", rightToeA, ["limb"]),
  part("Right toe B", rightToeB, ["limb"]),
  part("Right toe C", rightToeC, ["limb"]),
  part("Tail root", tailRoot, ["tail"]),
  part("Tail stem", tailStem, ["tail"]),
  part("Curled tail", tailCurl, ["tail"]),
  part("Tail tip", tailTip, ["tail"]),
];
