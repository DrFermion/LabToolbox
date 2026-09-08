// count_livedead.ijm - LIVE/DEAD adaptive-threshold counting (ImageJ)
// Usage (headless): fiji-windows-x64.exe --headless -macro count_livedead.ijm "<argfile.txt>"
// argfile (UTF-8, 3 lines): line1=inputDir  line2=outputCSV  line3=qcDir (may be empty)
//   Chinese paths OK in argfile, NOT on CLI
// Method == LabToolbox Python pipeline: bg-mode+40 threshold -> size filter 3-500 px
// Channel-trap rule: named channel (g->green, r->red) with max<30 falls back to brightest channel
// QC mode: when qcDir non-empty, each counted image is saved as <stem>_qc.png with every
//   counted particle circled (magenta) and numbered (white), for troubleshooting.
// NOTE: keep this macro file pure ASCII (macro files are not read as UTF-8)

s = File.openAsString(getArgument());
lines = split(s, "\n");
if (lines.length < 2) { print("ARGS FILE ERROR"); exit(); }
dir = replace(lines[0], "\r", "");
out = replace(lines[1], "\r", "");
if (endsWith(out, "\r")) out = substring(out, 0, lengthOf(out) - 1);
qcDir = "";
if (lines.length >= 3) {
  qcDir = replace(lines[2], "\r", "");
  if (endsWith(qcDir, "\r")) qcDir = substring(qcDir, 0, lengthOf(qcDir) - 1);
}
if (!endsWith(dir, "/") && !endsWith(dir, "\\")) dir = dir + "/";
if (lengthOf(qcDir) > 0 && !endsWith(qcDir, "/") && !endsWith(qcDir, "\\")) qcDir = qcDir + "/";

// highest non-zero histogram bin = channel max
function chanMax() {
  getHistogram(hvals, hcounts, 256);
  for (m = 255; m >= 0; m--) { if (hcounts[m] > 0) return m; }
  return 0;
}

// histogram mode = background level
function bgMode() {
  getHistogram(hvals, hcounts, 256);
  best = 0; bi = 0;
  for (i = 0; i < 256; i++) { if (hcounts[i] > best) { best = hcounts[i]; bi = i; } }
  return bi;
}

File.append("filename,chan_used,bg,thresh,count,roi_count", out);
list = getFileList(dir);
run("Clear Results");
roiManager("reset");
for (i = 0; i < list.length; i++) {
  f = list[i];
  if (!endsWith(toLowerCase(f), ".tif")) continue;
  open(dir + f);
  run("Set Scale...", "distance=0 known=0 pixel");  // strip Image-Pro fake calibration (inch/px) or Analyze Particles size filter breaks
  title = getTitle();
  if (title != f) { close(); continue; }
  chanUsed = "full";
  if (bitDepth() == 24) {         // RGB
    run("Split Channels");
    rT = title + " (red)"; gT = title + " (green)"; bT = title + " (blue)";
    selectWindow(rT); mr = chanMax();
    selectWindow(gT); mg = chanMax();
    selectWindow(bT); mb = chanMax();
    low = toLowerCase(f);
    isG = indexOf(low, "-g") >= 0;
    if (isG) { named = gT; nm = mg; } else { named = rT; nm = mr; }
    if (nm < 30) {
      mx = maxOf(mr, maxOf(mg, mb));
      if (mx == mr) named = rT;
      else if (mx == mg) named = gT;
      else named = bT;
      chanUsed = "auto-bright";
    } else {
      if (isG) chanUsed = "green"; else chanUsed = "red";
    }
    selectWindow(rT); if (rT != named) close();
    selectWindow(gT); if (gT != named) close();
    selectWindow(bT); if (bT != named) close();
    selectWindow(named);
  } else {
    chanUsed = "gray";
  }
  bg = bgMode();
  th = bg + 40;
  setThreshold(th, 255);
  run("Convert to Mask");
  run("Analyze Particles...", "size=3-500 show=Nothing add");
  cnt = nResults;
  rc = roiManager("count");
  File.append(f + "," + chanUsed + "," + bg + "," + th + "," + cnt + "," + rc, out);
  // ---- QC: circle + number every counted particle on the source channel ----
  if (lengthOf(qcDir) > 0 && cnt > 0 && roiManager("count") > 0) {
    selectWindow(named);
    run("Duplicate...", "title=qc_view");
    run("Green");                              // LUT: display as green fluorescence
    run("RGB Color");
    roiManager("Set Color", "magenta");
    setColor(255, 0, 255);                    // magenta numbers (drawn on pixels)
    setFont("SansSerif", 11);
    for (r = 0; r < roiManager("count"); r++) {
      roiManager("select", r);
      Overlay.addSelection();
      getSelectionBounds(qx, qy, qw, qh);
      drawString(r + 1, qx + qw / 2, qy + qh / 2 + 5);
    }
    run("Flatten");                            // flatten overlay (circles) into image
    qtitle = getTitle();                       // flatten window is active
    stem = substring(f, 0, lastIndexOf(f, "."));
    saveAs("PNG", qcDir + stem + "_qc.png");
    close();                                   // close flatten result (qc_view closed by loop)
  }
  run("Clear Results");
  roiManager("reset");
  for (k = 0; k < 20; k++) { if (nImages == 0) break; close(); }   // close all windows of this file (bounded)
}
print("BATCH DONE: " + list.length + " files -> " + out);
exit();
