import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import * as THREE from "three";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

class NodeFileReader {
  result = null;
  onloadend = null;
  onerror = null;

  readAsArrayBuffer(blob) {
    blob.arrayBuffer()
      .then((arrayBuffer) => {
        this.result = arrayBuffer;
        this.onloadend?.({ target: this });
      })
      .catch((error) => this.onerror?.(error));
  }

  readAsDataURL(blob) {
    blob.arrayBuffer()
      .then((arrayBuffer) => {
        const base64 = Buffer.from(arrayBuffer).toString("base64");
        this.result = `data:${blob.type || "application/octet-stream"};base64,${base64}`;
        this.onloadend?.({ target: this });
      })
      .catch((error) => this.onerror?.(error));
  }
}

globalThis.FileReader ??= NodeFileReader;

const args = process.argv.slice(2);
const preserveUp = args.includes("--preserve-up");
const [inputPath, outputPath] = args.filter((arg) => !arg.startsWith("--"));
if (!inputPath || !outputPath) {
  console.error("Usage: node scripts/stl-to-glb.mjs input.stl output.glb [--preserve-up]");
  process.exit(2);
}

const input = path.resolve(inputPath);
const output = path.resolve(outputPath);
const stlBytes = await readFile(input);
const arrayBuffer = stlBytes.buffer.slice(stlBytes.byteOffset, stlBytes.byteOffset + stlBytes.byteLength);
const geometry = new STLLoader().parse(arrayBuffer);
geometry.computeVertexNormals();

const material = new THREE.MeshStandardMaterial({
  color: 0x53616f,
  metalness: 0.08,
  roughness: 0.72
});

const mesh = new THREE.Mesh(geometry, material);
mesh.name = path.basename(input, path.extname(input));
if (!preserveUp) {
  mesh.rotateX(-Math.PI / 2);
}

const scene = new THREE.Scene();
scene.name = `${mesh.name}-converted-from-stl`;
scene.add(mesh);

const glb = await new Promise((resolve, reject) => {
  new GLTFExporter().parse(
    scene,
    resolve,
    reject,
    {
      binary: true,
      onlyVisible: true,
      trs: false
    }
  );
});

if (!(glb instanceof ArrayBuffer)) {
  throw new Error("GLTFExporter did not return binary GLB output");
}

await writeFile(output, Buffer.from(glb));
console.log(`Wrote ${output}`);
