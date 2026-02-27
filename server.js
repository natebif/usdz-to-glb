const express = require("express");
const multer = require("multer");
const { execSync } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
const upload = multer({ dest: "/tmp/" });

// Debug: check missing shared libs for USD .so files
try {
  const ldd = execSync('ldd /opt/blender-4.0.2-linux-x64/4.0/python/lib/python3.10/site-packages/pxr/Usd/_usd.so 2>&1 | grep "not found"').toString();
  console.log("Missing libs for _usd.so:\n", ldd);
} catch (e) {
  const out = e.stdout?.toString?.() || e.message?.slice(-500);
  console.log("ldd _usd.so result:", out);
}

try {
  const ldd2 = execSync('ldd /opt/blender-4.0.2-linux-x64/lib/libusd_ms.so 2>&1 | grep "not found"').toString();
  console.log("Missing libs for libusd_ms.so:\n", ldd2);
} catch (e) {
  const out = e.stdout?.toString?.() || e.message?.slice(-500);
  console.log("ldd libusd_ms.so result:", out);
}

// Also check what io_scene_usd addon looks like
try {
  const addon = execSync('find /opt/blender* -path "*/addons/io_scene_usd*" -o -path "*/scripts/startup/*usd*" 2>&1 | head -10').toString();
  console.log("io_scene_usd addon files:\n", addon);
} catch (e) {
  console.log("addon search failed:", e.message?.slice(-500));
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

