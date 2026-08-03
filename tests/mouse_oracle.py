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
`--fault pan` (mousedown never claims the drag) or `--fault pause` (the
tick advances even when paused) and the corresponding check MUST go red.
tests/test_orbit_mouse.sh drives all three runs.

Assumes an X display (the wrapper uses xvfb-run). Needs the gfx build
(EIGENSCRIPT), xdotool, xwd, PIL.
"""
import os, struct, subprocess, sys, tempfile, time, shutil
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
CHANGED_MIN = 100                           # pixels: a redraw of the whole plot
# Advancement is measured against a noise floor the run itself pins: the
# paused checks below come back at EXACTLY 0 differing pixels, twice, so a
# nonzero difference is genuine motion. It has to be judged that way — a
# damped orbit shrinks toward the fixed point, so late in a session "the
# simulation is still advancing" is only a handful of pixels.
ADVANCE_MIN = 1


# ---------- X plumbing ----------

def xdo(*args):
    subprocess.run(["xdotool"] + [str(a) for a in args], env=ENV, check=False)


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
    for _ in range(150):            # up to ~30s: window mapping is high-variance
        time.sleep(0.2)
        r = subprocess.run(["xdotool", "search", "--name", title],
                           env=ENV, capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip().split("\n")[0]
        if proc.poll() is not None:
            raise RuntimeError("app exited early: " + (proc.stdout.read() or ""))
    raise RuntimeError("window never appeared: " + (proc.stdout.read() or ""))


def window_origin(wid):
    g = subprocess.run(["xdotool", "getwindowgeometry", wid], env=ENV,
                       capture_output=True, text=True).stdout
    for line in g.splitlines():
        if "Position:" in line:
            xy = line.split("Position:")[1].split("(")[0].strip()
            return tuple(int(v) for v in xy.split(","))
    raise RuntimeError("no window position for " + wid)


def grab(wid, tmp):
    xwd = os.path.join(tmp, "g.xwd")
    for _ in range(30):
        time.sleep(0.15)
        cap = subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV,
                             capture_output=True)
        if cap.returncode != 0:
            continue                        # transient X error mid-map — retry
        img = xwd_to_image(xwd)
        if has_content(img):
            return img
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
    proc = subprocess.Popen([EIGS, app], cwd=REPO, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wid = wait_for_window(proc, "orbit-atlas")
        img = grab(wid, tmp)
        px = img.load()
        atlas = {cell_sig(px, 8 + k * CELL_W, 8): ch for k, ch in enumerate(CHARSET)}
        atlas[frozenset()] = " "        # blank cell — a real space in the label
        return atlas
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


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
}


def build_tree(tmp, fault):
    """Copy the app under test into tmp, optionally with a planted fault."""
    tree = os.path.join(tmp, "app")
    os.makedirs(tree)
    for name in ("orbit.eigs", "orbit_theme.eigs", "physics.eigs"):
        shutil.copy(os.path.join(REPO, name), os.path.join(tree, name))
    if fault:
        needle, repl = FAULTS[fault]
        path = os.path.join(tree, "orbit.eigs")
        src = open(path).read()
        if needle not in src:
            raise RuntimeError("planted fault %r no longer matches orbit.eigs" % fault)
        open(path, "w").write(src.replace(needle, repl, 1))
    with open(os.path.join(tree, "orbit_qa.eigs"), "w") as fh:
        fh.write("import orbit\norbit.run_session of [0.0, 0 - 1, \"\"]\n")
    return tree


def main():
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
    try:
        atlas = build_atlas(tmp)
        print("atlas: %d glyphs" % len(atlas))

        tree = build_tree(tmp, fault)
        proc = subprocess.Popen([EIGS, "orbit_qa.eigs"], cwd=tree, env=ENV,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        wid = wait_for_window(proc, TITLE)
        print("window %s at %r" % (wid, window_origin(wid)))

        # Window-relative pointer moves: `getwindowgeometry` reports the
        # FRAME position under a window manager, so adding it to a client
        # coordinate misses every thin control by the title-bar height.
        def mv(wx, wy):
            xdo("mousemove", "--window", wid, wx, wy)

        def click_at(wx, wy):
            mv(wx, wy); xdo("click", "1"); time.sleep(0.25)

        def drag(path, hold=0.12):
            mv(*path[0]); xdo("mousedown", "1"); time.sleep(hold)
            for wx, wy in path[1:]:
                mv(wx, wy); time.sleep(hold)
            xdo("mouseup", "1"); time.sleep(0.25)

        def key(k):
            xdo("key", "--window", wid, k); time.sleep(0.35)

        cx, cy = CANVAS[0] + CANVAS[2] // 2, CANVAS[1] + CANVAS[3] // 2

        # 1. running: consecutive frames of the plot differ. Checked first,
        # while the orbit is still wide — it decays toward the fixed point
        # from the moment the window opens.
        run_a = grab(wid, tmp)
        time.sleep(0.4)
        run_b = grab(wid, tmp)
        d = region_diff(run_a, run_b, CANVAS)
        check(d >= ADVANCE_MIN, "running: the plot advances between frames (%d px differ)" % d)

        # Park focus on the canvas up front (lib/ui draws a focus ring on
        # the focused widget, so focus must not move mid-comparison), and
        # leave the pointer over the plot — the wheel event carries no
        # cursor position, so the app anchors zoom on the last hover.
        click_at(cx, cy)

        start = grab(wid, tmp)
        base_zeta = decode_line(start, atlas, ZETA_LABEL_XY)
        base_zoom = decode_line(start, atlas, ZOOM_LABEL_XY)
        print("decoded labels at startup: %r / %r" % (base_zeta, base_zoom))
        check(base_zeta == "zeta = 0", "render-decode: zeta label reads %r" % base_zeta)
        check(base_zoom == "zoom x1", "render-decode: zoom label reads %r" % base_zoom)

        # 2. pause: consecutive frames are pixel-identical.
        key("space")
        paused_a = grab(wid, tmp)
        time.sleep(0.4)
        paused_b = grab(wid, tmp)
        d = region_diff(paused_a, paused_b, CANVAS)
        check(d == 0, "pause: advancement freezes — two frames 0.4s apart are identical (%d px differ)" % d)

        # 3. unpause: the plot advances again (Pause froze it, nothing hung).
        key("space")
        run_c = grab(wid, tmp)
        time.sleep(0.4)
        run_d = grab(wid, tmp)
        d = region_diff(run_c, run_d, CANVAS)
        check(d >= ADVANCE_MIN, "unpause: advancement resumes (%d px differ)" % d)

        # Freeze again for the view tests: pan/zoom/reset must be judged
        # against a still simulation.
        key("space")
        paused_b = grab(wid, tmp)

        # 4. drag to pan (real press, stepped motion, release).
        drag([(cx, cy), (cx - 30, cy - 12), (cx - 60, cy - 24), (cx - 90, cy - 36)])
        panned = grab(wid, tmp)
        d = region_diff(paused_b, panned, CANVAS)
        check(d > CHANGED_MIN, "drag: panning redraws the plot while paused (%d px differ)" % d)

        # 5. wheel to zoom.
        mv(cx, cy); time.sleep(0.2)
        xdo("click", "4"); time.sleep(0.2)
        xdo("click", "4"); time.sleep(0.35)
        zoomed = grab(wid, tmp)
        d = region_diff(panned, zoomed, CANVAS)
        check(d > CHANGED_MIN, "wheel: zooming redraws the plot (%d px differ)" % d)
        zoom_txt = decode_line(zoomed, atlas, ZOOM_LABEL_XY)
        print("decoded zoom label after 2 wheel steps: %r" % zoom_txt)
        check(zoom_txt != base_zoom and zoom_txt.startswith("zoom x"),
              "render-decode: zoom label moved off %r to %r" % (base_zoom, zoom_txt))

        # 6. reset restores the exact pre-pan view.
        key("r")
        reset = grab(wid, tmp)
        d = region_diff(paused_b, reset, CANVAS)
        check(d == 0, "reset: `r` restores the pre-pan plot pixel-for-pixel (%d px differ)" % d)
        check(decode_line(reset, atlas, ZOOM_LABEL_XY) == base_zoom,
              "render-decode: zoom label back to %r after reset" % base_zoom)

        # 7. slider drag changes zeta (read off the rendered label).
        sx, sy, sw = SLIDER
        drag([(sx + 8, sy), (sx + sw // 2, sy), (sx + sw - 20, sy)])
        after_slider = grab(wid, tmp)
        zeta_txt = decode_line(after_slider, atlas, ZETA_LABEL_XY)
        print("decoded zeta label after slider drag: %r" % zeta_txt)
        check(zeta_txt.startswith("zeta =") and zeta_txt != base_zeta,
              "slider: dragging moves zeta %r -> %r" % (base_zeta, zeta_txt))

    except Stop:
        print("(stopping at the first failure)")
    finally:
        if proc is not None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("\n%d mouse-oracle failure(s)" % len(fails))
        sys.exit(1)
    print("\nall mouse + render-decode checks passed")


if __name__ == "__main__":
    main()
