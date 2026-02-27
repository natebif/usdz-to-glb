const express = require("express");
const multer = require("multer");
const { execSync } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");
const app = express();
const upload = multer({ dest: "/tmp/" });

// Debug: log missing shared libraries on startup
try {
  const missing = execSync('ldd /opt/blender-4.0.2-linux-x64/4.0/python/lib/python3.10/lib-dynload/*.so 2>&1 | grep "not found"').toString();
  console.log("Missing libs:\n", missing);
} catch (e) {
  console.log("ldd check:", e.message?.slice(-500));
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

app.listen(process.env.PORT || 3000, () => console.log("USDZ to GLB converter running"));

