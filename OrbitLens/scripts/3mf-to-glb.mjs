import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { DOMParser as XmlDomParser } from "@xmldom/xmldom";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";
import { ThreeMFLoader } from "three/examples/jsm/loaders/3MFLoader.js";

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
class QueryDomParser {
  parseFromString(source, mimeType) {
    return attachQuerySelectors(new XmlDomParser().parseFromString(source, mimeType));
  }
}

function attachQuerySelectors(node) {
  if (!node || typeof node !== "object") {
    return node;
  }

  if (typeof node.getElementsByTagName === "function") {
    node.querySelectorAll ??= function querySelectorAll(selector) {
      return selectDescendants(this, selector);
    };
    node.querySelector ??= function querySelector(selector) {
      return this.querySelectorAll(selector)[0] ?? null;
    };
  }

  for (const child of Array.from(node.childNodes ?? [])) {
    attachQuerySelectors(child);
  }

  return node;
}

function selectDescendants(root, selector) {
  let current = [root];
  for (const tagName of selector.trim().split(/\s+/u)) {
    current = current.flatMap((node) => descendantsByLocalName(node, tagName));
  }
  return current;
}

function descendantsByLocalName(root, tagName) {
  const matches = [];
  const visit = (node) => {
    for (const child of Array.from(node.childNodes ?? [])) {
      const localName = child.localName ?? String(child.nodeName ?? "").split(":").pop();
      if (localName?.toLowerCase() === tagName.toLowerCase()) {
        matches.push(child);
      }
      visit(child);
    }
  };
  visit(root);
  return matches;
}

globalThis.DOMParser ??= QueryDomParser;

const args = process.argv.slice(2);
const preserveUp = args.includes("--preserve-up");
const [inputPath, outputPath] = args.filter((arg) => !arg.startsWith("--"));
if (!inputPath || !outputPath) {
  console.error("Usage: node scripts/3mf-to-glb.mjs input.3mf output.glb [--preserve-up]");
  process.exit(2);
}

const input = path.resolve(inputPath);
const output = path.resolve(outputPath);
const fileBytes = await readFile(input);
const arrayBuffer = fileBytes.buffer.slice(fileBytes.byteOffset, fileBytes.byteOffset + fileBytes.byteLength);
const group = new ThreeMFLoader().parse(arrayBuffer);
group.name = `${path.basename(input, path.extname(input))}-converted-from-3mf`;
if (!preserveUp) {
  group.rotateX(-Math.PI / 2);
}

const glb = await new Promise((resolve, reject) => {
  new GLTFExporter().parse(
    group,
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
