"""About Project: in-app documentation of the problem, method and techniques."""

from __future__ import annotations

import streamlit as st

from components.ui_components import card_title, flow_diagram, page_header, render

TECHNIQUES = [
    ("01", "Image loading", "The uploaded bytes are decoded into a NumPy array of pixels in BGR order "
     "(OpenCV's default).", "cv2.imdecode()"),
    ("02", "BGR → HSV conversion", "HSV separates colour (Hue) from colour strength (Saturation) and "
     "brightness (Value), so shadows and highlights change V but not H.", "cv2.cvtColor(img, COLOR_BGR2HSV)"),
    ("03", "HSV colour segmentation", "A colour is described as a box in HSV space: a hue interval plus "
     "minimum saturation and brightness.", "lower = (H1,S1,V1), upper = (H2,S2,V2)"),
    ("04", "Thresholding", "Every pixel inside the HSV box becomes 255 (white), everything else 0 (black). "
     "Red uses two boxes joined with OR.", "cv2.inRange(hsv, lower, upper)"),
    ("05", "Binary masking", "The mask selects only the target pixels from the original image, producing "
     "the segmented view.", "cv2.bitwise_and(img, img, mask=mask)"),
    ("06", "Erosion", "Shrinks white regions by removing boundary pixels - tiny noise specks disappear.",
     "cv2.erode()"),
    ("07", "Dilation", "Grows white regions - small gaps and cracks inside objects are filled.",
     "cv2.dilate()"),
    ("08", "Morphological opening", "Erosion followed by dilation: removes noise while keeping the size of "
     "real objects.", "cv2.morphologyEx(MORPH_OPEN)"),
    ("09", "Morphological closing", "Dilation followed by erosion: closes small holes inside objects "
     "(e.g. highlights on a shiny ball).", "cv2.morphologyEx(MORPH_CLOSE)"),
    ("10", "Contour detection", "Traces the outline of every connected white region in the mask. Regions "
     "below the minimum area are discarded.", "cv2.findContours(RETR_EXTERNAL)"),
    ("11", "Bounding boxes", "The smallest upright rectangle around each contour gives the object's "
     "position and size.", "cv2.boundingRect()"),
    ("12", "Centroid calculation", "The centre of mass of a contour from image moments: "
     "cx = M10 / M00, cy = M01 / M00.", "cv2.moments()"),
    ("13", "Frame-by-frame processing", "The video is read one frame at a time; steps 2-12 run on each "
     "frame and the annotated frame is written to the output file.", "cv2.VideoCapture / VideoWriter"),
    ("14", "Centroid-based tracking", "Centroids in the new frame are matched to existing tracks by the "
     "smallest Euclidean distance. Unmatched detections get new IDs; tracks missing too long are removed.",
     "CentroidTracker.update()"),
]


def render_about() -> None:
    page_header("About the Project",
                "Chromatic Vision - Intelligent Color Detection and Object Tracking Using Image Processing "
                "Techniques. A B.Tech mini-project for Image and Video Analytics.", "book", "Documentation")

    tabs = st.tabs([":material/info: Introduction", ":material/science: Techniques",
                    ":material/account_tree: Architecture", ":material/function: Algorithm",
                    ":material/rocket_launch: Applications & scope"])

    # ------------------------------------------------------------------
    with tabs[0]:
        c1, c2 = st.columns([1.3, 1], gap="large")
        with c1:
            with st.container(key="card_ab_intro"):
                card_title("Project introduction", "info")
                render('<div class="cv-doc"><p>Colour is one of the simplest and most reliable cues for finding '
                       'objects in images. Chromatic Vision is a web application that detects objects of a chosen '
                       'colour in images and videos, measures them, and follows them as they move - using only '
                       'classical image processing (no deep learning, no cloud services).</p>'
                       '<p>The user uploads an image or video, picks a target colour (or defines a custom HSV range), '
                       'and the system produces a binary mask, bounding boxes, object counts, tracking IDs, '
                       'downloadable results and analytics charts.</p></div>')
            with st.container(key="card_ab_problem"):
                card_title("Problem statement", "target")
                render('<div class="cv-doc"><p>Manually counting and locating coloured objects in images, or '
                       'following them through video, is slow and error-prone. Thresholding directly in RGB is '
                       'unreliable because lighting changes all three channels at once. The project needs a '
                       'simple, explainable pipeline that segments colours robustly, removes noise, identifies '
                       'individual objects and keeps track of them between frames - in an interface that '
                       'non-experts can use.</p></div>')
        with c2:
            with st.container(key="card_ab_obj"):
                card_title("Objectives", "sparkles")
                render('<div class="cv-doc"><ol>'
                       '<li>Detect objects of a selected colour using HSV segmentation.</li>'
                       '<li>Clean masks with erosion, dilation, opening and closing.</li>'
                       '<li>Identify objects with contours, bounding boxes and centroids.</li>'
                       '<li>Process videos frame by frame and track objects with consistent IDs.</li>'
                       '<li>Present results through visual analytics computed from real data.</li>'
                       '<li>Allow downloading processed images, masks, videos and CSV data.</li>'
                       '</ol></div>')
            with st.container(key="card_ab_tech"):
                card_title("Technologies used", "cpu")
                render('<div class="cv-tech-grid" style="grid-template-columns:1fr 1fr">'
                       '<div class="cv-tech"><b>Python 3.10+</b><p>Core language</p></div>'
                       '<div class="cv-tech"><b>OpenCV</b><p>Image &amp; video processing</p></div>'
                       '<div class="cv-tech"><b>NumPy</b><p>Pixel arrays, distances</p></div>'
                       '<div class="cv-tech"><b>Streamlit</b><p>Web interface</p></div>'
                       '<div class="cv-tech"><b>Plotly</b><p>Interactive charts</p></div>'
                       '<div class="cv-tech"><b>Matplotlib · Pillow</b><p>Static plots, imaging</p></div>'
                       '</div>')

    # ------------------------------------------------------------------
    with tabs[1]:
        render('<p style="color:#94A3B8;margin:0 0 14px 0">The fourteen image-processing techniques implemented '
               'in <code>modules/</code>, explained in simple terms.</p>')
        cards = "".join(
            f'<div class="cv-tech"><div class="k">TECHNIQUE {n}</div><b>{t}</b><p>{d}</p><code>{c}</code></div>'
            for n, t, d, c in TECHNIQUES)
        render(f'<div class="cv-tech-grid">{cards}</div>')
        st.write("")
        with st.container(key="card_ab_red"):
            card_title("Why red needs two HSV ranges", "palette")
            render('<div class="cv-doc"><p>OpenCV stores hue from 0 to 179 (the 360° colour wheel halved). '
                   'Red sits where the wheel wraps around - at both 0 and 179. A single interval such as '
                   '[170, 10] is impossible, so red is detected with <code>[0, 10]</code> OR '
                   '<code>[170, 179]</code> and the two masks are merged with <code>cv2.bitwise_or</code>.</p>'
                   '</div><div class="cv-hue-bar"><div class="sel" style="left:0%;width:5.6%"></div>'
                   '<div class="sel" style="left:95%;width:5%"></div></div>')

    # ------------------------------------------------------------------
    with tabs[2]:
        with st.container(key="card_ab_flow"):
            card_title("Processing workflow", "route", "image & per video frame")
            flow_diagram([
                ("Input", "Upload image or video, or load a sample", "JPG · PNG · MP4 · AVI · MOV"),
                ("HSV conversion", "Separate colour from brightness", "cvtColor"),
                ("Threshold", "Binary mask of the target colour", "inRange"),
                ("Morphology", "Opening removes noise, closing fills holes", "morphologyEx"),
                ("Contours", "Outline, box, area and centroid per object", "findContours"),
                ("Tracking", "Match centroids between frames (video)", "CentroidTracker"),
                ("Output", "Annotated media, analytics and downloads", "PNG · WebM · MP4 · CSV"),
            ])
        st.write("")
        with st.container(key="card_ab_arch"):
            card_title("System architecture", "layers", "three layers")
            render(
                '<div class="cv-arch">'
                '<div class="cv-arch-layer"><div class="t" style="color:#7DD3FC">Presentation layer · Streamlit</div>'
                '<div class="cv-arch-items"><div>app.py<small>Page config, routing</small></div>'
                '<div>components/<small>Sidebar, colour picker, UI kit, state</small></div>'
                '<div>views/<small>Overview, Image, Video, Analytics, About</small></div>'
                '<div>styles/main.css<small>Custom dark theme</small></div></div></div>'
                '<div class="cv-arch-down">▼ ▲</div>'
                '<div class="cv-arch-layer"><div class="t" style="color:#C4B5FD">Processing layer · modules/</div>'
                '<div class="cv-arch-items"><div>color_ranges.py<small>HSV presets, red dual range</small></div>'
                '<div>image_processing.py<small>Mask, morphology, contours</small></div>'
                '<div>video_processing.py<small>Frame loop, encoding</small></div>'
                '<div>object_tracking.py<small>Centroid tracker</small></div>'
                '<div>analytics.py<small>Distributions, charts</small></div></div></div>'
                '<div class="cv-arch-down">▼ ▲</div>'
                '<div class="cv-arch-layer"><div class="t" style="color:#86EFAC">Foundation · libraries &amp; storage</div>'
                '<div class="cv-arch-items"><div>OpenCV · NumPy<small>Vision &amp; arrays</small></div>'
                '<div>Plotly · Matplotlib<small>Visualisation</small></div>'
                '<div>Session state<small>Results, statistics</small></div>'
                '<div>outputs/sessions/<small>Temporary uploads &amp; videos</small></div></div></div>'
                '</div>')
        st.write("")
        with st.container(key="card_ab_method"):
            card_title("Methodology", "book")
            render('<div class="cv-doc"><ol>'
                   '<li><b>Requirement study</b> - identify colour detection and tracking needs of the course.</li>'
                   '<li><b>Colour model selection</b> - choose HSV over RGB for robustness to lighting.</li>'
                   '<li><b>Threshold tuning</b> - define presets for six colours from standard HSV hue bands, verified '
                   'on the bundled sample images; '
                   'expose sliders for fine-tuning.</li>'
                   '<li><b>Noise handling</b> - apply opening then closing with an elliptical kernel; drop '
                   'contours below a minimum area.</li>'
                   '<li><b>Tracking design</b> - greedy nearest-centroid matching with a distance gate and a '
                   'disappearance counter.</li>'
                   '<li><b>Interface &amp; analytics</b> - build the Streamlit app and charts from computed results.</li>'
                   '<li><b>Testing</b> - automated pytest cases with known ground truth plus automated browser '
                   'tests of the real interface.</li>'
                   '</ol></div>')

    # ------------------------------------------------------------------
    with tabs[3]:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            with st.container(key="card_ab_alg1"):
                card_title("Algorithm 1 · Colour object detection", "scan")
                st.code(
                    "Input : image I (BGR), HSV ranges R, kernel k, min area A\n"
                    "Output: list of objects, annotated image\n\n"
                    "1. HSV  <- cvtColor(I, BGR2HSV)\n"
                    "2. M    <- zeros(size of I)\n"
                    "3. for each (lower, upper) in R:\n"
                    "       M <- M OR inRange(HSV, lower, upper)\n"
                    "4. M    <- open(M, k)      # remove noise\n"
                    "5. M    <- close(M, k)     # fill holes\n"
                    "6. C    <- findContours(M, external)\n"
                    "7. for each contour c in C:\n"
                    "       if area(c) >= A:\n"
                    "           (x,y,w,h) <- boundingRect(c)\n"
                    "           (cx,cy)   <- moments(c)\n"
                    "           draw box and label on I\n"
                    "8. return objects, I", language="text")
        with c2:
            with st.container(key="card_ab_alg2"):
                card_title("Algorithm 2 · Centroid tracking", "route")
                st.code(
                    "Input : detections D_t (centroids) for frame t\n"
                    "State : tracks T (id, centroid, missing)\n\n"
                    "1. if D_t empty: missing += 1 for all T\n"
                    "2. if T empty: create a new track per D_t\n"
                    "3. Dist[i][j] <- ||T_i - D_j||   (Euclidean)\n"
                    "4. for pairs (i,j) sorted by Dist ascending:\n"
                    "       if i or j already used: skip\n"
                    "       if Dist[i][j] > max_distance: stop\n"
                    "       T_i.centroid <- D_j ; T_i.missing <- 0\n"
                    "5. unmatched T_i : missing += 1\n"
                    "       if missing > max_disappeared: delete\n"
                    "6. unmatched D_j : new track with next ID\n"
                    "7. draw box, ID and trail for matched tracks", language="text")
        st.info("The tracker is a classical centroid-matching method. It does not use deep learning, Kalman "
                "filtering or appearance features, so IDs can swap when two same-coloured objects cross very "
                "closely.", icon=":material/info:")

    # ------------------------------------------------------------------
    with tabs[4]:
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            with st.container(key="card_ab_apps"):
                card_title("Applications", "sparkles")
                render('<div class="cv-doc"><ul>'
                       '<li>Sorting fruits or products by colour on conveyor belts</li>'
                       '<li>Ball tracking in sports and physics experiments</li>'
                       '<li>Counting coloured components in quality inspection</li>'
                       '<li>Colour-marker tracking for robotics and gesture input</li>'
                       '<li>Traffic-light and signboard colour analysis</li>'
                       '<li>Teaching image processing concepts visually</li></ul></div>')
        with c2:
            with st.container(key="card_ab_lim"):
                card_title("Limitations", "info")
                render('<div class="cv-doc"><ul>'
                       '<li>Fixed HSV thresholds are sensitive to strong colour casts and very low light.</li>'
                       '<li>Touching objects of the same colour merge into one contour.</li>'
                       '<li>Background regions of the same colour are detected as objects.</li>'
                       '<li>Centroid matching can swap IDs when similar objects cross.</li>'
                       '<li>Processing runs on the CPU, so long HD videos take time.</li></ul></div>')
        with c3:
            with st.container(key="card_ab_future"):
                card_title("Future enhancements", "zap")
                render('<div class="cv-doc"><ul>'
                       '<li>Live webcam processing</li>'
                       '<li>Kalman-filter prediction for smoother tracks</li>'
                       '<li>Watershed segmentation to split touching objects</li>'
                       '<li>Automatic threshold calibration from a clicked pixel</li>'
                       '<li>Deep-learning detectors for shape-aware recognition</li>'
                       '<li>Exportable PDF analysis reports</li></ul></div>')
