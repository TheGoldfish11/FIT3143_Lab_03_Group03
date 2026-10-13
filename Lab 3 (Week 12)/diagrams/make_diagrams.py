# FIT3143 Lab 3 - slide diagrams for the EV charging WSN (Tasks 1 and 2)
# Julia Mallard, Nam Quang Tran (Lab 03, Group 03)
#
# Writes svg/*.svg (1280x720, slide-shaped). Run: python3 make_diagrams.py
# Colours are the same in every diagram:
#   blue  = charging node / node<->node messages
#   amber = base station / node<->base messages
#   green = charging ports, good outcome
#   red   = congested node
#   grey  = shutdown messages, ruled out, notes

import os
from html import escape

W, H = 1280, 720
FONT = "'Public Sans', 'Liberation Sans', Arial, sans-serif"
MONO = "'JetBrains Mono', 'DejaVu Sans Mono', monospace"

C = {
    'ink': '#1f2430', 'muted': '#5d6577', 'faint': '#c9ced8',
    'blue': '#3563a8', 'blue_bg': '#eaf1fb', 'blue_bg2': '#d9e5f7', 'blue_wash': '#f6f9fd',
    'amber': '#b4600e', 'amber_bg': '#fff1e0', 'amber_wash': '#fffaf3',
    'green': '#2f7d4a', 'green_bg': '#e4f3e9',
    'red': '#c0392b', 'red_bg': '#fdeaea',
    'grey': '#7d8597', 'grey_bg': '#f2f3f6',
    'white': '#ffffff',
}
MARKER_COLOURS = ['ink', 'blue', 'amber', 'green', 'red', 'grey']


class Svg:
    def __init__(self, label):
        self.label = label
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill='white', stroke='ink', rx=10, sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{C[fill] if fill in C else fill}" stroke="{C[stroke]}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=16, weight=400, anchor='middle', colour='ink', mono=False):
        fam = MONO if mono else FONT
        self.add(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" fill="{C[colour]}">{escape(s)}</text>')

    def lines(self, cx, cy, items, anchor='middle', x=None):
        # items: (text, size, weight, colour, mono); block is vertically centred on cy
        heights = [it[1] * 1.35 for it in items]
        y = cy - sum(heights) / 2
        for it, h in zip(items, heights):
            s, size, weight, colour, mono = it
            self.text(x if x is not None else cx, round(y + h * 0.74, 1), s, size, weight, anchor, colour, mono)
            y += h

    def box(self, x, y, w, h, items, fill='white', stroke='ink', rx=10, sw=2, dash=None):
        self.rect(x, y, w, h, fill, stroke, rx, sw, dash)
        self.lines(x + w / 2, y + h / 2, items)

    def diamond(self, cx, cy, w, h, items, fill='white', stroke='ink'):
        pts = f'{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}'
        self.add(f'<polygon points="{pts}" fill="{C[fill]}" stroke="{C[stroke]}" stroke-width="2"/>')
        self.lines(cx, cy, items)

    def arrow(self, pts, colour='ink', sw=2, dash=None, start=False, end=True, mid=False):
        p = ' '.join(f'{x},{y}' for x, y in pts)
        attrs = f'fill="none" stroke="{C[colour]}" stroke-width="{sw}" stroke-linejoin="round"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if end:
            attrs += f' marker-end="url(#ah-{colour})"'
        if start:
            attrs += f' marker-start="url(#ah-{colour})"'
        if mid:
            attrs += f' marker-mid="url(#ah-{colour})"'
        self.add(f'<polyline points="{p}" {attrs}/>')

    def pill(self, cx, cy, s, size=14, colour='ink', weight=400, mono=False, bg='white', stroke=None):
        # label on a background so it stays readable where it crosses lines
        w = len(s) * size * (0.62 if mono else 0.56) + 16
        h = size + 10
        st = f'stroke="{C[stroke]}" stroke-width="1.5"' if stroke else 'stroke="none"'
        self.add(f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" '
                 f'fill="{C[bg]}" {st}/>')
        self.text(cx, round(cy + size * 0.36, 1), s, size, weight, 'middle', colour, mono)

    def render(self):
        markers = ''.join(
            f'<marker id="ah-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="11" markerHeight="11" '
            f'markerUnits="userSpaceOnUse" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{C[c]}"/></marker>'
            for c in MARKER_COLOURS)
        body = '\n'.join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                f'role="img" aria-label="{escape(self.label)}">\n<defs>{markers}</defs>\n'
                f'<rect width="{W}" height="{H}" fill="#ffffff"/>\n{body}\n</svg>\n')


def T(s, size=16, weight=400, colour='ink', mono=False):
    return (s, size, weight, colour, mono)


# ---------------------------------------------------------------------------------------------
def architecture():
    s = Svg('A 3 by 3 Cartesian grid of charging node processes, each linked only to its neighbours, '
            'plus one base station process that every node reaches directly.')
    s.rect(24, 24, 1232, 672, 'white', 'grey', rx=14, sw=1.5, dash='6 5')
    s.text(48, 58, 'MPI_COMM_WORLD', 17, 700, 'start', mono=True)
    s.text(212, 58, 'mpirun -np m·n + 1   ·   ranks 0 … m·n−1 are nodes, rank m·n is the base station',
           15, 400, 'start', 'muted')

    s.rect(48, 80, 680, 592, 'blue_wash', 'blue', rx=12)
    s.text(72, 112, 'grid_comm', 18, 700, 'start', mono=True)
    s.text(196, 112, 'node ID = rank = x·n + y', 15, 400, 'start', 'muted')
    s.text(72, 136, 'MPI_Comm_split, then MPI_Cart_create(3 × 3, non-periodic, reorder = 0)',
           13, 400, 'start', 'muted', mono=True)

    ports = ['101101', '110111', '111111', '101111', '011110', '100110', '110111', '111110', '010011']
    xs, ys, bw, bh = [108, 318, 528], [166, 318, 470], 160, 104
    for r in range(3):
        for c in range(3):
            x, y, nid = xs[c], ys[r], r * 3 + c
            cx = x + bw / 2
            s.rect(x, y, bw, bh, 'white', 'blue')
            s.text(cx, y + 32, f'Node {nid}', 18, 700)
            s.text(cx, y + 55, f'({r},{c})', 14, 400, colour='muted', mono=True)
            for i, bit in enumerate(ports[nid]):
                px = cx - 63 + i * 22
                s.rect(px, y + 70, 16, 16, 'green' if bit == '1' else 'white', 'green', rx=3, sw=1.5)
            if c < 2:
                s.arrow([(x + bw + 2, y + bh / 2), (x + bw + 48, y + bh / 2)], 'blue', start=True)
            if r < 2:
                s.arrow([(cx, y + bh + 2), (cx, y + bh + 46)], 'blue', start=True)

    s.arrow([(72, 620), (124, 620)], 'blue', start=True)
    s.text(138, 625, 'neighbours only: NBR_REQ ⇄ NBR_RESP (found with MPI_Cart_shift)', 15, 400, 'start')
    s.rect(72, 642, 16, 16, 'green', 'green', rx=3, sw=1.5)
    s.text(96, 656, 'port in use', 15, 400, 'start')
    s.rect(196, 642, 16, 16, 'white', 'green', rx=3, sw=1.5)
    s.text(220, 656, 'port free', 15, 400, 'start')
    s.text(310, 656, '· each port is an OpenMP thread (k = 6 shown)', 15, 400, 'start', 'muted')

    s.box(900, 236, 330, 240, [
        T('Base station', 22, 700),
        T('rank m·n (= 9 here)', 14, 400, 'muted', True),
        T('', 8),
        T('1 MPI process, 1 thread', 16),
        T('polls with MPI_Iprobe', 16),
        T('finds the nearest free nodes', 16),
        T('writes base_station.log', 16),
    ], 'amber_bg', 'amber', rx=12)

    s.arrow([(730, 292), (898, 292)], 'amber')
    s.text(814, 282, 'REPORT', 14, 700, colour='amber', mono=True)
    s.arrow([(898, 338), (730, 338)], 'amber')
    s.text(814, 328, 'BASE_REPLY', 14, 700, colour='amber', mono=True)
    s.arrow([(898, 402), (730, 402)], 'grey', dash='6 4')
    s.text(814, 392, 'TERMINATE, FINAL', 13, 700, colour='grey', mono=True)
    s.arrow([(730, 448), (898, 448)], 'grey', dash='6 4')
    s.text(814, 438, 'TERM_ACK', 13, 700, colour='grey', mono=True)

    s.text(1065, 516, 'Any node talks to the base station', 15, 400, colour='muted')
    s.text(1065, 538, 'directly: no relaying through the grid', 15, 400, colour='muted')
    return s


# ---------------------------------------------------------------------------------------------
def node_internals():
    s = Svg('Inside one charging node process: k port threads each write their own slot of a shared '
            'array, and thread 0 reads it, keeps a history, and is the only thread that calls MPI.')
    s.rect(24, 24, 876, 672, 'blue_wash', 'blue', rx=14)
    s.text(48, 60, 'Node 4 (1,1): one MPI process', 20, 700, 'start')
    s.text(48, 86, '#pragma omp parallel num_threads(k + 1)   ·   k = 6 ports shown', 14, 400, 'start',
           'muted', mono=True)
    s.text(48, 126, 'Port threads 1 … k: each cycle, free → in use with p = 0.6, in use → free with p = 0.3',
           15, 400, 'start')

    centres = [115 + 134 * i for i in range(6)]
    values = [1, 0, 1, 1, 0, 1]
    for i, cx in enumerate(centres):
        s.box(cx - 61, 142, 122, 66, [T(f'thread {i + 1}', 13, 400, 'muted', True), T(f'port {i}', 17, 700)],
              'green_bg', 'green')
        s.arrow([(cx, 210), (cx, 294)], 'green')
    s.pill(452, 252, 'each thread writes only its own slot  ·  #pragma omp atomic write', 14)

    for i, cx in enumerate(centres):
        v = values[i]
        s.rect(cx - 67, 296, 134, 56, 'green_bg' if v else 'white', 'ink', rx=0, sw=1.5)
        s.text(cx, 322, str(v), 20, 700, mono=True)
        s.text(cx, 342, 'in use' if v else 'free', 13, 400, colour='muted')
    s.rect(48, 296, 804, 56, 'none', 'ink', rx=0, sw=2.5)
    s.text(48, 380, 'port_in_use[k]', 16, 700, 'start', mono=True)
    s.text(196, 380, 'shared by all k + 1 threads of this node', 15, 400, 'start', 'muted')

    s.arrow([(651, 354), (651, 428)], 'ink')
    s.text(638, 408, 'atomic read of every slot → free ports', 14, 400, 'end')

    s.rect(372, 430, 480, 240, 'blue_bg2', 'blue', sw=2.5)
    s.text(392, 462, 'thread 0: control thread', 18, 700, 'start')
    s.text(392, 486, 'the only thread that calls MPI (MPI_THREAD_FUNNELED)', 13, 400, 'start', 'muted', True)
    for j, line in enumerate([
        '• each cycle: count free ports, save to history',
        '• free ≤ threshold → NBR_REQ to every neighbour',
        '• all neighbours full → one REPORT to base station',
        '• receives with MPI_Iprobe + MPI_Recv, never waits',
        '• sends with MPI_Isend from a buffer pool',
        '• on FINAL: stops the port threads',
    ]):
        s.text(392, 522 + j * 26, line, 15, 400, 'start')

    s.rect(48, 430, 280, 240, 'grey_bg', 'grey')
    s.text(68, 462, 'history[256]', 17, 700, 'start', mono=True)
    s.text(68, 486, 'ring buffer, like Table 1', 14, 400, 'start', 'muted')
    s.text(68, 522, 'time', 13, 700, 'start', 'muted')
    s.text(300, 522, 'free ports', 13, 700, 'end', 'muted')
    for j, (t, a) in enumerate([('10:07:10', '1'), ('10:07:20', '6'), ('10:07:30', '5'),
                                ('10:07:40', '2'), ('10:07:50', '1')]):
        s.text(68, 550 + j * 26, t, 15, 400, 'start', mono=True)
        s.text(300, 550 + j * 26, a, 15, 400, 'end', mono=True)
    s.arrow([(372, 560), (330, 560)], 'ink')
    s.text(351, 550, 'saves', 12, 400, colour='muted')

    s.box(990, 300, 266, 120, [
        T('Neighbours (2–4)', 18, 700),
        T('found with MPI_Cart_shift', 13, 400, 'muted', True),
        T('⇄ NBR_REQ, NBR_RESP', 14, 400, 'blue', True),
    ], 'blue_bg', 'blue')
    s.arrow([(854, 460), (940, 460), (940, 360), (988, 360)], 'blue', start=True)

    s.box(990, 500, 266, 140, [
        T('Base station', 18, 700),
        T('→ REPORT, TERM_ACK', 14, 400, 'amber', True),
        T('← BASE_REPLY,', 14, 400, 'amber', True),
        T('   TERMINATE, FINAL', 14, 400, 'amber', True),
    ], 'amber_bg', 'amber')
    s.arrow([(854, 570), (988, 570)], 'amber', start=True)
    return s


# ---------------------------------------------------------------------------------------------
def node_flow():
    s = Svg('Thread 0 runs one loop that never blocks; a congestion incident is spread over several '
            'passes of that loop and ends in a redirect to a neighbour or one report to the base station.')
    s.rect(24, 24, 560, 672, 'blue_wash', 'faint', rx=14, sw=1.5)
    s.text(48, 60, 'Main loop of thread 0 (repeats until FINAL)', 18, 700, 'start')

    steps = [
        ('Handle every message that arrived', 'MPI_Iprobe → MPI_Recv, reply via MPI_Isend'),
        ('Every cycle (-c ms): count free ports', 'save (time, free) to history[]'),
        ('free ≤ threshold, no round open?', 'yes → start a round (right)'),
        ('Nothing handled? Sleep, then repeat', 'sleep_us(-i), default 1000 µs'),
    ]
    for i, (title, detail) in enumerate(steps):
        y = 90 + i * 130
        s.rect(100, y, 450, 96, 'white', 'blue')
        s.add(f'<circle cx="138" cy="{y + 48}" r="18" fill="{C["blue"]}"/>')
        s.text(138, y + 54, str(i + 1), 17, 700, colour='white')
        s.text(172, y + 42, title, 17, 700, 'start')
        s.text(172, y + 68, detail, 13, 400, 'start', 'muted', mono=True)
        if i < 3:
            s.arrow([(325, y + 96), (325, y + 128)], 'ink')
    s.arrow([(325, 576), (325, 616), (60, 616), (60, 138), (98, 138)], 'ink')
    s.text(192, 640, 'repeat', 14, 400, colour='muted')
    s.text(48, 676, 'Grey tags on the right name the loop step that does that work.', 13, 400, 'start', 'muted')

    s.rect(608, 24, 648, 672, 'white', 'faint', rx=14, sw=1.5)
    s.text(632, 60, 'One congestion incident (spans several passes)', 18, 700, 'start')

    s.box(712, 84, 440, 72, [T('Free ports ≤ threshold', 17, 700), T('e.g. 0 of 6 free, threshold = 1', 14, 400, 'muted')],
          'red_bg', 'red')
    s.arrow([(932, 156), (932, 184)], 'ink')
    s.box(712, 186, 440, 72, [T('NBR_REQ to each neighbour (2–4)', 17, 700),
                              T('MPI_Isend, then keep looping', 14, 400, 'muted')], 'blue_bg', 'blue')
    s.pill(1205, 222, 'loop step 3', 12, 'muted', bg='grey_bg', stroke='faint')
    s.arrow([(932, 258), (932, 304)], 'blue', dash='6 4')
    s.text(946, 287, 'NBR_RESP replies arrive', 14, 400, 'start', 'blue')
    s.pill(672, 330, 'loop step 1', 12, 'muted', bg='grey_bg', stroke='faint')

    s.diamond(932, 370, 420, 128, [T('All replies in.', 16, 700), T('Any neighbour above threshold?', 16)])
    s.arrow([(722, 370), (680, 370), (680, 468)], 'green')
    s.text(700, 360, 'yes', 14, 700, colour='green')
    s.arrow([(1142, 370), (1190, 370), (1190, 468)], 'amber')
    s.text(1166, 360, 'no', 14, 700, colour='amber')

    s.box(624, 470, 272, 112, [T('Redirect EVs', 17, 700), T('to the neighbour with', 14),
                               T('the most free ports', 14), T('no base station message', 13, 400, 'muted')],
          'green_bg', 'green')
    s.box(960, 470, 276, 100, [T('Send one REPORT', 17, 700), T('to the base station (104 B)', 14, 400, 'muted')],
          'amber_bg', 'amber')
    s.arrow([(1098, 570), (1098, 598)], 'amber')
    s.box(960, 600, 276, 80, [T('BASE_REPLY arrives', 16, 700), T('forward nearest nodes to EVs', 14)],
          'amber_bg', 'amber')
    s.pill(904, 640, 'loop step 1', 12, 'muted', bg='grey_bg', stroke='faint')
    return s


# ---------------------------------------------------------------------------------------------
def base_station():
    s = Svg('The base station is one thread polling for messages; each report is answered with every '
            'nearest available node or with no nodes nearby, and shutdown happens in two phases.')
    s.rect(24, 24, 420, 452, 'amber_wash', 'amber', rx=14)
    s.text(48, 58, 'Base station main loop', 18, 700, 'start')
    s.text(48, 80, '1 MPI process · 1 thread', 14, 400, 'start', 'muted')

    s.box(48, 98, 372, 82, [T('Poll for any message', 16, 700),
                            T('MPI_Iprobe(ANY_SOURCE, ANY_TAG)', 13, 400, 'ink', True),
                            T('nothing waiting → sleep -i µs', 13, 400, 'muted')], 'white', 'amber')
    s.arrow([(136, 180), (136, 228)], 'grey')
    s.arrow([(332, 180), (332, 228)], 'amber')
    s.box(48, 230, 176, 84, [T('TERM_ACK', 15, 700, 'grey', True), T('store node stats', 14), T('acks++', 13, 400, 'muted', True)],
          'white', 'grey')
    s.box(244, 230, 176, 84, [T('REPORT', 15, 700, 'amber', True), T('handle_report(R)', 14, 400, 'ink', True)],
          'white', 'amber')
    s.arrow([(136, 314), (136, 340), (36, 340), (36, 139), (46, 139)], 'ink')
    s.text(90, 334, 'loop', 13, 400, colour='muted')

    s.box(48, 364, 372, 92, [T('Remembers, per node', 15, 700),
                             T('last_report[]  known_avail[]  known_time[]', 13, 400, 'ink', True),
                             T('filled from reports only', 13, 400, 'muted')], 'grey_bg', 'grey')

    s.rect(468, 24, 788, 452, 'amber_wash', 'amber', rx=14)
    s.text(492, 58, 'handle_report(R)', 18, 700, 'start', mono=True)
    # drawn after the right panel so the panel does not cover it
    s.arrow([(420, 272), (484, 272), (484, 114), (498, 114)], 'amber')
    s.box(500, 84, 360, 60, [T('REPORT from node R', 16, 700),
                             T("R's and its neighbours' free ports", 13, 400, 'muted')], 'white', 'amber')
    s.arrow([(680, 144), (680, 162)], 'ink')
    s.diamond(680, 220, 380, 112, [T('Did every neighbour of R', 15, 700), T('report in the last w s?', 15, 700)])
    s.arrow([(870, 220), (928, 220)], 'amber')
    s.text(899, 210, 'yes', 14, 700, colour='amber')
    s.box(930, 180, 300, 80, [T('Reply: no nodes', 16, 700), T('available nearby', 16, 700)], 'amber_bg', 'amber')
    s.arrow([(680, 276), (680, 304)], 'green')
    s.text(694, 296, 'no', 14, 700, 'start', 'green')
    s.box(500, 306, 360, 92, [T('Search d = 2, 3, … hops out', 16, 700),
                              T('skip nodes that reported, or were', 13),
                              T('shown congested, in the last w s', 13)], 'white', 'ink')
    s.arrow([(860, 352), (928, 352)], 'green')
    s.box(930, 306, 300, 92, [T('Reply with ALL nodes', 16, 700), T('at the smallest distance d', 14),
                              T('(a tie returns several)', 13, 400, 'muted')], 'green_bg', 'green')
    s.arrow([(1080, 398), (1080, 418)], 'ink')
    s.arrow([(1230, 220), (1244, 220), (1244, 442), (1232, 442)], 'ink')
    s.box(500, 420, 730, 44, [T('update tables  ·  BASE_REPLY via MPI_Isend  ·  log the alert', 15)],
          'white', 'ink')

    s.text(24, 528, 'Shutdown in two phases, so no message is left unreceived', 17, 700, 'start')
    stages = [
        ('Run for -d seconds', 'answer every report', 'amber_bg', 'amber'),
        ('TERMINATE → all nodes', 'nodes stop new rounds', 'grey_bg', 'grey'),
        ('Wait for m·n TERM_ACKs', 'still answering reports', 'grey_bg', 'grey'),
        ('FINAL → all nodes', 'nothing left in flight', 'grey_bg', 'grey'),
        ('Summary to log', 'free memory, MPI_Finalize', 'grey_bg', 'grey'),
    ]
    for i, (a, b, fill, stroke) in enumerate(stages):
        x = 24 + i * 251
        s.box(x, 548, 226, 100, [T(a, 16, 700), T(b, 13, 400, 'muted')], fill, stroke)
        if i < 4:
            s.arrow([(x + 227, 598), (x + 249, 598)], 'ink')
    s.text(24, 684, 'MPI keeps messages between two processes in order, so a node always gets its last '
                    'BASE_REPLY before FINAL.', 14, 400, 'start', 'muted')
    return s


# ---------------------------------------------------------------------------------------------
def search_example():
    s = Svg('Two real alerts from the sample log: Node 0 is sent node 2 because nodes 4 and 6 had just '
            'reported; Node 3 is told nothing is nearby because all its neighbours had reported.')

    def panel(ox, title, sub, cells, result, result_colour, logline, why):
        s.rect(ox, 24, 604, 672, 'white', 'faint', rx=14, sw=1.5)
        s.text(ox + 24, 60, title, 20, 700, 'start')
        s.text(ox + 24, 86, sub, 15, 400, 'start', 'muted')
        styles = {
            'reporter': ('red_bg', 'red', 3, None, 'ink'),
            'nbr': ('amber_bg', 'amber', 2, None, 'ink'),
            'out': ('grey_bg', 'grey', 2, '6 4', 'muted'),
            'chosen': ('green_bg', 'green', 3, None, 'ink'),
            'skip': ('white', 'faint', 1.5, None, 'muted'),
        }
        x0 = ox + 46
        for (r, c), (nid, d, kind, l1, l2) in cells.items():
            x, y = x0 + c * 176, 110 + r * 134
            fill, stroke, sw, dash, tc = styles[kind]
            s.rect(x, y, 160, 118, fill, stroke, sw=sw, dash=dash)
            s.text(x + 12, y + 22, f'd={d}' if d else '', 13, 400, 'start', 'muted', True)
            s.text(x + 80, y + 50, f'Node {nid}', 18, 700, colour=tc)
            s.text(x + 80, y + 76, l1, 14, 400, colour=tc)
            s.text(x + 80, y + 98, l2, 14, 700 if kind in ('chosen', 'reporter') else 400, colour=tc)
        s.text(ox + 24, 546, result, 19, 700, 'start', result_colour)
        s.text(ox + 24, 574, logline, 13, 400, 'start', 'muted', True)
        for j, w in enumerate(why):
            s.text(ox + 24, 612 + j * 22, w, 15, 400, 'start')

    panel(24, 'Alert #5: Node 0 reports', 'sim time 16.008 s  ·  window w = 5 s', {
        (0, 0): (0, None, 'reporter', 'reporter', '0/6 free'),
        (0, 1): (1, 1, 'nbr', 'no recent report', '1/6 free'),
        (0, 2): (2, 2, 'chosen', 'last report 8.0 s ago', 'returned ✓'),
        (1, 0): (3, 1, 'nbr', 'no recent report', '1/6 free'),
        (1, 1): (4, 2, 'out', 'reported 16.006 s', 'ruled out'),
        (1, 2): (5, 3, 'skip', 'not searched', ''),
        (2, 0): (6, 2, 'out', 'reported 16.006 s', 'ruled out'),
        (2, 1): (7, 3, 'skip', 'not searched', ''),
        (2, 2): (8, 4, 'skip', 'not searched', ''),
    }, 'Reply → node 2 (distance 2)', 'green',
        'Decision : 1 nearest node(s) at distance 2: 2 (0,2)',
        ['Nodes 1 and 3 had not reported, so the base searches.',
         'Nodes 4 and 6 are also 2 hops away, but they had just',
         'reported, so they are probably full too.'])

    panel(652, 'Alert #6: Node 3 reports', 'same moment (16.008 s)  ·  w = 5 s', {
        (0, 0): (0, 1, 'nbr', 'reported 16.008 s', 'within w ✓'),
        (0, 1): (1, 2, 'skip', 'not checked', ''),
        (0, 2): (2, 3, 'skip', 'not checked', ''),
        (1, 0): (3, None, 'reporter', 'reporter', '1/6 free'),
        (1, 1): (4, 1, 'nbr', 'reported 16.006 s', 'within w ✓'),
        (1, 2): (5, 2, 'skip', 'not checked', ''),
        (2, 0): (6, 1, 'nbr', 'reported 16.006 s', 'within w ✓'),
        (2, 1): (7, 2, 'skip', 'not checked', ''),
        (2, 2): (8, 3, 'skip', 'not checked', ''),
    }, 'Reply → no nodes available nearby', 'amber',
        'Decision : all neighbours reported within 5.0 s',
        ['All three neighbours (0, 4, 6) reported within w.',
         'Their reports already covered the nodes beyond',
         'them, so there is nowhere close to send EVs.'])
    return s


# ---------------------------------------------------------------------------------------------
def sequence():
    s = Svg('Message sequence for one incident and for shutdown, with payload sizes and the timestamps '
            'used to measure round-trip delay.')
    lanes = {'n0': 230, 'n1': 520, 'n3': 760, 'b': 1100}
    heads = [('n0', 'Node 0', 'reporter', 'red_bg', 'red'), ('n1', 'Node 1', 'neighbour', 'blue_bg', 'blue'),
             ('n3', 'Node 3', 'neighbour', 'blue_bg', 'blue'), ('b', 'Base station', 'rank m·n', 'amber_bg', 'amber')]
    for key, a, b, fill, stroke in heads:
        x = lanes[key]
        s.box(x - 95, 28, 190, 58, [T(a, 17, 700), T(b, 13, 400, 'muted')], fill, stroke)
        s.add(f'<line x1="{x}" y1="86" x2="{x}" y2="644" stroke="{C["grey"]}" stroke-width="1.5" '
              f'stroke-dasharray="5 5"/>')

    n0, n1, n3, b = lanes['n0'], lanes['n1'], lanes['n3'], lanes['b']
    s.rect(n0 - 8, 112, 16, 330, 'blue_bg2', 'blue', rx=3, sw=1.5)

    def note(y, h, items, fill='grey_bg', stroke='grey'):
        s.box(24, y, 186, h, items, fill, stroke, rx=8, sw=1.5)

    note(104, 52, [T('0/6 free ≤ threshold', 13, 700), T('t1 = MPI_Wtime()', 13, 400, 'ink', True)], 'red_bg', 'red')
    s.arrow([(n0 + 8, 150), (n1, 150)], 'blue')
    s.pill((n0 + n1) / 2, 140, 'NBR_REQ · 12 B', 13, 'blue', 700, True)
    s.arrow([(n0 + 8, 182), (n3, 182)], 'blue')
    s.pill(640, 172, 'NBR_REQ · 12 B', 13, 'blue', 700, True)
    s.arrow([(n1, 226), (n0 + 8, 226)], 'blue')
    s.pill((n0 + n1) / 2, 216, 'NBR_RESP · 16 B, echoes t1', 13, 'blue', 700, True)
    s.arrow([(n3, 258), (n0 + 8, 258)], 'blue')
    s.pill(640, 248, 'NBR_RESP · 16 B', 13, 'blue', 700, True)
    note(234, 52, [T('neighbour delay', 13, 700), T('RTT = now − t1', 13, 400, 'ink', True)])

    note(312, 52, [T('all neighbours full', 13, 700), T('t2 = MPI_Wtime()', 13, 400, 'ink', True)], 'amber_bg', 'amber')
    s.arrow([(n0 + 8, 346), (b - 8, 346)], 'amber')
    s.pill(640, 336, 'REPORT · 104 B (one derived datatype)', 13, 'amber', 700, True)
    s.rect(b - 8, 346, 16, 56, 'amber_bg', 'amber', rx=3, sw=1.5)
    s.text(b + 20, 370, 'handle_report', 13, 400, 'start', mono=True)
    s.text(b + 20, 390, 'takes base_proc_s', 13, 400, 'start', 'muted')
    s.arrow([(b - 8, 404), (n0 + 8, 404)], 'amber')
    s.pill(640, 394, 'BASE_REPLY · 540 B, echoes t2 and base_proc_s', 13, 'amber', 700, True)
    note(392, 66, [T('report delay', 13, 700), T('RTT = now − t2', 13, 400, 'ink', True),
                   T('      − base_proc_s', 13, 400, 'ink', True)])

    s.add(f'<line x1="24" y1="486" x2="1256" y2="486" stroke="{C["grey"]}" stroke-width="1.5" stroke-dasharray="8 6"/>')
    s.pill(640, 486, 'after -d seconds: two-phase shutdown', 14, 'ink', 700, bg='grey_bg', stroke='faint')
    s.arrow([(b, 528), (n3, 528), (n1, 528), (n0, 528)], 'grey', mid=True)
    s.pill(930, 518, 'TERMINATE · 0 B → every node', 13, 'grey', 700, True)
    s.arrow([(n0, 572), (n1, 572), (n3, 572), (b, 572)], 'grey', mid=True)
    s.pill(930, 562, 'TERM_ACK · 140 B stats, one per node', 13, 'grey', 700, True)
    s.text(b + 20, 568, 'waits for all', 13, 400, 'start', 'muted')
    s.text(b + 20, 586, 'm·n acks', 13, 400, 'start', 'muted')
    s.arrow([(b, 616), (n3, 616), (n1, 616), (n0, 616)], 'grey', mid=True)
    s.pill(930, 606, 'FINAL · 0 B → every node', 13, 'grey', 700, True)
    for x in lanes.values():
        s.box(x - 66, 648, 132, 36, [T('MPI_Finalize', 13, 700, 'ink', True)], 'white', 'grey', rx=6, sw=1.5)
    note(512, 92, [T('0 B = empty message;', 12, 400, 'muted'), T('the tag is the whole', 12, 400, 'muted'),
                   T('instruction', 12, 400, 'muted')], 'white', 'faint')
    return s


# ---------------------------------------------------------------------------------------------
def blocking_vs_nonblocking():
    s = Svg('Why the nodes never block: with blocking receives two congested neighbours deadlock, while '
            'the polling loop answers each other and both rounds finish.')

    def panel(ox, title, sub):
        s.rect(ox, 24, 604, 672, 'white', 'faint', rx=14, sw=1.5)
        s.text(ox + 24, 60, title, 20, 700, 'start')
        s.text(ox + 24, 86, sub, 14, 400, 'start', 'muted', True)

    def lifelines(a, b):
        for x, name, free in [(a, 'Node A', '0/6 free'), (b, 'Node B', '1/6 free')]:
            s.box(x - 90, 110, 180, 54, [T(name, 17, 700), T(free, 13, 400, 'muted')], 'red_bg', 'red')
            s.add(f'<line x1="{x}" y1="164" x2="{x}" y2="580" stroke="{C["grey"]}" stroke-width="1.5" '
                  f'stroke-dasharray="5 5"/>')

    def requests(a, b, gap=0):
        # gap stops the arrowheads at the edge of an activity bar instead of under it
        s.arrow([(a + gap, 196), (b - gap, 246)], 'blue')
        s.arrow([(b - gap, 196), (a + gap, 246)], 'blue')
        s.text(a + 16, 190, 'NBR_REQ', 13, 700, 'start', 'blue', True)
        s.text(b - 16, 190, 'NBR_REQ', 13, 700, 'end', 'blue', True)

    # left: blocking
    a, b = 170, 480
    panel(24, 'Blocking receive', 'MPI_Send, then MPI_Recv(NBR_RESP)')
    lifelines(a, b)
    requests(a, b)
    s.rect(a - 8, 250, 16, 300, 'red_bg', 'red', rx=3, sw=1.5)
    s.rect(b - 8, 250, 16, 300, 'red_bg', 'red', rx=3, sw=1.5)
    s.text(a + 20, 300, 'blocked in MPI_Recv,', 14, 700, 'start', 'red')
    s.text(a + 20, 320, 'waiting for B’s reply', 14, 400, 'start', 'red')
    s.text(b - 20, 400, 'blocked in MPI_Recv,', 14, 700, 'end', 'red')
    s.text(b - 20, 420, 'waiting for A’s reply', 14, 400, 'end', 'red')
    s.text(a + 20, 360, 'B’s request: never read', 13, 400, 'start', 'muted')
    s.text(b - 20, 460, 'A’s request: never read', 13, 400, 'end', 'muted')
    s.text(326, 622, '✗ Deadlock', 22, 700, colour='red')
    s.text(326, 652, 'each waits for a reply the other never sends', 15)

    # right: our design
    a, b = 798, 1108
    panel(652, 'Our loop', 'MPI_Iprobe + MPI_Recv, MPI_Isend')
    lifelines(a, b)
    requests(a, b, 8)
    s.rect(a - 8, 190, 16, 210, 'blue_bg2', 'blue', rx=3, sw=1.5)
    s.rect(b - 8, 190, 16, 210, 'blue_bg2', 'blue', rx=3, sw=1.5)
    s.text(a + 20, 272, 'next pass answers B', 13, 400, 'start')
    s.text(b - 20, 272, 'next pass answers A', 13, 400, 'end')
    s.arrow([(a + 8, 290), (b - 8, 340)], 'blue')
    s.arrow([(b - 8, 290), (a + 8, 340)], 'blue')
    s.text(a + 16, 368, 'NBR_RESP', 13, 700, 'start', 'blue', True)
    s.text(b - 16, 368, 'NBR_RESP', 13, 700, 'end', 'blue', True)
    s.text(a + 20, 420, 'round done ✓', 14, 700, 'start', 'green')
    s.text(b - 20, 420, 'round done ✓', 14, 700, 'end', 'green')
    s.text(954, 622, '✓ No deadlock', 22, 700, colour='green')
    s.text(954, 652, 'nothing waits; replies go out on the next pass', 15)
    return s


DIAGRAMS = [
    ('01-architecture', architecture),
    ('02-node-internals', node_internals),
    ('03-node-flow', node_flow),
    ('04-base-station', base_station),
    ('05-nearest-node-example', search_example),
    ('06-message-sequence', sequence),
    ('07-blocking-vs-nonblocking', blocking_vs_nonblocking),
]

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, 'svg'), exist_ok=True)
    for name, fn in DIAGRAMS:
        with open(os.path.join(here, 'svg', name + '.svg'), 'w') as f:
            f.write(fn().render())
        print('wrote svg/' + name + '.svg')
