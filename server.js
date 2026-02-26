const express = require('express');
const multer = require('multer');
const { execSync } = require('child_process');
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const app = express();
const upload = multer({ dest: '/tmp/uploads/' });

app.post('/convert', upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });

  const id = crypto.randomUUID();
  const inputPath = req.file.path;
  const usdzPath = `/tmp/${id}.usdz`;
  const glbPath = `/tmp/${id}.glb`;

  fs.renameSync(inputPath, usdzPath);

  try {
    // Call Python converter
    const { execSync } = require("child_process");
execSync(`blender --background --python convert.py -- ${usdzPath} ${glbPath}`, { timeout: 120000 });

);


    if (!fs.existsSync(glbPath)) throw new Error('GLB not created');

    res.setHeader('Content-Type', 'model/gltf-binary');
    res.send(fs.readFileSync(glbPath));
  } catch (err) {
    res.status(500).json({ error: err.message });
  } finally {
    [usdzPath, glbPath].forEach(f => { try { fs.unlinkSync(f); } catch {} });
  }
});

app.listen(process.env.PORT || 3000, () => console.log('USDZ → GLB converter ready'));
