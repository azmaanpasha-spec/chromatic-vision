// Builds the printed mini-project report: report/Chromatic_Vision_Project_Report.docx
// Usage: npm install docx  &&  node scripts/build_report_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, BorderStyle, ShadingType, PageBreak, Header, Footer, PageNumber, NumberFormat,
  TableOfContents, LevelFormat, VerticalAlign, TabStopType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");  // project root
const PF = ROOT + "/report/figures/print/";
const FG = ROOT + "/report/figures/";
const SS = ROOT + "/report/screenshots/";
const OUT = ROOT + "/report/Chromatic_Vision_Project_Report.docx";

const FONT = "Times New Roman";
const CONTENT_W = 8666; // A4 width 11906 - left 1800 - right 1440 (DXA)
const MAX_PX = 570;     // usable width in px at 96 dpi

// ---------------------------------------------------------------- helpers
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
const runs = (text, opts = {}) => {
  // supports **bold** segments
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) =>
    t.startsWith("**") ? new TextRun({ text: t.slice(2, -2), bold: true, ...opts }) : new TextRun({ text: t, ...opts }));
};
const P = (text, opts = {}) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 360 }, ...opts, children: runs(text),
});
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
let listCounter = 0;
const bullets = (items) => items.map((t) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 60, line: 340 }, children: runs(t),
}));
const numbered = (items) => {
  const ref = "num" + (++listCounter);
  numberingConfigs.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] });
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 60, line: 340 }, children: runs(t) }));
};
const numberingConfigs = [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
  alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }];

let figNo = {};
function figure(file, caption, chapter, maxW = MAX_PX, maxH = 620) {
  figNo[chapter] = (figNo[chapter] || 0) + 1;
  const { w, h } = pngSize(file);
  let width = Math.min(maxW, w), height = Math.round(h * width / w);
  if (height > maxH) { height = maxH; width = Math.round(w * height / h); }
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width, height },
        altText: { title: caption, description: caption, name: path.basename(file) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
      children: [new TextRun({ text: `Figure ${chapter}.${figNo[chapter]}: `, bold: true, size: 22 }),
                 new TextRun({ text: caption, italics: true, size: 22 })] }),
  ];
}
let tabNo = {};
const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(caption, chapter, headers, rows, widths) {
  const keep = rows.length <= 10;
  tabNo[chapter] = (tabNo[chapter] || 0) + 1;
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, header, w, last) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: header ? { fill: "D9E2F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ keepNext: keep && !last, keepLines: true, spacing: { line: 260 }, alignment: header ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: runs(String(text), { size: 21, bold: header || undefined }) })],
  });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: `Table ${chapter}.${tabNo[chapter]}: `, bold: true, size: 22 }),
                 new TextRun({ text: caption, italics: true, size: 22 })] }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, true, widths[i])) }),
             ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, false, widths[i], ri === rows.length - 1)) }))] }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}
function code(lines) {
  return lines.map((l, i) => new Paragraph({
    shading: { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" }, keepLines: true, keepNext: i < lines.length - 1,
    spacing: { line: 240, after: 0, before: i === 0 ? 120 : 0 }, indent: { left: 200, right: 200 },
    children: [new TextRun({ text: l || " ", font: "Courier New", size: 18 })],
  })).concat([new Paragraph({ spacing: { after: 160 }, children: [] })]);
}
const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [] }));
const center = (text, opts = {}, after = 120) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after },
  children: [new TextRun({ text, ...opts })] });

// ---------------------------------------------------------------- front matter
const cover = [
  ...blank(3),
  center("A MINI-PROJECT REPORT ON", { size: 26, bold: true }, 408),
  center("CHROMATIC VISION", { size: 48, bold: true, color: "1F3864" }, 204),
  center("Intelligent Color Detection and Object Tracking", { size: 30, bold: true }, 68),
  center("Using Image Processing Techniques", { size: 30, bold: true }, 612),
  center("Submitted in partial fulfilment of the requirements for the course", { size: 24, italics: true }, 102),
  center("IMAGE AND VIDEO ANALYTICS", { size: 26, bold: true }, 102),
  center("of", { size: 24, italics: true }, 102),
  center("BACHELOR OF TECHNOLOGY", { size: 26, bold: true }, 816),
  center("Submitted by", { size: 24, italics: true }, 136),
  center("Name: ______________________________", { size: 24 }, 102),
  center("Roll No.: ____________________________", { size: 24 }, 816),
  center("Under the guidance of", { size: 24, italics: true }, 136),
  center("______________________________", { size: 24 }, 68),
  center("(Designation)", { size: 22 }, 1020),
  center("DEPARTMENT OF ______________________________", { size: 24, bold: true }, 102),
  center("______________________________ (Name of the Institute)", { size: 24, bold: true }, 102),
  center("Academic Year 20___ – 20___", { size: 24 }, 102),
];

const certificate = [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { before: 600, after: 480 },
    children: [new TextRun({ text: "CERTIFICATE", bold: true, size: 32, underline: {} })] }),
  P("This is to certify that the mini-project report entitled **“Chromatic Vision – Intelligent Color Detection and Object Tracking Using Image Processing Techniques”** is a bonafide record of the work carried out by **______________________** (Roll No. **____________**) in partial fulfilment of the requirements for the course **Image and Video Analytics** of the Bachelor of Technology programme during the academic year 20___ – 20___.", { spacing: { after: 240, line: 420 } }),
  ...blank(5),
  new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }], children: [
    new TextRun({ text: "Signature of the Guide", bold: true }), new TextRun({ text: "\tSignature of the Head of Department", bold: true })] }),
  new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }], spacing: { after: 600 }, children: [
    new TextRun("Name: ____________________"), new TextRun("\tName: ____________________")] }),
  ...blank(2),
  new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: CONTENT_W }], children: [
    new TextRun({ text: "Internal Examiner", bold: true }), new TextRun({ text: "\tExternal Examiner", bold: true })] }),
  ...blank(2),
  new Paragraph({ children: [new TextRun("Date: ______________")] }),
  new Paragraph({ children: [new TextRun("Place: ______________")] }),
];

const abstract = [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360 },
    children: [new TextRun({ text: "ABSTRACT", bold: true, size: 32 })] }),
  P("Colour is one of the simplest and most reliable visual cues for locating objects in a scene. This project presents **Chromatic Vision**, a web-based application that detects objects of a chosen colour in images and videos, measures them, and tracks them across video frames using only classical image processing techniques."),
  P("Each image or video frame is converted from the BGR colour space to the HSV colour space. A binary mask of the target colour is produced with cv2.inRange(); red is handled with two hue ranges because it lies at both ends of the hue circle. The mask is cleaned using morphological opening and closing, and individual objects are identified through contour analysis, which gives a bounding box, area and centroid for every object. For videos, a centroid-based tracker links detections between consecutive frames and keeps object identities through short occlusions."),
  P("The application is developed in Python with OpenCV, NumPy and Streamlit, and provides interactive analytics using Plotly and Matplotlib. It was evaluated on a purpose-built synthetic dataset with exactly known ground truth. The detected object counts matched the ground truth for every colour tested, neutral (white, grey, black) objects were never falsely detected, and both tracked objects in the sample video kept their identities for all 200 frames, including a 9-frame occlusion. The average processing time was about 9–10 ms per 640×360 frame on a desktop CPU. The system was verified with 34 automated unit tests and 23 automated browser-based checks, all of which passed."),
  new Paragraph({ spacing: { before: 240 }, children: [new TextRun({ text: "Keywords: ", bold: true }),
    new TextRun({ text: "HSV colour space, colour segmentation, morphological operations, contour detection, centroid tracking, OpenCV, Streamlit.", italics: true })] }),
];

const toc = [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 },
    children: [new TextRun({ text: "TABLE OF CONTENTS", bold: true, size: 32 })] }),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
];

// ---------------------------------------------------------------- chapters
const ch1 = [
  H1("1. INTRODUCTION"),
  H2("1.1 Project Overview"),
  P("Image and video analytics is concerned with automatically extracting meaningful information from visual data. Among all visual features, colour is one of the easiest to compute and one of the most useful in practice: fruit sorting, counting coloured components, following a ball in a sports clip or tracking a coloured marker on a robot all depend on it. Deep-learning detectors are powerful, but they need large labelled datasets, long training and usually a GPU, and their decisions are hard to explain. When the main distinguishing property of an object is its colour, classical colour segmentation is faster, fully transparent and requires no training."),
  P("**Chromatic Vision** packages this classical pipeline into an easy-to-use web application. The user uploads an image or a video (or loads a bundled sample), selects a target colour from a palette or defines a custom HSV range, and the system returns:"),
  ...bullets([
    "a binary segmentation mask of the selected colour and the segmented image,",
    "the bounding box, area and centroid of every detected object, with the object count,",
    "for videos, a processed video in which each object carries a tracking ID and a motion trail,",
    "analytics charts computed from the actual results (colour distribution, object areas, detections per frame, processing time, trajectories),",
    "downloadable processed images, masks, videos and CSV data.",
  ]),
  P("Every intermediate stage of the pipeline (HSV conversion, threshold mask, erosion, dilation, opening, closing and the final detections) is displayed in the application, so the project also works as a visual teaching aid for the topics of the Image and Video Analytics course."),
  H2("1.2 Scope of the Project"),
  ...bullets([
    "Colour-based detection of objects in still images (JPG, JPEG, PNG).",
    "Frame-by-frame colour detection and multi-object tracking in videos (MP4, AVI, MOV).",
    "Six predefined colours (red, orange, yellow, green, blue, purple) and a custom HSV range mode.",
    "Visual analytics, session statistics and export of results.",
    "Runs completely offline on a normal computer: no IoT hardware, cloud services, paid APIs or GPU.",
  ]),
  H2("1.3 Organisation of the Report"),
  P("Chapter 2 states the problem and objectives. Chapter 3 describes the methodology and the image processing techniques used. Chapter 4 presents the system (model) architecture. Chapter 5 gives the dataset details. Chapter 6 explains the implementation, Chapter 7 presents the results, Chapter 8 contains the application screenshots and Chapter 9 concludes the report."),
];

const ch2 = [
  H1("2. PROBLEM STATEMENT AND OBJECTIVES"),
  H2("2.1 Problem Statement"),
  P("Manually locating, counting and following coloured objects in images and videos is slow, subjective and does not scale. Simple approaches that threshold the raw RGB values are unreliable, because a change in illumination (a shadow, a highlight or a darker scene) changes all three RGB channels together, so the same object may fall outside a fixed RGB threshold. Basic classroom scripts usually display a single OpenCV window, have no way to tune parameters, give no measurements or analytics, and crash on invalid input."),
  P("**The problem addressed by this project is therefore:** to design and implement a reliable, explainable and easy-to-use system that (i) segments a user-selected colour robustly under normal lighting variation, (ii) removes noise and fills holes in the segmented regions, (iii) separates the result into individual objects and measures each one, (iv) maintains a consistent identity for every object across the frames of a video, even when detections are briefly missed, and (v) presents the results and analytics through a professional graphical interface."),
  H2("2.2 Objectives"),
  ...numbered([
    "To detect objects of a selected colour using HSV colour-space segmentation.",
    "To handle the colour red correctly using two hue ranges.",
    "To clean binary masks using erosion, dilation, morphological opening and closing.",
    "To identify objects using contour detection, bounding boxes and centroid calculation.",
    "To process videos frame by frame and track moving objects using centroid-based tracking.",
    "To provide visual analytics computed only from real processing results.",
    "To allow the user to download processed images, masks, videos and data.",
    "To build a polished, responsive web interface and verify the system with automated tests.",
  ]),
  H2("2.3 Limitations of Existing Approaches"),
  ...table("Existing approaches and their drawbacks", 2, ["Approach", "Drawbacks"], [
    ["Manual inspection and counting", "Slow, subjective, impossible for long videos"],
    ["Fixed RGB thresholding scripts", "Sensitive to shadows and highlights; no interface; no measurements or analytics"],
    ["Image editors with colour pickers", "Can select a colour but cannot count objects, export data or track motion"],
    ["Deep-learning object detectors", "Need labelled data, training and often a GPU; hard to explain; excessive when colour alone identifies the object"],
  ], [3000, 5666]),
];

const ch3 = [
  H1("3. METHODOLOGY"),
  H2("3.1 Overall Approach"),
  P("The project follows a classical computer-vision pipeline. The same pipeline is applied to a single image or, for a video, to every frame in turn. The development methodology consisted of the following steps:"),
  ...numbered([
    "**Requirement study** – identification of the colour detection, tracking and analytics features required.",
    "**Colour model selection** – HSV was chosen over RGB because hue carries the colour while shading mainly affects the value (brightness) channel.",
    "**Threshold design** – HSV ranges were defined for six colours on the OpenCV scale (H: 0–179, S and V: 0–255) and exposed through sliders for fine-tuning.",
    "**Noise handling** – morphological opening followed by closing with an elliptical kernel; contours smaller than a minimum area are discarded.",
    "**Object description** – bounding rectangle, contour area and centroid (from image moments) are computed for every contour.",
    "**Tracking design** – greedy nearest-centroid matching with a maximum match distance and a disappearance counter.",
    "**Interface and analytics** – a five-page Streamlit application in which every chart reads directly from the stored results.",
    "**Testing** – a synthetic dataset with exact ground truth, automated unit tests (pytest) and automated browser tests (Playwright).",
  ]),
  H2("3.2 Image Processing Techniques Used"),
  ...table("Image processing techniques implemented", 3, ["No.", "Technique", "Purpose (in simple words)", "OpenCV function"], [
    ["1", "Image loading", "Decode uploaded bytes into a BGR pixel array; very large images are scaled to 1600 px", "cv2.imdecode, cv2.resize"],
    ["2", "BGR to HSV conversion", "Separate colour (hue) from colour strength (saturation) and brightness (value)", "cv2.cvtColor"],
    ["3", "HSV colour segmentation", "Describe a colour as a box in HSV space: hue interval plus minimum S and V", "–"],
    ["4", "Thresholding", "Pixels inside the HSV box become 255 (white), all others 0 (black)", "cv2.inRange"],
    ["5", "Binary masking", "Keep only the target-colour pixels of the original image", "cv2.bitwise_and"],
    ["6", "Erosion", "Shrink white regions – removes isolated noise pixels", "cv2.erode"],
    ["7", "Dilation", "Grow white regions – fills small gaps", "cv2.dilate"],
    ["8", "Morphological opening", "Erosion then dilation – removes noise while keeping object size", "cv2.morphologyEx (OPEN)"],
    ["9", "Morphological closing", "Dilation then erosion – fills small holes such as highlights", "cv2.morphologyEx (CLOSE)"],
    ["10", "Contour detection", "Trace the outline of each connected white region", "cv2.findContours"],
    ["11", "Bounding box", "Smallest upright rectangle enclosing a contour", "cv2.boundingRect"],
    ["12", "Centroid calculation", "Centre of mass: cx = M10/M00, cy = M01/M00", "cv2.moments"],
    ["13", "Frame-by-frame processing", "Read, process and write one frame at a time (constant memory)", "cv2.VideoCapture / VideoWriter"],
    ["14", "Centroid-based tracking", "Match centroids between frames by smallest Euclidean distance", "CentroidTracker (own code)"],
  ], [600, 2000, 3866, 2200]),
  H2("3.3 HSV Colour Model and the Red Hue Problem"),
  P("In OpenCV the hue channel is stored from 0 to 179 (the 360° colour wheel divided by two). Red lies exactly where the wheel wraps around, i.e. close to both 0 and 179. A single interval such as [170, 10] cannot be expressed in one cv2.inRange() call, so red is detected as the union of two ranges, [0, 10] OR [170, 179], whose masks are merged with cv2.bitwise_or(). A unit test confirms that using only the lower range finds just one of two red objects, while the dual range finds both."),
  ...table("Default HSV ranges for the predefined colours (adjustable in the application)", 3,
    ["Colour", "Hue range", "Min. saturation", "Min. value"], [
    ["Red", "0–10 and 170–179", "120", "70"], ["Orange", "11–20", "120", "100"], ["Yellow", "21–34", "100", "100"],
    ["Green", "35–85", "60", "50"], ["Blue", "95–128", "80", "50"], ["Purple", "129–160", "60", "50"],
  ], [2166, 2500, 2000, 2000]),
  H2("3.4 Algorithm 1 – Colour Object Detection"),
  ...code([
    "Input : image I (BGR), list of HSV ranges R, kernel size k, minimum area A",
    "Output: list of objects (box, area, centroid), annotated image",
    "",
    "1. HSV <- cvtColor(I, BGR2HSV)",
    "2. M   <- empty (all-zero) mask of the size of I",
    "3. for each (lower, upper) in R:          # 2 ranges for red, 1 otherwise",
    "       M <- M OR inRange(HSV, lower, upper)",
    "4. M   <- morphologyEx(M, OPEN,  ellipse(k))   # remove noise",
    "5. M   <- morphologyEx(M, CLOSE, ellipse(k))   # fill holes",
    "6. C   <- findContours(M, RETR_EXTERNAL)",
    "7. for each contour c in C with contourArea(c) >= A:",
    "       (x, y, w, h) <- boundingRect(c)",
    "       m <- moments(c);  cx <- m10/m00;  cy <- m01/m00",
    "       store object, draw box, label and centroid on I",
    "8. return objects (sorted by area), I",
  ]),
  H2("3.5 Algorithm 2 – Centroid-Based Tracking (for each frame t)"),
  ...code([
    "Input : detections D_t = {(centroid, box)} of frame t",
    "State : tracks T = {id -> (centroid, box, missing)}, next_id",
    "Params: max_distance d_max, max_disappeared m_max",
    "",
    "1. if D_t is empty: missing += 1 for every track; delete tracks with missing > m_max",
    "2. if T is empty: create a new track (next_id++) for every detection",
    "3. Dist[i][j] <- Euclidean distance between track i and detection j",
    "4. for all pairs (i, j) in increasing order of Dist:",
    "       skip if track i or detection j is already matched",
    "       stop if Dist[i][j] > d_max",
    "       update track i with detection j; missing_i <- 0",
    "5. unmatched tracks: missing += 1; delete if missing > m_max",
    "6. unmatched detections: start a new track with next_id",
    "7. draw box, 'ID n' label and the trail of recent centroids",
  ]),
  P("The disappearance counter (step 5) is what allows an object to keep its ID when it is hidden for a few frames, for example behind an obstacle. The matching is greedy (closest pair first) rather than an optimal assignment; for a small number of well-separated objects this gives the same result with much simpler code. The tracker uses position only – it is not a deep-learning or Kalman-filter tracker."),
];

const ch4 = [
  H1("4. SYSTEM ARCHITECTURE"),
  H2("4.1 Architecture of the Processing Model"),
  P("Chromatic Vision does not use a trained machine-learning model. Its “model” is the deterministic image-processing pipeline of Chapter 3, organised into a three-layer software architecture (Figure 4.1):"),
  ...bullets([
    "**Presentation layer (Streamlit)** – app.py (page configuration and routing), reusable UI components, one module per page and a custom stylesheet.",
    "**Processing layer (modules/)** – all computer-vision logic: colour ranges, image processing, video processing, object tracking and analytics. This layer has no dependency on the user interface, which makes it easy to test.",
    "**Foundation layer** – the OpenCV, NumPy, Plotly and Matplotlib libraries, Streamlit session state (results and statistics) and a per-session folder for temporary files that is cleaned automatically.",
  ]),
  ...figure(PF + "fig_architecture.png", "System architecture of Chromatic Vision", 4),
  H2("4.2 Processing Workflow"),
  P("Figure 4.2 shows the flow of data through the processing model. For a still image steps 1–6 and 8 are executed once. For a video, steps 2–7 are repeated for every frame and each annotated frame is written to the output video."),
  ...figure(PF + "fig_workflow.png", "Processing workflow (steps 2–7 are repeated for every video frame)", 4),
  H2("4.3 Technologies Used"),
  ...table("Technology stack", 4, ["Technology", "Role in the project"], [
    ["Python 3.10+", "Implementation language (developed and tested on Python 3.12.10)"],
    ["OpenCV", "Image decoding, colour conversion, thresholding, morphology, contours, moments, video input/output"],
    ["NumPy", "Pixel arrays, distance matrix for tracking, statistics"],
    ["Streamlit", "Web interface, widgets, session state, file upload and download"],
    ["Plotly", "Interactive charts: colour distribution, object areas, per-frame charts, trajectories"],
    ["Matplotlib", "Hue-spectrum histogram and report figures"],
    ["Pillow", "Reading file format information of uploaded images; image display in Streamlit"],
    ["pytest, Playwright", "Automated unit tests and automated browser (end-to-end) tests"],
  ], [2400, 6266]),
  H2("4.4 Hardware and Software Requirements"),
  ...table("Hardware and software requirements", 4, ["Item", "Minimum requirement", "System used for testing"], [
    ["Processor", "Dual-core 64-bit CPU", "AMD Ryzen 5 5600G (6 cores / 12 threads)"],
    ["RAM", "4 GB", "16 GB"],
    ["GPU", "Not required", "Not used"],
    ["Operating system", "Windows 10/11, Linux or macOS", "Windows 10 Pro"],
    ["Software", "Python 3.10+, modern web browser", "Python 3.12.10, Microsoft Edge"],
  ], [2200, 3133, 3333]),
];

const ch5 = [
  H1("5. DATASET DETAILS"),
  H2("5.1 Description of the Dataset"),
  P("Because the system is based on image processing rather than machine learning, it does not require a training dataset. A dataset is nevertheless needed to **evaluate** the detection and tracking accuracy. For this purpose a small sample dataset was created synthetically with OpenCV and NumPy (scripts/generate_samples.py). Generating the data has two important advantages: the exact number and position of objects of every colour is known (ground truth), and there are no copyright or licensing restrictions."),
  P("To make the data realistic, the scenes contain shaded balls with highlights (constant hue but varying brightness), flat geometric shapes, neutral distractor objects (white, grey and black) that must not be detected, a gradient background and added Gaussian noise. The ground truth is stored in assets/sample_ground_truth.json."),
  ...table("Sample dataset", 5, ["File", "Type", "Resolution", "Length", "Content"], [
    ["shapes_scene.png", "Image (PNG)", "1280 × 800", "–", "15 coloured shapes (circles, rectangles, triangles) in all six colours + 3 neutral distractors"],
    ["ball_collection.jpg", "Image (JPEG)", "1000 × 640", "–", "9 shaded balls: 4 red, 3 blue, 2 green"],
    ["neutral_scene.png", "Image (PNG)", "900 × 600", "–", "Only white, grey and black objects (negative test)"],
    ["moving_objects.mp4", "Video (MP4)", "640 × 360", "200 frames, 25 fps, 8 s", "2 red balls in opposite lanes, 1 bouncing blue ball, 1 green square, 1 yellow ball on a sine path, and a grey pillar that hides one red ball"],
    ["orbiting_ball.avi", "Video (AVI, MJPG)", "480 × 360", "120 frames, 30 fps, 4 s", "1 orange ball moving on a circular path"],
  ], [1900, 1350, 1250, 1500, 2666]),
  ...table("Ground truth – number of objects of each colour", 5, ["File", "Red", "Orange", "Yellow", "Green", "Blue", "Purple"], [
    ["shapes_scene.png", "3", "2", "2", "3", "3", "2"],
    ["ball_collection.jpg", "4", "0", "0", "2", "3", "0"],
    ["neutral_scene.png", "0", "0", "0", "0", "0", "0"],
    ["moving_objects.mp4", "2", "0", "1", "1", "1", "0"],
    ["orbiting_ball.avi", "0", "1", "0", "0", "0", "0"],
  ], [2266, 1066, 1066, 1066, 1066, 1066, 1070]),
  ...figure(PF + "p_dataset.png", "Sample dataset: (a)–(c) images, (d)–(e) first frames of the videos", 5),
  H2("5.2 User Data"),
  P("In addition to the samples, the user can upload any JPG, JPEG or PNG image and any MP4, AVI or MOV video (up to 200 MB). Images larger than 1600 pixels on the longest side and videos wider than the chosen processing width are scaled down automatically to keep memory use and processing time reasonable."),
];

const ch6 = [
  H1("6. IMPLEMENTATION"),
  H2("6.1 Project Structure"),
  P("The source code is modular: the computer-vision logic is completely separated from the user interface."),
  ...table("Main source files", 6, ["File / folder", "Responsibility"], [
    ["app.py", "Entry point: page configuration, loading of the stylesheet, page routing"],
    ["modules/color_ranges.py", "HSV presets for six colours, dual-range builder for red, colour conversions"],
    ["modules/image_processing.py", "load_image_from_bytes, to_hsv, create_mask, apply_morphology, find_objects, draw_detections, analyze_image"],
    ["modules/object_tracking.py", "CentroidTracker class with update(), track history and summary"],
    ["modules/video_processing.py", "get_video_info, make_preview, process_video (frame loop, overlays, WebM and MP4 writers)"],
    ["modules/analytics.py", "Colour distribution and hue histogram; Plotly and Matplotlib chart builders"],
    ["components/", "Session state and navigation, sidebar, colour picker, reusable HTML/CSS components"],
    ["views/", "One module per page: Overview, Image Analysis, Video Tracking, Analytics, About"],
    ["styles/main.css", "Custom dark theme (#0B1020 background, indigo / sky-blue / violet accents)"],
    ["tests/", "34 automated unit tests (pytest)"],
    ["scripts/", "Sample generation, report figures, automated browser test and screenshots"],
  ], [2900, 5766]),
  H2("6.2 Image Analysis Module"),
  P("analyze_image() runs the complete pipeline of Algorithm 1 and returns a result object containing the original image, HSV image, raw mask, every morphological stage, the final mask, the segmented image, the annotated image, the list of objects, the colour coverage percentage and the processing time. The objects are sorted by area and labelled “Red #1”, “Red #2”, etc. on the annotated image, with a white dot marking the centroid."),
  H2("6.3 Video Tracking Module"),
  P("process_video() opens the input with cv2.VideoCapture and reads one frame at a time, so memory use stays constant regardless of video length. Each frame is optionally resized, processed with the detection pipeline and passed to the CentroidTracker. The tracked objects are drawn with a colour per ID, an “ID n” label and a motion trail of recent centroids, together with a status bar (colour, frame number, object count). Each frame is written to two output files:"),
  ...bullets([
    "**WebM (VP8)** – plays directly in every modern browser and is used for the in-app player;",
    "**MP4 (MPEG-4 Part 2)** – for desktop players such as VLC and Windows Media Player. (The OpenCV build for Windows does not include an H.264 encoder, which was confirmed during development.)",
  ]),
  P("Per-frame statistics (number of objects, active IDs and processing time) are recorded for the analytics page and the CSV download. A progress callback updates the progress bar and a live preview in the browser while the video is processed."),
  H2("6.4 User Interface"),
  P("The interface is a Streamlit application with a custom dark theme and five pages selected from the sidebar: **Overview** (hero section, live session statistics, quick demos and feature cards), **Image Analysis Studio**, **Video Tracking Studio**, **Analytics & Insights** and **About Project** (in-app documentation). Streamlit session state stores the current page, the statistics, the latest results and the run history. The layout adapts to phone screens."),
  H2("6.5 Error Handling and Resource Management"),
  ...bullets([
    "Empty, corrupt or non-image files raise a ValueError that the interface shows as a clear error message instead of crashing.",
    "Unreadable or empty videos are detected before processing; videos with no matching colour are processed normally and report zero detections.",
    "Uploads, previews and generated videos are stored in a per-session folder; old outputs are deleted when replaced, and folders older than 12 hours are removed automatically.",
  ]),
  H2("6.6 Testing Method"),
  P("Two types of automated tests were written and executed. **Unit tests** (pytest, 34 tests) check the processing layer against the known ground truth, including edge cases such as invalid files, empty videos, very large inputs and tracker behaviour during occlusions. **End-to-end tests** (Playwright with Microsoft Edge) operate the real application in a browser exactly as a user would – navigating every page, running both demos, changing colours, uploading valid and invalid files and downloading the results – and also capture the screenshots used in this report."),
];

const ch7 = [
  H1("7. RESULTS AND DISCUSSION"),
  P("All values in this chapter were obtained from actual runs of the system on the test machine described in Table 4.2. Processing times vary slightly from run to run."),
  H2("7.1 Image Detection Results"),
  ...table("Image detection results with default settings (kernel 5 × 5, 1 iteration, minimum area 300 px)", 7,
    ["Image", "Colour", "Expected", "Detected", "Coverage (%)", "Time (ms)"], [
    ["shapes_scene.png", "Red", "3", "3", "4.81", "29.5 *"], ["shapes_scene.png", "Orange", "2", "2", "2.52", "7.5"],
    ["shapes_scene.png", "Yellow", "2", "2", "2.37", "8.5"], ["shapes_scene.png", "Green", "3", "3", "4.90", "6.6"],
    ["shapes_scene.png", "Blue", "3", "3", "3.83", "7.6"], ["shapes_scene.png", "Purple", "2", "2", "2.37", "9.5"],
    ["ball_collection.jpg", "Red", "4", "4", "7.63", "5.6"], ["ball_collection.jpg", "Blue", "3", "3", "5.93", "4.5"],
    ["ball_collection.jpg", "Green", "2", "2", "3.91", "4.7"], ["neutral_scene.png", "All six", "0", "0", "0.00", "–"],
  ], [2366, 1200, 1200, 1200, 1400, 1300]),
  P("* The first call includes a one-time OpenCV initialisation cost; subsequent calls on the same image take 7–10 ms.", { spacing: { after: 200 } }),
  ...figure(FG + "fig_pipeline_stages.png", "Pipeline stages for red on shapes_scene.png: (a) original, (b) raw mask, (c) erosion, (d) dilation, (e) final mask, (f) detected objects", 7),
  P("**Discussion.** The detected count equals the ground truth for every colour on both sample images (15 of 15 colour/image combinations). The neutral distractors are never detected, because the minimum saturation and value thresholds exclude achromatic pixels – something a simple RGB threshold cannot guarantee. The shaded red ball, whose brightness varies strongly from its highlight to its edge, is detected as a single object, which demonstrates the advantage of the HSV colour space."),
  H2("7.2 Video Tracking Results"),
  ...table("Video tracking results (max. match distance 80 px, 15 frames to keep a lost ID)", 7,
    ["Video", "Colour", "Frames", "Frames with detections", "Detection freq.", "Unique IDs", "Avg. ms / frame"], [
    ["moving_objects.mp4", "Red", "200", "200", "100 %", "2", "9.44"],
    ["moving_objects.mp4", "Blue", "200", "200", "100 %", "1", "8.73"],
    ["moving_objects.mp4", "Purple (absent)", "200", "0", "0 %", "0", "8.22"],
    ["orbiting_ball.avi", "Orange", "120", "120", "100 %", "1", "9.97"],
  ], [2066, 1300, 900, 1300, 1100, 900, 1100]),
  ...figure(PF + "p_tracking_grid.png", "Frames 1, 61, 96, 101, 151 and 200 of the processed sample video. In frames 96 and 101 the lower red ball (ID 1) is hidden behind the pillar; after reappearing it keeps ID 1", 7),
  P("**Discussion.** The tracker produced exactly **two IDs** for the two red balls over the whole clip. Track 1 was matched in 191 of the 200 frames: for 9 frames it was hidden behind the pillar, and the disappearance counter kept the track alive so that the ball received the same ID when it reappeared. Track 2 was matched in all 200 frames. When the selected colour is absent (purple) the system runs without error, reports zero detections and still produces an output video. An average of about 9–10 ms per frame corresponds to roughly 100 frames per second, which is faster than real time for these videos. The output WebM and MP4 files were re-opened with OpenCV and contained the expected number of frames."),
  H2("7.3 Summary of Test Cases"),
  ...table("Test cases and results", 7, ["ID", "Test", "Expected result", "Actual result", "Status"], [
    ["TC-01", "Red detection (both hue ends; sample image)", "Both ends found; 3 red objects", "2 of 2 found; 3 red objects", "Pass"],
    ["TC-02", "Blue detection", "1 object, centroid at centre (±2 px)", "As expected", "Pass"],
    ["TC-03", "Green detection", "Exact bounding box; 2 green balls in sample", "As expected", "Pass"],
    ["TC-04", "Multiple objects, all colours on all samples", "Counts equal ground truth", "15 of 15 match", "Pass"],
    ["TC-05", "No matching colour", "0 objects, info message, no crash", "As expected", "Pass"],
    ["TC-06", "Invalid image upload (text file renamed .png)", "Clear error message", "“Invalid image” shown", "Pass"],
    ["TC-07", "Video processing (MP4, AVI, MOV)", "Correct video info; processed", "As expected", "Pass"],
    ["TC-08", "Moving object tracking with occlusion", "2 IDs for 2 red balls", "2 IDs, kept through occlusion", "Pass"],
    ["TC-09", "Processed image download", "Valid PNG file", "PNG downloaded and decoded", "Pass"],
    ["TC-10", "Processed video download", "WebM and MP4 open with all frames", "As expected", "Pass"],
    ["TC-11", "Dashboard statistics", "Counts update after real runs only", "5 images, 1 video shown", "Pass"],
    ["TC-12", "Navigation between pages", "All 5 pages open", "As expected", "Pass"],
    ["TC-13", "Responsive layout (390 px)", "No horizontal scrolling", "As expected", "Pass"],
  ], [800, 2500, 2200, 2266, 900]),
  P("Overall, all **34 unit tests** and all **23 automated browser checks** passed."),
];

const shots = [
  ["p_overview.png", "Overview dashboard with live session statistics and navigation sidebar"],
  ["p_image_top.png", "Image Analysis Studio – input, colour palette, HSV range and original vs. processed comparison"],
  ["p_image_results.png", "Image detection results – metrics, comparison of original, mask and bounding boxes, downloads"],
  ["03b_mask_tab.png", "Mask and segmentation tab – raw mask, cleaned mask and segmented image", SS],
  ["03c_morphology_tab.png", "Morphology pipeline tab – HSV hue, threshold, erosion, dilation, opening and closing", SS],
  ["p_invalid.png", "Error handling – a corrupt file uploaded as an image is rejected with a clear message"],
  ["p_video_top.png", "Video Tracking Studio – video information (FPS, frames, resolution, duration) and preview"],
  ["p_video_results.png", "Video tracking results – metrics, processed video with IDs and trails, downloads"],
  ["p_an_img_1.png", "Analytics – image metrics and colour distribution charts"],
  ["p_an_img_2.png", "Analytics – object areas, Matplotlib hue spectrum and visual comparison"],
  ["p_an_vid_1.png", "Analytics – video metrics, objects per frame and processing time per frame"],
  ["p_an_vid_2.png", "Analytics – centroid trajectories and track lifetimes"],
  ["p_about_arch.png", "About Project page – in-app workflow and architecture diagrams"],
];
const ch8 = [H1("8. SCREENSHOTS"),
  P("The following screenshots were captured from the running application with the automated browser test."),
  ...shots.flatMap(([f, c, dir]) => figure((dir || PF) + f, c, 8, MAX_PX, 560))];
// mobile pair
{
  figNo[8] += 1;
  const img = (f) => { const { w, h } = pngSize(PF + f); const width = 210; return new ImageRun({ type: "png",
    data: fs.readFileSync(PF + f), transformation: { width, height: Math.round(h * width / w) },
    altText: { title: f, description: "Mobile layout", name: f } }); };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const nb = { top: none, bottom: none, left: none, right: none };
  ch8.push(new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [4333, 4333], rows: [new TableRow({
    children: ["p_mobile_1.png", "p_mobile_2.png"].map((f) => new TableCell({ borders: nb, width: { size: 4333, type: WidthType.DXA },
      children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [img(f)] })] })) })] }));
  ch8.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 240 }, children: [
    new TextRun({ text: `Figure 8.${figNo[8]}: `, bold: true, size: 22 }),
    new TextRun({ text: "Responsive layout on a phone screen (390 px wide): Overview and Image Analysis", italics: true, size: 22 })] }));
}

const ch9 = [
  H1("9. CONCLUSION"),
  H2("9.1 Conclusion"),
  P("This project shows that a classical image processing pipeline – HSV colour conversion, cv2.inRange() thresholding, morphological cleaning, contour analysis and centroid tracking – is sufficient to detect, measure and track colour-defined objects reliably and faster than real time, without any training data or GPU. All the objectives stated in Chapter 2 were achieved: six colour presets plus custom ranges, correct dual-range red detection, configurable morphology, frame-by-frame video tracking with consistent IDs through short occlusions, analytics computed from real results, downloadable outputs and a polished, responsive web interface."),
  P("On the evaluation dataset, the detected object counts matched the ground truth exactly for every colour, neutral objects were never falsely detected, and both red balls kept their identities for all 200 frames of the sample video. All 34 unit tests and 23 automated browser checks passed."),
  H2("9.2 Limitations"),
  ...bullets([
    "Fixed HSV thresholds are sensitive to strong colour casts and very dim lighting.",
    "Touching objects of the same colour merge into one contour, and background regions of the target colour are detected as objects.",
    "Centroid matching uses position only, so IDs may swap when two same-coloured objects cross very closely.",
    "The evaluation dataset is synthetic; accuracy on real photographs depends on threshold tuning and was not measured on a labelled real-world dataset.",
  ]),
  H2("9.3 Future Enhancements"),
  ...bullets([
    "Live webcam processing.",
    "Kalman-filter motion prediction and Hungarian assignment for more robust tracking.",
    "Watershed segmentation to separate touching objects.",
    "Automatic threshold calibration from a pixel clicked by the user.",
    "Shape classification (circle, rectangle, triangle) and multi-colour tracking in one pass.",
  ]),
  H1("REFERENCES"),
  ...numbered([
    "R. C. Gonzalez and R. E. Woods, Digital Image Processing, 4th ed. Pearson, 2018.",
    "G. Bradski and A. Kaehler, Learning OpenCV: Computer Vision with the OpenCV Library. O’Reilly Media, 2008.",
    "R. Szeliski, Computer Vision: Algorithms and Applications, 2nd ed. Springer, 2022.",
    "A. R. Smith, “Color gamut transform pairs,” ACM SIGGRAPH Computer Graphics, vol. 12, no. 3, pp. 12–19, 1978.",
    "J. Serra, Image Analysis and Mathematical Morphology. Academic Press, 1982.",
    "S. Suzuki and K. Abe, “Topological structural analysis of digitized binary images by border following,” Computer Vision, Graphics, and Image Processing, vol. 30, no. 1, pp. 32–46, 1985.",
    "OpenCV documentation – Changing Colorspaces, Morphological Transformations, Contours. https://docs.opencv.org/",
    "Streamlit documentation. https://docs.streamlit.io/",
    "Plotly Python documentation. https://plotly.com/python/",
  ]),
];

// ---------------------------------------------------------------- document
const pageProps = {
  page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1800, right: 1440, header: 708, footer: 708 } },
};
const header = new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "808080", space: 4 } },
  children: [new TextRun({ text: "Chromatic Vision – Image and Video Analytics Mini-Project", italics: true, size: 18, color: "555555" })] })] });
const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] });
const emptyHF = { header: new Header({ children: [new Paragraph({ children: [] })] }), footer: new Footer({ children: [new Paragraph({ children: [] })] }) };

const doc = new Document({
  creator: "Chromatic Vision project", title: "Chromatic Vision – Mini-Project Report",
  styles: {
    default: { document: { run: { font: FONT, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: "1F3864" },
        paragraph: { spacing: { before: 120, after: 280 }, keepNext: true, outlineLevel: 0, alignment: AlignmentType.CENTER } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true },
        paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true },
        paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 2 } },
      { id: "TOC1", name: "toc 1", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 23, bold: true },
        paragraph: { spacing: { before: 100, after: 20, line: 264 } } },
      { id: "TOC2", name: "toc 2", basedOn: "Normal", next: "Normal", run: { font: FONT, size: 22 },
        paragraph: { spacing: { before: 0, after: 10, line: 252 }, indent: { left: 360 } } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [
    { properties: { ...pageProps, titlePage: true, page: { ...pageProps.page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } },
      headers: { first: emptyHF.header, default: new Header({ children: [new Paragraph({ children: [] })] }) },
      footers: { first: emptyHF.footer, default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
      children: [...cover, ...certificate, ...abstract, ...toc] },
    { properties: { ...pageProps, page: { ...pageProps.page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } },
      headers: { default: header }, footers: { default: footer },
      children: [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8, ...ch9] },
  ],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("written", OUT, buf.length); });
