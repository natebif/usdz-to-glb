const express = require('express');
const multer = require('multer');
const { execSync } = require('child_process');
const fs = require('fs');
const crypto = require('crypto');

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
    execSync(`blender --background --python-expr "
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_open(filepath='${usdzPath}')
bpy.ops.export_scene.gltf(filepath='${glbPath}', export_format='GLB')
"`, { timeout: 120000 });
    
    if (!fs.existsSync(glbPath)) throw new Error('GLB not created');
    
    res.setHeader('Content-Type', 'model/gltf-binary');
    res.send(fs.readFileSync(glbPath));
  } catch (err) {
    res.status(500).json({ error: err.message });
  } finally {
    [usdzPath, glbPath].forEach(f => { try { fs.unlinkSync(f); } catch {} });
  }
});

app.listen(process.env.PORT || 3000, () => console.log('Converter ready'));
