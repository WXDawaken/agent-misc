import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { PNG } from "pngjs";

export function dataUrlToPngBuffer(dataUrl: string): Buffer {
  const match = /^data:image\/png;base64,(?<data>.+)$/u.exec(dataUrl);
  if (!match?.groups?.data) {
    throw new Error("Renderer did not return a PNG data URL");
  }
  return Buffer.from(match.groups.data, "base64");
}

export async function writePngFromDataUrl(dataUrl: string, imagePath: string): Promise<{ nonblank: boolean }> {
  const buffer = dataUrlToPngBuffer(dataUrl);
  await mkdir(path.dirname(imagePath), { recursive: true });
  await writeFile(imagePath, buffer);
  return { nonblank: isNonblankPng(buffer) };
}

export function isNonblankPng(buffer: Buffer): boolean {
  const png = PNG.sync.read(buffer);
  let first: string | undefined;
  let differingPixels = 0;
  let opaquePixels = 0;

  for (let offset = 0; offset < png.data.length; offset += 4) {
    const alpha = png.data[offset + 3];
    if (alpha > 0) {
      opaquePixels += 1;
    }
    const current = `${png.data[offset]},${png.data[offset + 1]},${png.data[offset + 2]},${alpha}`;
    if (first === undefined) {
      first = current;
    } else if (first !== current) {
      differingPixels += 1;
      if (differingPixels > 16 && opaquePixels > 16) {
        return true;
      }
    }
  }

  return false;
}

export async function writeContactSheet(imagePaths: string[], outputPath: string, columns = 3, padding = 12): Promise<void> {
  if (imagePaths.length === 0) {
    throw new Error("Cannot create a contact sheet without images");
  }

  const images = await Promise.all(imagePaths.map(async (imagePath) => PNG.sync.read(await readFile(imagePath))));
  const tileWidth = Math.max(...images.map((image) => image.width));
  const tileHeight = Math.max(...images.map((image) => image.height));
  const rows = Math.ceil(images.length / columns);
  const sheet = new PNG({
    width: columns * tileWidth + (columns + 1) * padding,
    height: rows * tileHeight + (rows + 1) * padding
  });

  sheet.data.fill(255);
  for (let index = 0; index < images.length; index += 1) {
    const image = images[index];
    const col = index % columns;
    const row = Math.floor(index / columns);
    const x = padding + col * (tileWidth + padding);
    const y = padding + row * (tileHeight + padding);
    PNG.bitblt(image, sheet, 0, 0, image.width, image.height, x, y);
  }

  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, PNG.sync.write(sheet));
}

