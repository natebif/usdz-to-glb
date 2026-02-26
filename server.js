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

  fs.renameSync(inputPath, usdzPath);

  try {
    // Call Python converter directly
    execSync(`python3 convert.py ${usdzPath} ${glbPath}`, {
      stdio: "inherit",
      timeout: 120000,
    });

    if (!fs.existsSync(glbPath)) {
      throw new Error("GLB not created");
    }

    res.setHeader("Content-Type", "model/gltf-binary");
    res.send(fs.readFileSync(glbPath));
  } catch (err) {
    res.status(500).json({ error: err.message });
  } finally {
    try { fs.unlinkSync(usdzPath); } catch {}
    try { fs.unlinkSync(glbPath); } catch {}
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log("USDZ → GLB converter running");
});
