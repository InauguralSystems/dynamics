#!/usr/bin/env python3
"""Mouse + render-decode oracle for the orbit lab (dynamics#20 rung 1).

A stubbed-gfx suite stays green while every real interaction is broken
(the #599 lesson), and the byte-identical trajectory oracle deliberately
never looks at what a user sees. So this launches the REAL orbit-lab
window, drives REAL pointer and key input with xdotool, and verifies by
reading pixels back:

  1. running  -> two grabs of the plot differ            (the sim is live)
  2. Pause    -> two grabs are pixel-identical           (advancement froze)
  3. unpause  -> the plot changes again                  (pause was a freeze,
                                                          not a hang)
  4. drag     -> the plot changes                        (pan is wired)
  5. wheel    -> the plot changes AND the decoded "zoom xN" label moves
                 off "zoom x1"                           (zoom is wired)
  6. `r`      -> the plot is pixel-identical to the pre-pan frame and the
                 label is back to "zoom x1"              (reset restores)
  7. slider   -> the decoded "zeta = ..." label leaves its startup value
                                                         (the slider drives zeta)

Step 2 is also what validates the comparator: a checker that called every
frame "changed" would fail it, and one that called every frame "the same"
would fail steps 1/3/4/5.

The session runs the real interactive entry, `run_session(zeta, -1, "")`,
at zeta = 0 rather than orbit_main.eigs's 0.15 — the SAME code path with
a different parameter. A damped orbit reaches its fixed point within
seconds of the window opening, and a still orbit cannot tell a working
Pause from a dead one; undamped, "is it advancing" stays answerable for
the whole session. The zeta drag is last for the same reason: it puts
damping back.

Text is decoded exactly, not OCR'd: the bitmap font (forced via a
nonexistent EIGS_GFX_FONT) is a fixed atlas on a 12x14 px cell grid at
scale 2, and lib/ui draws a label's text at exactly the label's origin.

Whether pan/zoom perturbs the SIMULATION is a separate, deterministic
question answered by tests/orbit_ui_pan_dump.eigs (byte-identical
trajectory with the view moving every frame) — this file is about
whether the controls respond at all.

The checker is validated by planted faults rather than trusted: run with
`--fault pan` (mousedown never claims the drag), `--fault pause` (the
tick advances even when paused), or `--fault mode` (the view never changes)
and the corresponding check MUST go red. The wrapper drives all four runs.

Assumes an X display (the wrapper uses xvfb-run). Needs the gfx build
(EIGENSCRIPT), xdotool, xwd, PIL.
"""
import os, re, struct, subprocess, sys, tempfile, time, shutil
from PIL import Image

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, SDL_VIDEODRIVER="x11",
           EIGS_GFX_FONT="/nonexistent/force-bitmap.ttf")

TITLE = "dynamics - orbit lab"
CELL_W, CELL_H = 12, 14                     # scale-2 bitmap glyph grid
CHARSET = "".join(chr(c) for c in range(33, 127))
INK = lambda r, g, b: min(r, g, b) > 150

# orbit.eigs geometry (window coords): canvas, and the two labels this
# oracle decodes — side panel at (460, 12), labels at panel-relative
# (8, 66) and (8, 186).
CANVAS = (12, 12, 436, 446)
ZETA_LABEL_XY = (468, 78)
ZOOM_LABEL_XY = (468, 198)
SLIDER = (468, 100, 192)                    # x, y (centre), width
# Slice 3: the view selector at panel-relative (8, 412, 192, 26), and the
# first caption of the bifurcation control column at panel-relative
# (8, 60) — a slot the phase-portrait column leaves blank, so decoding it
# reads the CURRENT view rather than a label that exists in both.
MODE_BTN = (564, 437)
BIF_LABEL_XY = (468, 72)
CHANGED_MIN = 100                           # pixels: a redraw of the whole plot
# Advancement is measured against a noise floor the run itself pins: the
# paused checks below come back at EXACTLY 0 differing pixels, twice, so a
# nonzero difference is genuine motion. It has to be judged that way — a
# damped orbit shrinks toward the fixed point, so late in a session "the
# simulation is still advancing" is only a handful of pixels.
ADVANCE_MIN = 1
ACTION_TIMEOUT = 8.0
POLL_INTERVAL = 0.05


# ---------- X plumbing ----------

def xdo(*args, timeout=3.0, search=False):
    if not search:
        print("XDO send %r monotonic=%.6f" % (args, time.monotonic()), flush=True)
    result = subprocess.run(["xdotool"] + [str(a) for a in args], env=ENV,
                            capture_output=True, text=True, timeout=timeout)
    # Search rc1 means no matching window yet, not a successful input.
    if result.returncode != 0 and not (search and result.returncode == 1):
        raise RuntimeError("xdotool %r rc%d: %s" %
                           (args, result.returncode, result.stderr.strip()))
    return result.stdout


def app_output(proc):
    with open(proc.output_path) as fh:
        return fh.read()[-8000:]


def ensure_live(proc):
    if proc.poll() is not None:
        raise RuntimeError("app exited rc%d: %s" % (proc.returncode, app_output(proc)))


def start_app(args, cwd, tmp, name):
    path = os.path.join(tmp, name + ".log")
    with open(path, "w") as log:
        proc = subprocess.Popen([EIGS] + args, cwd=cwd, env=ENV,
                                stdout=log, stderr=subprocess.STDOUT, text=True)
    proc.output_path = path
    return proc


def stop_app(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def xwd_to_image(path):
    d = open(path, "rb").read()
    f = struct.unpack(">25I", d[:100])
    hs, pw, ph, bpl, ncolors = f[0], f[4], f[5], f[12], f[19]
    off = hs + ncolors * 12
    img = Image.new("RGB", (pw, ph)); px = img.load()
    for y in range(ph):
        row = off + y * bpl
        for x in range(pw):
            p = struct.unpack_from("<I", d, row + x * 4)[0]
            px[x, y] = ((p >> 16) & 255, (p >> 8) & 255, p & 255)
    return img


def has_content(img):
    px = img.load(); W, H = img.size
    lit = 0
    for y in range(0, H, 3):
        for x in range(0, W, 3):
            if INK(*px[x, y]):
                lit += 1
                if lit > 40:
                    return True
    return False


def wait_for_window(proc, title):
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        ensure_live(proc)
        windows = xdo("search", "--all", "--onlyvisible", "--pid", proc.pid,
                      "--name", "^" + re.escape(title) + "$", search=True,
                      timeout=min(3.0, max(0.01, deadline - time.monotonic())))
        if windows.strip():
            return windows.strip().splitlines()[0]
        time.sleep(min(POLL_INTERVAL, max(0, deadline - time.monotonic())))
    # Never read a live stdout pipe on timeout: that would defeat the bound.
    raise RuntimeError("window deadline expired: " + app_output(proc))


def window_origin(wid):
    g = xdo("getwindowgeometry", wid)
    for line in g.splitlines():
        if "Position:" in line:
            xy = line.split("Position:")[1].split("(")[0].strip()
            return tuple(int(v) for v in xy.split(","))
    raise RuntimeError("no window position for " + wid)


class CaptureDeadline(RuntimeError):
    pass


def grab(wid, tmp, proc, deadline=None):
    action_deadline = deadline is not None
    deadline = deadline if deadline is not None else time.monotonic() + ACTION_TIMEOUT
    xwd = os.path.join(tmp, "g.xwd")
    while time.monotonic() < deadline:
        ensure_live(proc)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        deadline_limited = action_deadline and remaining < 3.0
        try:
            cap = subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV,
                                 capture_output=True, timeout=min(3.0, remaining))
        except subprocess.TimeoutExpired:
            if deadline_limited and time.monotonic() >= deadline:
                raise CaptureDeadline("visible action deadline during capture")
            raise
        if cap.returncode != 0:
            raise RuntimeError("xwd rc%d: %s" %
                               (cap.returncode, cap.stderr.decode(errors="replace")))
        img = xwd_to_image(xwd)
        if has_content(img):
            return img
        time.sleep(min(POLL_INTERVAL, max(0, deadline - time.monotonic())))
    if action_deadline:
        raise CaptureDeadline("visible action deadline before capture")
    raise RuntimeError("could not capture the window")


# ---------- pixel helpers ----------

def region_diff(a, b, rect):
    """Number of differing pixels inside rect ((x, y, w, h))."""
    x, y, w, h = rect
    pa, pb = a.load(), b.load()
    n = 0
    for j in range(y, y + h):
        for i in range(x, x + w):
            if pa[i, j] != pb[i, j]:
                n += 1
    return n


def cell_sig(px, cx, cy):
    return frozenset((dx, dy) for dy in range(CELL_H) for dx in range(CELL_W)
                     if INK(*px[cx + dx, cy + dy]))


def build_atlas(tmp):
    """Render the charset through the real gfx_text and map glyph -> char."""
    app = os.path.join(tmp, "atlas.eigs")
    w = CELL_W * len(CHARSET) + 40
    with open(app, "w") as fh:
        fh.write('ok is gfx_open of [%d, 40, "orbit-atlas"]\n'
                 'n is 0\n'
                 'loop while n < 400:\n'
                 '    gfx_clear of [16, 18, 28]\n'
                 '    gfx_text of [8, 8, "%s", 230, 233, 240, 2]\n'
                 '    gfx_present of null\n'
                 '    gfx_delay of 16\n'
                 '    n is n + 1\n'
                 'gfx_close of null\n' % (w, CHARSET.replace("\\", "\\\\").replace('"', '\\"')))
    proc = start_app([app], REPO, tmp, "atlas")
    try:
        wid = wait_for_window(proc, "orbit-atlas")
        img = grab(wid, tmp, proc)
        px = img.load()
        atlas = {cell_sig(px, 8 + k * CELL_W, 8): ch for k, ch in enumerate(CHARSET)}
        atlas[frozenset()] = " "        # blank cell — a real space in the label
        return atlas
    finally:
        stop_app(proc)


def decode_line(img, atlas, xy, n=22):
    px = img.load(); W, H = img.size
    x, y = xy
    s = ""
    for k in range(n):
        cx = x + k * CELL_W
        if cx + CELL_W > W or y + CELL_H > H:
            break
        s += atlas.get(cell_sig(px, cx, y), "�")
    return s.strip()


# ---------- the run ----------

# Planted faults: (needle, replacement) applied to the app tree's copy of
# orbit.eigs. Each must make its check go red — that is what separates
# this from a golden master.
FAULTS = {
    # mousedown never claims the pointer, so the drag never pans.
    "pan": ("        _drag.active is 1\n", "        _drag.active is 0\n"),
    # the tick advances the simulation even while paused.
    "pause": ("    if _app.paused == 0:\n", "    if _app.paused == 0 or 1 == 1:\n"),
    # the view selector's handler fires but switches nothing — the class
    # of bug where "a handler ran" is mistaken for "the UI changed".
    "mode": ('    if w.value == 1:\n        return set_mode of "bif"\n',
             '    if w.value == 1:\n        return null\n'),
}


def build_tree(tmp, fault):
    """Copy the app under test into tmp, optionally with a planted fault."""
    tree = os.path.join(tmp, "app")
    os.makedirs(tree)
    for name in ("orbit.eigs", "orbit_theme.eigs", "physics.eigs", "logistic.eigs"):
        shutil.copy(os.path.join(REPO, name), os.path.join(tree, name))
    if fault:
        needle, repl = FAULTS[fault]
        path = os.path.join(tree, "orbit.eigs")
        src = open(path).read()
        if needle not in src:
            raise RuntimeError("planted fault %r no longer matches orbit.eigs" % fault)
        open(path, "w").write(src.replace(needle, repl, 1))
    # Read-only acknowledgement through the existing post-event frame hook.
    # This lives ONLY in the disposable app copy. Production input handlers,
    # simulation and rendering remain unchanged; a tick is not a pixel verdict.
    with open(os.path.join(tree, "orbit.eigs"), "a") as fh:
        fh.write('\ndefine mouse_qa_ack(sim) as:\n'
                 '    write_text of ["mouse-qa-state", '
                 'f"{_app.ticks}|{sim.frame}|{_app.paused}|{_app.mode}|END\\n"]\n'
                 '    return null\n')
    with open(os.path.join(tree, "orbit_qa.eigs"), "w") as fh:
        fh.write("import orbit\norbit.set_frame_hook of orbit.mouse_qa_ack\n"
                 "orbit.run_session of [0.0, 0 - 1, \"\"]\n")
    return tree


def main():
    sys.stdout.reconfigure(line_buffering=True)
    fault = None
    stop_on_fail = "--stop-on-fail" in sys.argv
    if "--fault" in sys.argv:
        fault = sys.argv[sys.argv.index("--fault") + 1]
        if fault not in FAULTS:
            raise SystemExit("unknown fault %r; known: %s" % (fault, ", ".join(FAULTS)))
        print("=== planted fault: %s (the matching check MUST go red) ===" % fault)

    tmp = tempfile.mkdtemp()
    fails = []
    class Stop(Exception):
        pass

    def check(ok, msg):
        print(("PASS " if ok else "FAIL ") + msg)
        if not ok:
            fails.append(msg)
            if stop_on_fail:
                raise Stop()

    proc = None
    infrastructure_error = None
    evidence_root = os.environ.get("ORBIT_MOUSE_ARTIFACTS")
    evidence = None
    if evidence_root:
        os.makedirs(evidence_root, exist_ok=True)
        evidence = tempfile.mkdtemp(prefix=(fault or "clean") + "-", dir=evidence_root)
        print("evidence: " + evidence)
    try:
        atlas = build_atlas(tmp)
        print("atlas: %d glyphs" % len(atlas))

        tree = build_tree(tmp, fault)
        proc = start_app(["orbit_qa.eigs"], tree, tmp, "orbit")
        wid = wait_for_window(proc, TITLE)
        print("window %s at %r" % (wid, window_origin(wid)))

        def state():
            ensure_live(proc)
            try:
                with open(os.path.join(tree, "mouse-qa-state")) as fh:
                    fields = fh.read().strip().split("|")
                if len(fields) != 5 or fields[4] != "END":
                    return None       # write_text may be between truncate/write
                ticks, frame, paused = map(int, fields[:3])
                if ticks < 1 or frame < 0 or paused not in (0, 1) or fields[3] not in ("orbit", "bif"):
                    return None
                return dict(ticks=ticks, frame=frame, paused=paused, mode=fields[3])
            except (FileNotFoundError, ValueError):
                return None

        def wait_state(name, predicate, duration=0.0):
            started = time.monotonic()
            deadline = started + ACTION_TIMEOUT
            last = None
            while time.monotonic() < deadline:
                last = state()
                if last is not None and predicate(last) and time.monotonic() - started >= duration:
                    print("ACK %s monotonic=%.6f elapsed=%.3f state=%r" %
                          (name, time.monotonic(), time.monotonic() - started, last))
                    return last
                time.sleep(min(POLL_INTERVAL, max(0, deadline - time.monotonic())))
            raise RuntimeError("%s acknowledgement deadline; last=%r" % (name, last))

        def ticks_after(name, before, duration=0.0):
            return wait_state(name, lambda s: s["ticks"] >= before["ticks"] + 3, duration)

        def snapshot(name, deadline=None):
            img = grab(wid, tmp, proc, deadline)
            print("CAPTURE %s monotonic=%.6f state=%r" % (name, time.monotonic(), state()))
            if evidence:
                img.save(os.path.join(evidence, name + ".png"))
            return img

        def visible(name, predicate, before):
            # Poll the postcondition, never resend input. A live newer tick is
            # required in addition to pixels; a frozen stale frame cannot pass.
            started = time.monotonic()
            deadline = started + ACTION_TIMEOUT
            last = None
            seen = None
            captured_state = None
            while time.monotonic() < deadline:
                seen = state()
                if seen is not None and seen["ticks"] > before["ticks"]:
                    try:
                        last = grab(wid, tmp, proc, deadline)
                    except CaptureDeadline:
                        ensure_live(proc)
                        break
                    captured_state = seen
                    if predicate(last, seen):
                        print("VISIBLE %s monotonic=%.6f elapsed=%.3f state=%r" %
                              (name, time.monotonic(), time.monotonic() - started, seen))
                        if evidence:
                            last.save(os.path.join(evidence, name + ".png"))
                        return last, seen
                time.sleep(min(POLL_INTERVAL, max(0, deadline - time.monotonic())))
            print("DEADLINE %s monotonic=%.6f state=%r" % (name, time.monotonic(), seen))
            if last is None:
                raise RuntimeError(name + ": no live newer frame before deadline")
            if evidence:
                last.save(os.path.join(evidence, name + "-deadline.png"))
            # Return the failing sample to the existing named pixel assertion.
            return last, captured_state

        ready = wait_state("startup", lambda s: s["mode"] == "orbit" and s["paused"] == 0)

        # Window-relative pointer moves: `getwindowgeometry` reports the
        # FRAME position under a window manager, so adding it to a client
        # coordinate misses every thin control by the title-bar height.
        def mv(wx, wy):
            xdo("mousemove", "--window", wid, wx, wy)

        def click_at(wx, wy):
            mv(wx, wy); xdo("click", "1")
            print("INPUT click (%d,%d) monotonic=%.6f" % (wx, wy, time.monotonic()))

        def drag(path, hold=0.12):
            # Gesture pacing keeps native stepped motion; it is never used
            # as evidence that an action completed. The visible waiter is.
            mv(*path[0]); xdo("mousedown", "1"); time.sleep(hold)
            for wx, wy in path[1:]:
                mv(wx, wy); time.sleep(hold)
            xdo("mouseup", "1")
            print("INPUT drag monotonic=%.6f" % time.monotonic())

        def key(k):
            xdo("key", "--window", wid, k)
            print("INPUT key %s monotonic=%.6f" % (k, time.monotonic()))

        def pause_to(value):
            before = wait_state("before-space", lambda s: True)
            if before["paused"] == value:
                raise RuntimeError("unexpected pause state before space: %r" % before)
            key("space")
            ack = wait_state("space-%d" % value,
                             lambda s: s["ticks"] > before["ticks"] and s["paused"] == value)
            # The hook precedes drawing. A following tick witnesses completion
            # of the acknowledged tick's render before its pixels are compared.
            settled = ticks_after("space-rendered", ack)
            if settled["paused"] != value:
                raise RuntimeError("pause state changed again before capture")
            return settled

        cx, cy = CANVAS[0] + CANVAS[2] // 2, CANVAS[1] + CANVAS[3] // 2

        # 1. running: consecutive frames of the plot differ. Checked first,
        # while the orbit is still wide — it decays toward the fixed point
        # from the moment the window opens.
        run_a = snapshot("running-before")
        run_b, running = visible("running", lambda img, s:
                                 s["frame"] > ready["frame"] and
                                 region_diff(run_a, img, CANVAS) >= ADVANCE_MIN, ready)
        d = region_diff(run_a, run_b, CANVAS)
        check(d >= ADVANCE_MIN and running["frame"] > ready["frame"],
              "running: the plot advances between frames (%d px differ)" % d)

        # Park focus on the canvas up front (lib/ui draws a focus ring on
        # the focused widget, so focus must not move mid-comparison), and
        # leave the pointer over the plot — the wheel event carries no
        # cursor position, so the app anchors zoom on the last hover.
        click_at(cx, cy)
        ticks_after("canvas-focus-rendered", running)

        start = snapshot("startup-labels")
        base_zeta = decode_line(start, atlas, ZETA_LABEL_XY)
        base_zoom = decode_line(start, atlas, ZOOM_LABEL_XY)
        print("decoded labels at startup: %r / %r" % (base_zeta, base_zoom))
        check(base_zeta == "zeta = 0", "render-decode: zeta label reads %r" % base_zeta)
        check(base_zoom == "zoom x1", "render-decode: zoom label reads %r" % base_zoom)

        # 2. pause: consecutive frames are pixel-identical.
        paused = pause_to(1)
        paused_a = snapshot("pause-before")
        frozen = ticks_after("pause-observation", paused, duration=0.4)
        paused_b = snapshot("pause-after")
        d = region_diff(paused_a, paused_b, CANVAS)
        check(d == 0 and frozen["frame"] == paused["frame"] and frozen["paused"] == 1,
              "pause: advancement freezes — live ticks over >=0.4s are identical (%d px differ)" % d)

        # 3. unpause: the plot advances again (Pause froze it, nothing hung).
        resumed = pause_to(0)
        run_c = snapshot("unpause-before")
        run_d, advanced = visible("unpause", lambda img, s:
                                 s["frame"] > resumed["frame"] and
                                 region_diff(run_c, img, CANVAS) >= ADVANCE_MIN, resumed)
        d = region_diff(run_c, run_d, CANVAS)
        check(d >= ADVANCE_MIN and advanced["frame"] > resumed["frame"],
              "unpause: advancement resumes (%d px differ)" % d)

        # Freeze again for the view tests: pan/zoom/reset must be judged
        # against a still simulation.
        paused = pause_to(1)
        paused_b = snapshot("pre-pan")

        # 4. drag to pan (real press, stepped motion, release).
        drag([(cx, cy), (cx - 30, cy - 12), (cx - 60, cy - 24), (cx - 90, cy - 36)])
        panned, panned_state = visible("pan", lambda img, s:
                                      region_diff(paused_b, img, CANVAS) > CHANGED_MIN, paused)
        d = region_diff(paused_b, panned, CANVAS)
        check(d > CHANGED_MIN, "drag: panning redraws the plot while paused (%d px differ)" % d)

        # 5. wheel to zoom.
        mv(cx, cy)
        xdo("click", "4")
        xdo("click", "4")
        print("INPUT wheel monotonic=%.6f" % time.monotonic())
        zoomed, zoomed_state = visible("zoom", lambda img, s:
                                      region_diff(panned, img, CANVAS) > CHANGED_MIN and
                                      decode_line(img, atlas, ZOOM_LABEL_XY) != base_zoom and
                                      decode_line(img, atlas, ZOOM_LABEL_XY).startswith("zoom x"),
                                      panned_state)
        d = region_diff(panned, zoomed, CANVAS)
        check(d > CHANGED_MIN, "wheel: zooming redraws the plot (%d px differ)" % d)
        zoom_txt = decode_line(zoomed, atlas, ZOOM_LABEL_XY)
        print("decoded zoom label after 2 wheel steps: %r" % zoom_txt)
        check(zoom_txt != base_zoom and zoom_txt.startswith("zoom x"),
              "render-decode: zoom label moved off %r to %r" % (base_zoom, zoom_txt))

        # 6. reset restores the exact pre-pan view.
        key("r")
        reset, reset_state = visible("reset", lambda img, s:
                                    region_diff(paused_b, img, CANVAS) == 0 and
                                    decode_line(img, atlas, ZOOM_LABEL_XY) == base_zoom, zoomed_state)
        d = region_diff(paused_b, reset, CANVAS)
        check(d == 0, "reset: `r` restores the pre-pan plot pixel-for-pixel (%d px differ)" % d)
        check(decode_line(reset, atlas, ZOOM_LABEL_XY) == base_zoom,
              "render-decode: zoom label back to %r after reset" % base_zoom)

        # 7. slider drag changes zeta (read off the rendered label).
        sx, sy, sw = SLIDER
        drag([(sx + 8, sy), (sx + sw // 2, sy), (sx + sw - 20, sy)])
        after_slider, slider_state = visible("slider", lambda img, s:
                                            decode_line(img, atlas, ZETA_LABEL_XY).startswith("zeta =") and
                                            decode_line(img, atlas, ZETA_LABEL_XY) != base_zeta,
                                            reset_state)
        zeta_txt = decode_line(after_slider, atlas, ZETA_LABEL_XY)
        print("decoded zeta label after slider drag: %r" % zeta_txt)
        check(zeta_txt.startswith("zeta =") and zeta_txt != base_zeta,
              "slider: dragging moves zeta %r -> %r" % (base_zeta, zeta_txt))

        # 8. the view selector (slice 3). Clicking it must swap the phase
        # portrait for the bifurcation chart — verified in PIXELS on both
        # halves of the window: the control column decodes to the
        # bifurcation captions, and the plot area is redrawn wholesale.
        # Then the diagram must be STATIC: two frames 0.4 s apart
        # pixel-identical is the visible face of "the bifurcation tick
        # does no per-frame work", which is what the memory gate
        # (tests/test_bif_mem.sh) measures in RSS.
        before_toggle = snapshot("pre-mode")
        click_at(*MODE_BTN)
        bif, bif_state = visible("mode-bif", lambda img, s:
                                 decode_line(img, atlas, BIF_LABEL_XY) == "logistic map" and
                                 region_diff(before_toggle, img, CANVAS) > CHANGED_MIN, slider_state)
        bif_txt = decode_line(bif, atlas, BIF_LABEL_XY)
        print("decoded bifurcation column: %r" % bif_txt)
        check(bif_txt == "logistic map",
              "mode: the control column reads %r after the view toggle" % bif_txt)
        d = region_diff(before_toggle, bif, CANVAS)
        check(d > CHANGED_MIN,
              "mode: the plot area is redrawn as the bifurcation chart (%d px differ)" % d)
        ticks_after("bif-observation", bif_state, duration=0.4)
        bif_b = snapshot("bif-static")
        d = region_diff(bif, bif_b, CANVAS)
        check(d == 0,
              "mode: the bifurcation diagram is static between frames (%d px differ)" % d)

        # 9. toggling back restores the phase portrait — the pre-existing
        # view must survive a round trip through the new one.
        click_at(*MODE_BTN)
        back, _ = visible("mode-orbit", lambda img, s:
                          decode_line(img, atlas, ZETA_LABEL_XY) == zeta_txt and
                          region_diff(before_toggle, img, CANVAS) == 0, bif_state)
        back_txt = decode_line(back, atlas, ZETA_LABEL_XY)
        print("decoded zeta label after toggling back: %r" % back_txt)
        check(back_txt == zeta_txt,
              "mode: toggling back restores the phase-portrait column (%r)" % back_txt)
        d = region_diff(before_toggle, back, CANVAS)
        check(d == 0,
              "mode: the phase portrait comes back pixel-for-pixel (%d px differ)" % d)

    except Stop:
        print("(stopping at the first failure)")
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        infrastructure_error = str(exc)
        print("ERROR mouse oracle: " + infrastructure_error)
    finally:
        if proc is not None:
            stop_app(proc)
        if evidence:
            for name in ("orbit.log", "atlas.log"):
                path = os.path.join(tmp, name)
                if os.path.exists(path):
                    shutil.copy(path, evidence)
        shutil.rmtree(tmp, ignore_errors=True)

    if infrastructure_error is not None:
        sys.exit(2)
    if fails:
        print("\n%d mouse-oracle failure(s)" % len(fails))
        sys.exit(1)
    print("\nall mouse + render-decode checks passed")


if __name__ == "__main__":
    main()
