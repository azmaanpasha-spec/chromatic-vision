// Builds the printed assignment report: report/Chromatic_Vision_Project_Report.docx
// Layout follows the department's CSDX 536 assignment format (bordered A4 pages,
// Times New Roman, numbered sections, figures with short observations).
// Usage: npm install docx  &&  node scripts/build_report_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, BorderStyle, Footer, PageNumber, LevelFormat, VerticalAlign,
  PageBorderDisplay, PageBorderOffsetFrom, PageBorderZOrder,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const PF = ROOT + "/report/figures/print/";
const FG = ROOT + "/report/figures/";
const OUT = ROOT + "/report/Chromatic_Vision_Project_Report.docx";
const M = JSON.parse(fs.readFileSync(FG + "measured_results.json", "utf8"));

const FONT = "Times New Roman";
const MARGIN_LR = 850;
const CONTENT_W = 11906 - 2 * MARGIN_LR; // 10206 DXA
const MAX_PX = 560;

// ---------------------------------------------------------------- helpers
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
// **bold** segments inside a string
const runs = (text, opts = {}) => text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((t) =>
  t.startsWith("**") ? new TextRun({ text: t.slice(2, -2), bold: true, ...opts }) : new TextRun({ text: t, ...opts }));
const P = (text, opts = {}) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 100 }, ...opts,
  children: runs(text) });
const PK = (text) => P(text, { keepNext: true });
const H1 = (text, opts = {}) => new Paragraph({ heading: HeadingLevel.HEADING_1, ...opts, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const bullets = (items) => items.map((t) => new Paragraph({ numbering: { reference: "bullets", level: 0 },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 }, children: runs(t) }));
let listNo = 0;
const numberingConfigs = [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
  alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 300 } } } }] }];
const numbered = (items, align = AlignmentType.JUSTIFIED) => {
  const ref = "num" + (++listNo);
  numberingConfigs.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 360 } } } }] });
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, alignment: align,
    spacing: { after: 40 }, children: runs(t) }));
};

let figNo = 0;
function figure(file, caption, note, maxW = MAX_PX, maxH = 360) {
  figNo += 1;
  const { w, h } = pngSize(file);
  let width = Math.min(maxW, w), height = Math.round(h * width / w);
  if (height > maxH) { height = maxH; width = Math.round(w * height / h); }
  const out = [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 80 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width, height },
        altText: { title: caption, description: caption, name: path.basename(file) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: !!note, spacing: { after: 80 },
      children: [new TextRun({ text: `Figure ${figNo}: `, bold: true }), new TextRun(caption)] }),
  ];
  if (note) out.push(P(note, { spacing: { after: 200 } }));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths) {
  const scale = CONTENT_W / widths.reduce((a, b) => a + b, 0);
  const w = widths.map((x) => Math.floor(x * scale));
  w[w.length - 1] += CONTENT_W - w.reduce((a, b) => a + b, 0);
  const keep = rows.length <= 12;
  const cell = (text, header, cw, last) => new TableCell({
    borders, width: { size: cw, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    margins: { top: 40, bottom: 40, left: 100, right: 100 },
    children: [new Paragraph({ keepNext: keep && !last, keepLines: true, alignment: AlignmentType.LEFT,
      children: runs(String(text), header ? { bold: true } : {}) })],
  });
  return [
    new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: w,
      rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((hd, i) => cell(hd, true, w[i])) }),
        ...rows.map((r, ri) => new TableRow({ cantSplit: true,
          children: r.map((c, i) => cell(c, false, w[i], ri === rows.length - 1)) }))] }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}
const blank = (n = 1, size = 24) => Array.from({ length: n }, () =>
  new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text: "", size })] }));

// ---------------------------------------------------------------- cover page
const coverLine = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160, line: 360 },
  children: [new TextRun({ text, bold: true, underline: {}, size: 48 })] });
const boxLine = (children, align = AlignmentType.LEFT) => new Paragraph({ alignment: align, spacing: { after: 120 },
  children });
const cover = [
  ...blank(15),
  coverLine("CSDX 536"),
  coverLine("IMAGE & VIDEO ANALYTICS"),
  coverLine("ASSIGNMENT"),
  ...blank(5),
  new Table({
    alignment: AlignmentType.RIGHT, width: { size: 4300, type: WidthType.DXA }, columnWidths: [4300],
    rows: [new TableRow({ children: [new TableCell({
      borders: { top: { style: BorderStyle.SINGLE, size: 6, color: "7F7F7F" }, bottom: { style: BorderStyle.SINGLE, size: 6, color: "7F7F7F" },
        left: { style: BorderStyle.SINGLE, size: 6, color: "7F7F7F" }, right: { style: BorderStyle.SINGLE, size: 6, color: "7F7F7F" } },
      width: { size: 4300, type: WidthType.DXA }, margins: { top: 160, bottom: 200, left: 140, right: 140 },
      children: [
        boxLine([new TextRun({ text: "Submitted by", bold: true })], AlignmentType.CENTER),
        boxLine([new TextRun("AZMAAN PASHA (______________)")]),
        boxLine([new TextRun({ text: "Department: ", bold: true }), new TextRun("B.Tech – AI & DS “A”")],
          AlignmentType.CENTER),
      ] })] })],
  }),
];

// ---------------------------------------------------------------- data from measured_results.json
const gt = JSON.parse(fs.readFileSync(ROOT + "/assets/sample_ground_truth.json", "utf8"));
const imageRows = M.images.map((r) => [r.image, r.color, gt.images[r.image][r.color], r.objects,
  r.objects === gt.images[r.image][r.color] ? "Yes" : "No", r.coverage.toFixed(2) + "%", r.ms.toFixed(1) + " ms"]);
imageRows.push(["neutral_scene.png", "All six presets", 0, 0, "Yes", "0.00%", "–"]);
const vidExpected = (v) => (gt.videos[v.video].objects[v.color] || 0);
const videoRows = M.videos.map((v) => [v.video, v.color, v.frames, `${v.with_detections} (${v.frequency.toFixed(1)}%)`,
  vidExpected(v), v.tracks, v.avg_ms.toFixed(2) + " ms"]);
const redVideo = M.videos.find((v) => v.video === "moving_objects.mp4" && v.color === "Red");
const trackRows = redVideo.tracks_detail.map((t) => [t["Track ID"], t["First frame"] + 1, t["Last frame"] + 1,
  `${t["Frames seen"]} of ${redVideo.frames}`, t["Path length (px)"].toFixed(1)]);

// ---------------------------------------------------------------- body
const body = [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360 },
    children: [new TextRun({ text: "CHROMATIC VISION – INTELLIGENT COLOR DETECTION AND OBJECT TRACKING USING IMAGE PROCESSING TECHNIQUES",
      bold: true, underline: {}, size: 36 })] }),

  H1("1. Abstract"),
  P("Chromatic Vision is an image and video analytics application designed to detect objects of a chosen colour in images and to follow those objects across the frames of a video. The system uses classical image processing techniques rather than deep learning, so it does not require any training data, labelled dataset or GPU."),
  P("Every input image or video frame is converted from the BGR colour space to the HSV (Hue, Saturation, Value) colour space. A binary mask of the target colour is produced by HSV thresholding, using two hue ranges for red because red lies at both ends of the hue circle. The mask is cleaned with morphological opening and closing, and contour analysis is used to locate each object, draw its bounding box and calculate its centroid. For videos, a centroid-based tracker links the detections of consecutive frames so that every object keeps a consistent ID."),
  P("A Streamlit application with five pages (Overview, Image Analysis, Video Tracking, Analytics & Insights and About Project) has been developed with OpenCV, NumPy, Plotly, Matplotlib and Pillow. Users can upload their own media or use the bundled sample images and videos, select one of six colour presets or a custom range, adjust the processing parameters and download the processed image, binary mask, segmented image, tracked video and CSV reports."),
  P(`On the bundled sample set the detected object counts matched the known ground truth for all 15 image–colour combinations tested. In the 200-frame sample video the two red balls were tracked with two stable IDs, including through a short occlusion, at an average of ${redVideo.avg_ms.toFixed(2)} ms per frame. All 34 automated unit tests and 22 end-to-end interface checks passed.`),
  P("The project demonstrates the practical use of colour spaces, segmentation, morphology, contour analysis and object tracking. It is developed as an educational prototype; its colour presets are tuned for clearly coloured objects and are not intended for safety-critical use."),

  H1("2. Introduction"),
  P("Colour is one of the simplest and most informative visual features of an object. Many practical tasks such as sorting coloured products, following a coloured marker, counting coloured items or locating a ball in a sports clip can be solved by finding the pixels that have a particular colour and grouping them into objects."),
  P("Digital images are usually stored in the RGB (or, in OpenCV, BGR) colour space, where the colour and the brightness of a pixel are mixed across three channels. A small change in lighting therefore changes all three values. The HSV colour space separates the colour itself (hue) from its purity (saturation) and its brightness (value), which makes it much easier to describe a colour with a fixed range of numbers."),
  P("This project focuses on colour-based object detection and tracking using image processing techniques. The system analyses uploaded images and video frames to identify objects of a selected colour, removes noise from the result with morphological operations, measures each object with contour analysis and follows moving objects with a centroid tracker."),
  P("OpenCV performs the image and video processing, NumPy handles the pixel arrays, and Streamlit provides an interactive interface for uploading media, choosing parameters and viewing results. Plotly and Matplotlib are used to present real analytics computed from each run."),
  P("The project demonstrates how image and video analytics can be applied to colour detection and object tracking without the cost of training a deep learning model."),

  H1("3. Problem Statement"),
  P("Identifying and counting objects of a particular colour by eye is slow and error-prone, especially when there are many objects in an image or when the objects move through a long video."),
  P("Simple thresholding in the RGB colour space is not reliable because brightness and colour are mixed, so the same object can produce very different RGB values under different lighting. Red objects are a particular difficulty, because their hue values fall on both sides of the 0°/360° boundary of the hue circle."),
  P("Therefore, a computer vision-based system is developed to detect objects of a selected colour in uploaded images and videos, using the HSV colour space and a dual hue range for red."),
  P("The system aims to segment the target colour, remove noise, locate each object with a bounding box and centroid, assign consistent IDs to moving objects in videos, and report measured statistics such as object count, colour coverage, detection frequency and processing time."),

  H1("4. Objectives"),
  P("The main objectives of the project are:"),
  ...bullets([
    "To develop a colour detection system based on the HSV colour space.",
    "To provide predefined HSV presets for red, orange, yellow, green, blue and purple, and a custom range option.",
    "To detect red correctly using two hue ranges that are combined with a logical OR.",
    "To remove noise from the binary mask using erosion, dilation, opening and closing.",
    "To locate objects with contour detection and to draw bounding boxes, labels and centroids.",
    "To process uploaded videos frame by frame and track moving objects with consistent IDs.",
    "To calculate real analytics: object count, coverage, colour distribution, detections per frame and processing time.",
    "To allow the processed image, mask, segmented image, tracked video and CSV reports to be downloaded.",
    "To develop an interactive, easy-to-use application using Streamlit.",
    "To verify the system with automated tests against a sample set with known ground truth.",
  ]),

  H1("5. Existing and Proposed Approach"),
  P("**5.1 Existing approach:** Colour-based inspection is often done manually, by looking at images or video and counting objects by eye. Simple automated approaches threshold the RGB values directly, while modern approaches train deep learning detectors. These approaches have certain limitations:"),
  ...bullets([
    "Manual counting and following of objects requires continuous human attention.",
    "Analysing many images or long videos manually is time-consuming and inconsistent.",
    "RGB thresholds are sensitive to lighting, because colour and brightness are mixed in every channel.",
    "A single hue interval cannot capture red, which wraps around the end of the hue circle.",
    "Deep learning detectors need a labelled dataset, training time and often a GPU, which is excessive for detecting a known colour.",
  ]),
  P("**5.2 Proposed approach:** The proposed system uses the HSV colour space and classical image processing. Each image or frame is converted to HSV and thresholded with cv2.inRange using the selected colour preset. For red, two masks (hue 0–10 and 170–179) are combined. Morphological opening removes small noise and closing fills small holes, after which cv2.findContours locates each object. Objects smaller than a minimum area are ignored, and the remaining objects are measured with a bounding rectangle and image moments."),
  P("For videos, OpenCV reads the file frame by frame and the same detection pipeline is applied to every frame. A centroid tracker matches each detection to the nearest existing track, so each object keeps the same ID while it moves. The annotated frames are written to WebM and MP4 output videos. The Streamlit application displays the results, charts and statistics and provides download buttons. No training is required, and the whole system runs on an ordinary CPU."),

  H1("6. Technologies and Tools Used"),
  ...table(["Technology", "Purpose", "Role in the project"], [
    ["Python 3.12", "Programming language", "Implements the project logic."],
    ["OpenCV", "Computer vision library", "Colour conversion, thresholding, morphology, contours, video reading and writing."],
    ["NumPy", "Numerical computing library", "Stores images as arrays; computes distances in the tracker and pixel statistics."],
    ["Streamlit", "Web application framework", "Provides the five-page interface for uploading media and viewing results."],
    ["Plotly", "Interactive charting library", "Draws the analytics charts (distribution, objects per frame, trajectories)."],
    ["Matplotlib", "Plotting library", "Draws the hue spectrum chart and the report figures."],
    ["Pillow", "Image processing library", "Reads image format information for uploaded files."],
    ["pytest", "Testing framework", "Runs the 34 automated unit tests."],
    ["Playwright", "Browser automation tool", "Runs the end-to-end interface checks and captures the screenshots."],
    ["Git and GitHub", "Version control", "Stores and publishes the project source code."],
  ], [2.2, 2.8, 5]),

  H1("7. System Requirements"),
  H2("7.1 Hardware requirements:"),
  ...bullets([
    "Computer or laptop capable of running Python 3.10 or later.",
    "No GPU is required; all processing runs on the CPU.",
    "Minimum 4 GB RAM; more is useful for long or high-resolution videos.",
    "Sufficient storage space for the uploaded and processed video files.",
    "The project was developed and tested on a Windows 10 PC.",
  ]),
  H2("7.2 Software requirements:"),
  ...bullets([
    "Python 3.12 virtual environment (Python 3.10 or later is supported).",
    "Streamlit 1.50 or later.",
    "OpenCV (opencv-python-headless) 4.9 or later.",
    "NumPy 1.26 or later.",
    "Plotly 5.20 or later and Matplotlib 3.8 or later.",
    "Pillow 10.0 or later.",
    "pytest (for running the tests).",
    "A modern web browser (Chrome, Edge or Firefox).",
  ]),

  H1("8. System Architecture and Workflow"),
  P("The proposed system follows a sequence of operations from media input and colour selection to detection, tracking and result presentation."),
  H2("8.1 System architecture"),
  P("The system is organised in three layers and consists of the following major components:"),
  ...numbered([
    "**Presentation layer:** app.py sets up the page and navigation; the components and views packages build the sidebar, colour picker and the five pages; styles/main.css provides the dark theme.",
    "**Media input:** Users upload an image (JPG, JPEG, PNG) or a video (MP4, AVI, MOV), or select a bundled sample.",
    "**Colour selection:** color_ranges.py provides the HSV presets and builds the dual range for red or a custom range from the sliders.",
    "**Image processing:** image_processing.py converts to HSV, creates the mask, applies morphology and finds the objects.",
    "**Video processing:** video_processing.py reads each frame, runs the detection pipeline, draws the overlay and writes the output videos.",
    "**Object tracking:** object_tracking.py assigns and maintains object IDs with a centroid tracker.",
    "**Analytics:** analytics.py computes colour distribution and hue histograms and builds the charts.",
    "**Foundation:** OpenCV, NumPy, Plotly and Matplotlib do the computation and visualisation; st.session_state stores the results and statistics of the current session.",
  ]),
  ...figure(PF + "fig_architecture.png", "System Architecture of Chromatic Vision", null, 560, 330),
  H2("8.2 Workflow"),
  P("The user uploads an image or video (or selects a sample), chooses the target colour and adjusts the parameters. The input is then converted from BGR to HSV, thresholded with cv2.inRange, cleaned with opening and closing, and searched for contours; each object's bounding box, area and centroid are calculated. For video these steps are repeated for every frame and the centroids are passed to the tracker, which assigns IDs. Finally the annotated output, statistics and charts are displayed with the download options."),
  ...figure(PF + "fig_workflow.png", "Processing Workflow", null, 600, 200),

  H1("9. Methodology and Algorithm"),
  H2("9.1 Dataset details"),
  P("Colour detection with HSV thresholding is a rule-based method, so no training dataset is required. To test the system objectively, a sample dataset with known ground truth was generated with the script scripts/generate_samples.py. Each sample contains solid, clearly coloured shapes with a known number of objects of each colour, and the expected counts are stored in assets/sample_ground_truth.json. The same files are used by the demo mode of the application and by the automated tests."),
  ...table(["File", "Type", "Resolution", "Frames / FPS", "Objects (ground truth)"], [
    ["shapes_scene.png", "Image (PNG)", "1280 × 800", "–", "3 red, 2 orange, 2 yellow, 3 green, 3 blue, 2 purple shapes"],
    ["ball_collection.jpg", "Image (JPG)", "1000 × 640", "–", "4 red, 3 blue, 2 green shaded balls"],
    ["neutral_scene.png", "Image (PNG)", "900 × 600", "–", "None (white, grey and black only; negative test)"],
    ["moving_objects.mp4", "Video (MP4)", "640 × 360", "200 / 25 fps", "2 red, 1 blue, 1 green, 1 yellow moving; short occlusion"],
    ["orbiting_ball.avi", "Video (AVI)", "480 × 360", "120 / 30 fps", "1 orange ball on a circular path"],
  ], [2.2, 1.4, 1.4, 1.5, 4.5]),
  ...figure(PF + "p_dataset.png", "Sample Dataset Used for Testing", null, 520, 230),

  H2("9.2 Colour space conversion (BGR to HSV)"),
  P("OpenCV loads images in BGR order. Each image or frame is converted to HSV with cv2.cvtColor(image, cv2.COLOR_BGR2HSV). In OpenCV, the hue channel ranges from 0 to 179 (the 0°–360° colour wheel divided by two), while saturation and value range from 0 to 255. Because hue describes the colour independently of brightness, a single hue range can describe a colour under different lighting, and minimum saturation and value thresholds can reject grey, white and very dark pixels."),
  H2("9.3 HSV thresholding and colour presets"),
  PK("A binary mask is produced with cv2.inRange(hsv, lower, upper), which sets a pixel to 255 when all three channels lie within the range and to 0 otherwise. The following presets are provided; each can be fine-tuned from the interface:"),
  ...table(["Colour", "Hue range", "Saturation", "Value"], [
    ["Red", "0–10 and 170–179", "120–255", "70–255"],
    ["Orange", "11–20", "120–255", "100–255"],
    ["Yellow", "21–34", "100–255", "100–255"],
    ["Green", "35–85", "60–255", "50–255"],
    ["Blue", "95–128", "80–255", "50–255"],
    ["Purple", "129–160", "60–255", "50–255"],
  ], [2, 3, 2.5, 2.5]),
  P("**Dual-range red detection:** Red hues lie near 0 and also near 179, at the two ends of the hue circle. A single interval cannot cover both ends, so two masks are created and combined with a bitwise OR: mask = inRange(hsv, (0, S, V), (10, 255, 255)) OR inRange(hsv, (170, S, V), (179, 255, 255)). An automated test confirms that a single red range misses objects at one end of the hue circle, while the dual range detects both."),
  H2("9.4 Morphological operations"),
  P("The raw mask usually contains isolated noise pixels and small holes. Morphological operations with a 5 × 5 elliptical structuring element (adjustable from 3 to 11) are used to clean it:"),
  ...bullets([
    "**Erosion:** shrinks white regions and removes small noise pixels.",
    "**Dilation:** grows white regions and fills small gaps.",
    "**Opening (erosion followed by dilation):** removes small noise while keeping the size of larger objects.",
    "**Closing (dilation followed by erosion):** fills small holes inside objects.",
  ]),
  P("The final mask is obtained by applying opening followed by closing. The erosion and dilation results are also shown in the interface for comparison."),
  ...figure(FG + "fig_pipeline_stages.png", "Stages of the Image Processing Pipeline (Red Preset)", "The stages are generated from the real pipeline on shapes_scene.png: original image, raw mask, erosion, dilation, final mask and detected objects.", 600, 280),
  H2("9.5 Contour detection and object localisation"),
  P("The external contours of the cleaned mask are found with cv2.findContours using RETR_EXTERNAL and CHAIN_APPROX_SIMPLE. Contours with an area below the minimum area (300 px for images and 250 px for videos by default) are discarded as noise. For each remaining object the system calculates:"),
  ...bullets([
    "**Bounding box:** x, y, width and height from cv2.boundingRect.",
    "**Area:** the contour area in pixels from cv2.contourArea.",
    "**Centroid:** from the image moments, cx = M10 / M00 and cy = M01 / M00 (the box centre is used if M00 is zero).",
  ]),
  P("Bounding boxes, labels with the object number and area, and centroid markers are drawn on the output image. The segmented image is produced with a bitwise AND of the original image and the mask."),
  H2("9.6 Centroid tracking algorithm"),
  P("For videos, a simple centroid-based multi-object tracker is used. It is not a deep learning tracker; it links detections between consecutive frames purely by the distance between their centroids. For each frame:"),
  ...numbered([
    "Receive the list of centroids detected in the current frame.",
    "Compute the Euclidean distance between every existing track and every new centroid.",
    "Match pairs greedily, closest first, as long as the distance is below the maximum match distance (80 px by default).",
    "Start a new track with a new ID for every unmatched detection.",
    "Mark every unmatched track as disappeared; remove it when it has been missing for more than the allowed number of frames (15 by default).",
  ]),
  P("Step 5 lets an object keep its ID through short missed detections such as brief occlusions. The tracker also stores the path of each object, which is used to draw motion trails and trajectory charts and to calculate the path length."),
  H2("9.7 Video processing"),
  P("OpenCV's VideoCapture reads the uploaded video frame by frame. Frames wider than 960 px are resized to keep processing fast. Each frame passes through the detection pipeline and the tracker, and the annotated frame, with boxes, IDs, trails and a status bar, is written to two output files: WebM (VP8), which plays directly in the browser, and MP4 (mp4v) for desktop players. Per-frame results (object count and processing time) are collected for the analytics and for the CSV export."),
  H2("9.8 Result analysis"),
  P("For images the system reports the number of objects, the area of each object, the colour coverage (percentage of pixels in the final mask), the colour distribution and the hue spectrum. For videos it reports frames processed, frames with detections, detection frequency, unique track IDs, objects per frame, processing time per frame, trajectories and track lifetimes. All values are calculated from the actual run; when no run has been made, the Analytics page shows an empty state instead of placeholder values."),

  H1("10. Implementation Details"),
  H2("10.1 Development environment"),
  P("**Python virtual environment:** The project runs in a Python 3.12 virtual environment on Windows. The dependencies are listed in requirements.txt and installed with pip install -r requirements.txt."),
  P("**Streamlit application:** The application is started with streamlit run app.py and opens in the browser at http://localhost:8501. Uploaded files and processed outputs are stored in a temporary folder for each session, and folders older than 12 hours are cleaned up automatically."),
  P("The code is organised into the modules described in Section 8.1: color_ranges.py, image_processing.py, video_processing.py, object_tracking.py and analytics.py, with the interface in app.py, components/ and views/."),
  H2("10.2 Application features"),
  ...bullets([
    "Five pages: Overview, Image Analysis, Video Tracking, Analytics & Insights and About Project.",
    "Image upload (JPG, JPEG, PNG) and video upload (MP4, AVI, MOV), with a sample demo mode.",
    "Six colour presets with fine-tune sliders, a custom HSV range and adjustable processing parameters.",
    "Side-by-side original, mask and processed image; bounding boxes, centroids, track IDs and motion trails.",
    "Downloads for the processed image, mask, segmented image, tracked video (WebM and MP4) and CSV reports.",
    "Clear error messages for invalid files and an information message when no object is found.",
  ]),

  H1("11. Testing and Observation"),
  H2("11.1 Application test cases"),
  PK("The following test cases were run against the application in a real browser using the sample images and videos. All 22 end-to-end checks passed; the main cases are listed below."),
  ...table(["Test case", "Expected behaviour", "Observation"], [
    ["Run the sample image demo (shapes_scene.png, Red)", "Three red objects should be detected.", "3 objects detected; coverage 4.81%; boxes and centroids drawn."],
    ["Upload ball_collection.jpg and select Red", "Four red balls should be detected.", "4 objects detected."],
    ["Analyse neutral_scene.png", "No object should be found and a message shown.", "Information message shown; no false detections."],
    ["Upload a non-image file renamed as .png", "A clear error message should be shown.", "Error message shown; the application kept running."],
    ["Run the sample video demo (moving_objects.mp4, Red)", "Two red balls should keep two IDs.", "200 frames processed; 2 unique IDs maintained."],
    ["Download the processed image and videos", "PNG, WebM and MP4 files should download.", "All three files downloaded."],
    ["Open Analytics & Insights after the runs", "Image and video metrics should be shown.", "Metrics and charts displayed from the latest runs."],
  ], [3.2, 3.3, 3.5]),
  H2("11.2 Automated unit tests"),
  PK("The core modules are tested with pytest. All 34 tests passed (34 passed in 5.93 s)."),
  ...table(["Test file", "Tests", "What is tested", "Result"], [
    ["test_image_processing.py", 17, "Red at both hue ends, blue and green detection, multiple objects, no-match case, invalid input, opening and closing, minimum area, resizing, colour distribution.", "17 passed"],
    ["test_tracking.py", 6, "Consistent IDs, survival through short occlusion, removal after the limit, new IDs for far or new objects, path length.", "6 passed"],
    ["test_video_processing.py", 11, "Video information, AVI and MOV input, tracking of two red balls, single orange ball, readable outputs, no detections, resizing, invalid and empty files, preview.", "11 passed"],
    ["Total", 34, "", "34 passed"],
  ], [2.6, 0.9, 5, 1.5]),
  H2("11.3 Image detection results"),
  PK("The detected object counts were compared with the ground truth for each sample image and colour:"),
  ...table(["Image", "Colour", "Expected", "Detected", "Match", "Coverage", "Time"], imageRows, [2.4, 1.6, 1.1, 1.1, 0.9, 1.2, 1.1]),
  P("All 15 image–colour combinations matched the ground truth. The first run (29.4 ms) includes start-up overhead; the remaining runs took between 4.4 and 8.7 ms."),
  H2("11.4 Video tracking results"),
  ...table(["Video", "Colour", "Frames", "Frames with detections", "Expected objects", "Unique IDs", "Avg time / frame"], videoRows,
    [2.3, 1.1, 1, 1.9, 1.3, 1.1, 1.5]),
  P(`The number of unique IDs matched the expected number of objects in every case, and no objects were detected for Purple, which is not present in the video. Red track 1 was seen in ${redVideo.tracks_detail[0]["Frames seen"]} of ${redVideo.frames} frames: it was hidden for 9 frames but kept the same ID because the gap was shorter than the 15-frame limit.`),
  H2("11.5 Output screenshots"),
  ...figure(PF + "p_image_results.png", "Image Detection Results", "The system detected 3 red objects with 4.81% coverage and showed the original image, binary mask and bounding boxes with download options.", 520, 300),
  ...figure(PF + "p_video_results.png", "Video Tracking Results", "The system processed 200 frames at 9.9 ms per frame and tracked the two red balls with 2 unique IDs.", 520, 300),
  ...figure(PF + "p_tracking_grid.png", "Tracked Frames from the Output Video", "Each red ball keeps its ID and motion trail; between frames 96 and 101 track 1 is briefly hidden and keeps the same ID when it reappears.", 560, 220),
  ...figure(PF + "p_an_img_1.png", "Analytics – Image Colour Distribution", "The colour composition and colour families of the analysed image are calculated from its pixels.", 520, 300),

  H1("12. Limitations"),
  ...bullets([
    "Detection depends only on colour, so different objects of the same colour cannot be told apart.",
    "Strong lighting changes, shadows, reflections and colour casts may move pixels outside the HSV range.",
    "Low saturation colours (pastels) and colours close to white, grey or black are difficult to separate.",
    "Objects of the same colour that touch or overlap are merged into a single contour.",
    "The centroid tracker can swap IDs when two objects cross closely, and objects hidden for longer than the allowed frames receive a new ID.",
    "The presets are tuned on the bundled synthetic samples; real-world scenes may need fine-tuning with the sliders.",
  ]),

  H1("13. Conclusion and Future Enhancements"),
  H2("13.1 Conclusion"),
  P("Chromatic Vision demonstrates the application of classical image processing techniques to colour detection and object tracking. The system converts images and video frames to the HSV colour space, segments the target colour with HSV thresholding (including dual-range red), cleans the mask with morphological operations, and locates objects with contour analysis, bounding boxes and centroids. A centroid tracker keeps consistent IDs for moving objects in videos."),
  P(`On the sample dataset the detected counts matched the ground truth for all 15 image–colour combinations, every sample video produced the expected number of track IDs, and the 200-frame video was processed at about ${redVideo.avg_ms.toFixed(1)} ms per frame on a CPU. The Streamlit application presents the results with real analytics and downloadable outputs, and the system was verified with 34 unit tests and 22 end-to-end checks.`),
  P("This project provides practical experience in colour spaces, image segmentation, morphological processing, contour analysis, object tracking, video analytics, testing and web application development."),
  H2("13.2 Future enhancements"),
  P("The project can be improved in the following ways:"),
  ...bullets([
    "**Live Camera Input:** Process webcam or CCTV streams in real time.",
    "**Multiple Colours at Once:** Detect and track several colours in a single pass.",
    "**Adaptive Thresholds:** Adjust the HSV ranges automatically to the lighting of each scene.",
    "**Better Tracking:** Use the Hungarian algorithm or a Kalman filter to reduce ID swaps when objects cross.",
    "**Object Separation:** Use the watershed algorithm to separate touching objects of the same colour.",
    "**Real-World Evaluation:** Tune and evaluate the presets on a labelled set of real photographs and videos.",
  ]),

  H1("References"),
  ...numbered([
    "Gonzalez, R. C. and Woods, R. E. Digital Image Processing, 4th ed. Pearson, 2018.",
    "Smith, A. R. “Color Gamut Transform Pairs.” ACM SIGGRAPH Computer Graphics, 12(3), 1978, pp. 12–19.",
    "Suzuki, S. and Abe, K. “Topological Structural Analysis of Digitized Binary Images by Border Following.” Computer Vision, Graphics, and Image Processing, 30(1), 1985, pp. 32–46.",
    "OpenCV Documentation – Changing Colorspaces. https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html",
    "OpenCV Documentation – Morphological Transformations. https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html",
    "OpenCV Documentation – Contour Features (moments, bounding rectangle). https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html",
    "OpenCV Documentation – VideoCapture Class. https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html",
    "Streamlit Documentation. https://docs.streamlit.io/",
    "Plotly Python Documentation. https://plotly.com/python/",
    "NumPy Documentation. https://numpy.org/doc/",
  ], AlignmentType.LEFT),
];

// ---------------------------------------------------------------- document
const pageBorder = { style: BorderStyle.SINGLE, size: 6, color: "404040", space: 24 };
const doc = new Document({
  creator: "Azmaan Pasha",
  title: "Chromatic Vision – Intelligent Color Detection and Object Tracking",
  styles: {
    default: { document: { run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 259 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: "000000" },
        paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, keepLines: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "000000" },
        paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, keepLines: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1000, bottom: 1000, left: MARGIN_LR, right: MARGIN_LR, footer: 480 },
        borders: { pageBorderTop: pageBorder, pageBorderBottom: pageBorder, pageBorderLeft: pageBorder, pageBorderRight: pageBorder,
          pageBorders: { display: PageBorderDisplay.ALL_PAGES, offsetFrom: PageBorderOffsetFrom.PAGE, zOrder: PageBorderZOrder.FRONT } },
      },
    },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: [...cover, ...body],
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, figNo, "figures"); });
