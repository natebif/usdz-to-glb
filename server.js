const express = require("express");
const multer = require("multer");
const { execSync } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
const upload = multer({ dest: "/tmp/" });

app.post("/convert", upload.single("file"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const id = crypto.randomUUID();
  const inputPath = req.file.path;
  const usdzPath = `/tmp/${id}.usdz`;
  const glbPath = `/tmp/${id}.glb`;

  // Rename uploaded temp file to proper .usdz
  fs.renameSync(inputPath, usdzPath);

  try {
    console.log("Starting Blender conversion...");
    console.log("Input:", usdzPath);
    console.log("Output:", glbPath);

    // Run Blender via CLI and capture stdout/stderr
    try {
      execSync(
        `blender --background --python convert.py -- "${usdzPath}" "${glbPath}"`,
        { stdio: "pipe", timeout: 120000 }
      );
    } } catch (blenderErr) {
  const stderr = blenderErr.stderr?.toString() || '';
  const stdout = blenderErr.stdout?.toString() || '';
  console.error("STDERR:", stderr);
  console.error("STDOUT:", stdout);
  throw new Error(`Blender failed: ${stderr || stdout}`);
}

    if (!fs.existsSync(glbPath)) {
      throw new Error("GLB file was not created");
    }

    console.log("Conversion successful");

    res.setHeader("Content-Type", "model/gltf-binary");
    res.send(fs.readFileSync(glbPath));

  } catch (err) {
    console.error("Conversion error:", err);
    res.status(500).json({ error: err.message });
  } finally {
    try { fs.unlinkSync(usdzPath); } catch {}
    try { fs.unlinkSync(glbPath); } catch {}
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log("USDZ → GLB converter running");
});
