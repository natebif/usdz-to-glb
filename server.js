const express = require("express");
const multer = require("multer");
const { execSync } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");

const app = express();
const upload = multer({ dest: "/tmp/" });

app.post("/convert", upload.single("file"), (req, res) => {
  console.log("Received file:", req.file ? req.file.originalname : "none", "size:", req.file ? req.file.size : 0, "bytes");
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });

  var id = crypto.randomUUID();
  var usdzPath = "/tmp/" + id + ".usdz";
  var glbPath = "/tmp/" + id + ".glb";
  fs.renameSync(req.file.path, usdzPath);

  try {
    var output = execSync(
      'blender --background --python convert.py -- "' + usdzPath + '" "' + glbPath + '"',
      { encoding: "utf-8", timeout: 120000 }
    );
    console.log("Blender output:", output.slice(-2000));

    if (!fs.existsSync(glbPath)) {
      throw new Error("GLB file was not created. Blender output: " + output.slice(-1000));
    }

    // Extract all BBOX lines from Blender output
    var bboxLines = output.split("\n").filter(function(l) { return l.indexOf("BBOX") !== -1; }).join(" | ");
    var vertsLines = output.split("\n").filter(function(l) { return l.indexOf("VERTS") !== -1; }).join(" | ");
    res.setHeader("X-Verts-Info", encodeURIComponent(vertsLines || "no VERTS found"));
    res.setHeader("Content-Type", "model/gltf-binary");
    res.setHeader("X-Bbox-Info", encodeURIComponent(bboxLines || "no BBOX found"));
    res.setHeader("X-Blender-Log", encodeURIComponent(output.slice(-1500)));
    res.send(fs.readFileSync(glbPath));
  } catch (err) {
    var stderr = (err.stderr && err.stderr.toString()) || "";
    var stdout = (err.stdout && err.stdout.toString()) || "";
    var msg = err.message + (stderr ? " STDERR: " + stderr.slice(-500) : "") + (stdout ? " STDOUT: " + stdout.slice(-500) : "");
    console.error("Conversion error:", msg);
    res.status(500).json({ error: msg });
  } finally {
    try { fs.unlinkSync(usdzPath); } catch (e) {}
    try { fs.unlinkSync(glbPath); } catch (e) {}
  }
});

app.listen(process.env.PORT || 3000, function() {
  console.log("USDZ to GLB converter running.");
});

