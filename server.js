const express = require("express");
const multer = require("multer");
const { execSync } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
const upload = multer({ dest: "/tmp/" });

// Debug: find Blender's Python and check for missing libs
try {
  const find = execSync('find /opt/blender* -name "*.so" -path "*/lib-dynload/*" 2>&1 | head -20').toString();
  console.log("Found .so files:\n", find);
} catch (e) {
  console.log("find failed:", e.message?.slice(-500));
}

try {
  const blenderPath = execSync('which blender || find /opt -name blender -type f 2>&1 | head -5').toString();
  console.log("Blender binary:", blenderPath);
} catch (e) {
  console.log("Blender location failed:", e.message?.slice(-500));
}

try {
  const pythonLibs = execSync('find /opt/blender* -name "io_scene_usd" -o -name "*usd*" 2>&1 | head -20').toString();
  console.log("USD-related files:\n", pythonLibs);
} catch (e) {
  console.log("USD search failed:", e.message?.slice(-500));
}

app.post("/convert", upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });

  const id = crypto.randomUUID();
  const usdzPath = `/tmp/${id}.usdz`;
  const glbPath = `/tmp/${id}.glb`;

  fs.renameSync(req.file.path, usdzPath);

  try {
    const output = execSync(
      `blender --background --python convert.py -- "${usdzPath}" "${glbPath}"`,
      { encoding: "utf-8", timeout: 120000 }
    );
    console.log("Blender output:", output.slice(-2000));

    if (!fs.existsSync(glbPath)) {
      throw new Error("GLB file was not created. Blender output: " + output.slice(-1000));
    }

    res.setHeader("Content-Type", "model/gltf-binary");
    res.send(fs.readFileSync(glbPath));
  } catch (err) {
    const stderr = err.stderr?.toString?.() || "";
    const stdout = err.stdout?.toString?.() || "";
    const msg = err.message + (stderr ? ` STDERR: ${stderr.slice(-500)}` : "") + (stdout ? ` STDOUT: ${stdout.slice(-500)}` : "");
    console.error("Conversion error:", msg);
    res.status(500).json({ error: msg });
  } finally {
    try { fs.unlinkSync(usdzPath); } catch {}
    try { fs.unlinkSync(glbPath); } catch {}
  }
});

app.listen(process.env.PORT || 3000, () => console.log("USDZ to GLB converter running."));


