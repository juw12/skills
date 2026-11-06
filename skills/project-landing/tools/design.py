"""Per-project design DNA: every landing page gets its own look.

Each project has its own
  - display font (no two pages share one),
  - hero layout, background pattern, card style and heading treatment,
  - hand-drawn emblem (inline SVG, drawn for that project),
  - section headlines written for that project (README-faithful, no invented claims).
"""
import math

# --------------------------------------------------------------------------- fonts
# slug: (Google Fonts css2 family spec, CSS font-family, heading weight)
FONTS = {
    "airiz-motor": ("Barlow+Condensed:wght@600;800", "Barlow Condensed", 800),
    "atomize": ("Unbounded:wght@600;800", "Unbounded", 700),
    "cairn": ("Young+Serif", "Young Serif", 400),
    "cozy-island": ("Fredoka:wght@500;700", "Fredoka", 700),
    "crewcup": ("Gloock", "Gloock", 400),
    "datum-bench": ("Archivo:wght@600;800", "Archivo", 800),
    "datum-cad": ("Chakra+Petch:wght@600;700", "Chakra Petch", 700),
    "e-coder": ("Martian+Mono:wght@500;700", "Martian Mono", 700),
    "earlystar": ("Syne:wght@600;800", "Syne", 800),
    "etsy-prompts": ("DM+Serif+Display", "DM Serif Display", 400),
    "fade": ("Anton", "Anton", 400),
    "game-library": ("Silkscreen:wght@400;700", "Silkscreen", 700),
    "glow": ("Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800", "Bricolage Grotesque", 800),
    "guang-yao-together": ("Noto+Serif+Display:wght@600;800", "Noto Serif Display", 700),
    "handoff": ("Outfit:wght@600;800", "Outfit", 800),
    "haru": ("Zen+Maru+Gothic:wght@500;700", "Zen Maru Gothic", 700),
    "hazel": ("Familjen+Grotesk:wght@600;700", "Familjen Grotesk", 700),
    "hearthwood": ("Cinzel:wght@600;800", "Cinzel", 700),
    "house-of-articles": ("Bebas+Neue", "Bebas Neue", 400),
    "jeda": ("Cormorant+Garamond:ital,wght@0,600;0,700;1,600", "Cormorant Garamond", 700),
    "kinibuka": ("Baloo+2:wght@600;800", "Baloo 2", 800),
    "launchkit": ("Lexend:wght@600;800", "Lexend", 800),
    "lingua": ("Figtree:wght@600;800", "Figtree", 800),
    "maccormack": ("IBM+Plex+Serif:wght@500;700", "IBM Plex Serif", 700),
    "mint": ("Nunito:wght@700;900", "Nunito", 900),
    "morning-paper": ("Playfair+Display:ital,wght@0,700;0,900;1,700", "Playfair Display", 900),
    "nudge": ("Literata:ital,wght@0,600;0,700;1,600", "Literata", 700),
    "orbis": ("Albert+Sans:wght@600;800", "Albert Sans", 800),
    "outlook-archiver": ("Public+Sans:wght@600;800", "Public Sans", 800),
    "peers": ("Instrument+Serif:ital@0;1", "Instrument Serif", 400),
    "pips": ("Chewy", "Chewy", 400),
    "plm-aml-approval": ("Work+Sans:wght@600;800", "Work Sans", 800),
    "pushlab": ("Space+Mono:wght@400;700", "Space Mono", 700),
    "respark": ("Rubik:wght@600;800", "Rubik", 800),
    "rewind": ("Righteous", "Righteous", 400),
    "scopeguard": ("Manrope:wght@600;800", "Manrope", 800),
    "shiphub": ("Red+Hat+Display:wght@600;900", "Red Hat Display", 900),
    "signals": ("Azeret+Mono:wght@500;700", "Azeret Mono", 700),
    "skillmouse": ("Geologica:wght@600;800", "Geologica", 800),
    "sortie": ("Grandstander:wght@600;800", "Grandstander", 800),
    "steward": ("Sora:wght@600;800", "Sora", 800),
    "sweep": ("Schibsted+Grotesk:wght@600;800", "Schibsted Grotesk", 800),
    "sync": ("Poppins:wght@600;800", "Poppins", 800),
    "teman-sehat": ("Quicksand:wght@600;700", "Quicksand", 700),
    "tools": ("Onest:wght@600;800", "Onest", 800),
    "townsquare-3d": ("Lilita+One", "Lilita One", 400),
    "twin": ("Inter+Tight:wght@600;800", "Inter Tight", 800),
    "undanu": ("Marcellus", "Marcellus", 400),
    "upwind": ("Chivo:wght@600;800", "Chivo", 800),
    "vale": ("Philosopher:wght@400;700", "Philosopher", 700),
    "vitals": ("Exo+2:wght@600;800", "Exo 2", 800),
}

# --------------------------------------------------------------------------- layout
# hero layouts: center | split | split-r | poster | editorial
# backgrounds:  dots | grid | lines | diag | plus | waves | topo | rings | stars | checker | paper | fine
# cards:        soft | outline | brutal | flat | ticket | pill
# headings:     center | marker | left | upper | italic | outline
STYLE = {
    "airiz-motor": ("split", "fine", "outline", "upper"),
    "atomize": ("poster", "rings", "brutal", "outline"),
    "cairn": ("editorial", "topo", "soft", "left"),
    "cozy-island": ("center", "waves", "pill", "marker"),
    "crewcup": ("split-r", "dots", "ticket", "italic"),
    "datum-bench": ("split", "grid", "outline", "left"),
    "datum-cad": ("split-r", "fine", "brutal", "upper"),
    "e-coder": ("poster", "lines", "outline", "left"),
    "earlystar": ("editorial", "stars", "brutal", "marker"),
    "etsy-prompts": ("split-r", "paper", "ticket", "italic"),
    "fade": ("poster", "diag", "brutal", "upper"),
    "game-library": ("center", "checker", "brutal", "upper"),
    "glow": ("center", "dots", "soft", "marker"),
    "guang-yao-together": ("editorial", "paper", "soft", "italic"),
    "handoff": ("split", "plus", "flat", "left"),
    "haru": ("center", "dots", "pill", "center"),
    "hazel": ("poster", "lines", "flat", "outline"),
    "hearthwood": ("editorial", "stars", "outline", "center"),
    "house-of-articles": ("poster", "diag", "outline", "upper"),
    "jeda": ("center", "paper", "soft", "italic"),
    "kinibuka": ("split-r", "dots", "pill", "marker"),
    "launchkit": ("split", "rings", "soft", "outline"),
    "lingua": ("split-r", "lines", "flat", "left"),
    "maccormack": ("split", "fine", "outline", "left"),
    "mint": ("center", "plus", "pill", "marker"),
    "morning-paper": ("editorial", "lines", "outline", "italic"),
    "nudge": ("split-r", "waves", "soft", "italic"),
    "orbis": ("split", "rings", "soft", "center"),
    "outlook-archiver": ("split-r", "grid", "outline", "left"),
    "peers": ("editorial", "paper", "ticket", "italic"),
    "pips": ("center", "dots", "pill", "marker"),
    "plm-aml-approval": ("split", "grid", "ticket", "upper"),
    "pushlab": ("split-r", "plus", "brutal", "left"),
    "respark": ("split", "diag", "flat", "marker"),
    "rewind": ("center", "checker", "ticket", "outline"),
    "scopeguard": ("split-r", "rings", "outline", "upper"),
    "shiphub": ("editorial", "plus", "flat", "marker"),
    "signals": ("poster", "grid", "outline", "upper"),
    "skillmouse": ("split-r", "dots", "brutal", "marker"),
    "sortie": ("center", "plus", "pill", "outline"),
    "steward": ("split", "grid", "soft", "center"),
    "sweep": ("split-r", "lines", "flat", "upper"),
    "sync": ("poster", "waves", "soft", "outline"),
    "teman-sehat": ("center", "waves", "pill", "center"),
    "tools": ("editorial", "grid", "ticket", "left"),
    "townsquare-3d": ("center", "checker", "brutal", "marker"),
    "twin": ("split", "topo", "soft", "upper"),
    "undanu": ("center", "paper", "ticket", "italic"),
    "upwind": ("split-r", "fine", "outline", "upper"),
    "vale": ("poster", "stars", "outline", "center"),
    "vitals": ("split-r", "plus", "soft", "left"),
}

# --------------------------------------------------------------------------- headlines
# slug: {section: title}. Sections: why, ideas, features, steps, checklist, quick, faq, related, band
COPY = {
    "airiz-motor": {"why": "Motor testing without the clipboard.", "ideas": "Jog it, check it, grade it.",
                    "features": "Everything on the test bench.", "checklist": "On the bench today.",
                    "band": "Put a motor on the bench."},
    "atomize": {"why": "One post deserves more than one day.", "ideas": "In, out, and ready to sell.",
                "features": "From one post to a week.", "band": "Read how Atomize is planned."},
    "cairn": {"why": "Your project's thinking, kept with the code.", "ideas": "A small stack of good habits.",
              "features": "Every screen, one calm loop.", "steps": "Three ways in.", "checklist": "Already in v1.0.",
              "band": "Give your repo a second brain."},
    "cozy-island": {"why": "A little island for long laptop days.", "ideas": "Fish, garden, breathe.",
                    "features": "Life on the island.", "band": "Visit the island."},
    "crewcup": {"why": "The office coffee run, sorted.", "ideas": "Your usual, in one tap.",
                "features": "What's on the menu.", "band": "Start a coffee run."},
    "datum-bench": {"why": "NPI work, in one place instead of ten.", "ideas": "Flow, checks, numbers.",
                    "features": "Tools on the bench.", "checklist": "Measured and working.",
                    "band": "Open the bench."},
    "datum-cad": {"why": "From a written spec to a real solid.", "ideas": "Spec in, STEP out.",
                  "features": "How a part gets built.", "band": "Build a part."},
    "e-coder": {"why": "A coding agent you can actually leave running.", "ideas": "Small, local, careful.",
                "features": "What the agent can do.", "quick": "Run it on your repo.", "band": "Point it at a repo."},
    "earlystar": {"why": "Stars that were earned this week.", "ideas": "Momentum, not hype.",
                  "features": "How the ranking works.", "band": "See what's rising."},
    "etsy-prompts": {"why": "Etsy copy without the blank page.", "ideas": "150 prompts, one workflow.",
                     "features": "What's in the pack.", "band": "Read the prompt pack."},
    "fade": {"why": "Book the cut you just watched.", "ideas": "Watch, book, pay.",
             "features": "Inside the shop.", "band": "Find your barber."},
    "game-library": {"why": "Bored? There's a game for that.", "ideas": "Search, filter, surprise.",
                     "features": "Press start.", "band": "Pick a game."},
    "glow": {"why": "Free AI that works for everyone.", "ideas": "Four apps, one glow.",
             "features": "Every app in the family.", "band": "Try Glow."},
    "guang-yao-together": {"why": "Lessons, review and a study friend.", "ideas": "Learn a little every day.",
                           "features": "Inside the classroom.", "band": "Start learning together."},
    "handoff": {"why": "An agency kit and a product in one hand-off.", "ideas": "Build, pitch, validate.",
                "features": "What's in the box.", "band": "Read the playbook."},
    "haru": {"why": "A soft place for your everyday photos.", "ideas": "One little diorama a day.",
             "features": "Things to do in Haru.", "band": "Open your diary."},
    "hazel": {"why": "One studio for every video length.", "ideas": "Short, fast, long.",
              "features": "On the edit desk.", "band": "Open the studio."},
    "hearthwood": {"why": "A village worth coming home to.", "ideas": "Quests by the fire.",
                   "features": "Life in Hearthwood.", "band": "Enter the village."},
    "house-of-articles": {"why": "When the athlete moves, the market moves.", "ideas": "Moment, market, reason.",
                          "features": "Off the shelf.", "band": "Check the market."},
    "jeda": {"why": "Room to pause, for every faith.", "ideas": "A quiet place to return to.",
             "features": "Inside the library.", "band": "Take a pause."},
    "kinibuka": {"why": "Is it open right now? Now you know.", "ideas": "Open, followed, ordered.",
                 "features": "Around the neighbourhood.", "band": "See who's open."},
    "launchkit": {"why": "Launch with a crowd already waiting.", "ideas": "Waitlist, signal, launch.",
                  "features": "The launch kit.", "band": "Plan your launch."},
    "lingua": {"why": "Understand every Teams meeting.", "ideas": "Read, translate, float.",
               "features": "How the window works.", "band": "Float the captions."},
    "maccormack": {"why": "A second-order look at a 1-D wave.", "ideas": "Predict, correct, compare.",
                   "features": "The numerical method.", "band": "Read the study."},
    "mint": {"why": "Money together, without the spreadsheet.", "ideas": "Budget, text, trade.",
             "features": "What Mint keeps fresh.", "band": "Try Mint."},
    "morning-paper": {"why": "The morning's tech news, already read for you.", "ideas": "Today's edition.",
                      "features": "Sections in this paper.", "band": "Read today's paper."},
    "nudge": {"why": "Friends reach out. Nudge makes sure you notice.", "ideas": "A kinder inbox.",
              "features": "How Nudge helps you reply.", "band": "Reconnect with someone."},
    "orbis": {"why": "Your team, in one orbit.", "ideas": "Chat, push, everywhere.",
              "features": "Around the orbit.", "band": "Try Orbis."},
    "outlook-archiver": {"why": "An inbox that archives itself.", "ideas": "Quietly, every message.",
                         "features": "What the daemon does.", "band": "Read the README."},
    "peers": {"why": "Reviews you can actually decide with.", "ideas": "Use it, wait, or skip.",
              "features": "Every review, one verdict.", "band": "Read the verdicts."},
    "pips": {"why": "A little company while you focus.", "ideas": "51 friends on your screen.",
             "features": "Meet the pips.", "band": "Let them roam."},
    "plm-aml-approval": {"why": "The AML paperwork, walked for you.", "ideas": "Start, fill, stop.",
                         "features": "Each step of the workflow.", "band": "Read the README."},
    "pushlab": {"why": "Every push, proven on a real device.", "ideas": "Send, watch, prove.",
                "features": "On the lab bench.", "band": "Open the lab."},
    "respark": {"why": "Dormant customers are the easiest win.", "ideas": "Win back, bridge, run.",
                "features": "What Respark rekindles.", "band": "Read the README."},
    "rewind": {"why": "The shows streaming forgot.", "ideas": "Remember, find, keep.",
               "features": "Back on the shelf.", "band": "Press rewind."},
    "scopeguard": {"why": "A business AI that stays on topic.", "ideas": "Four verdicts, one guard.",
                   "features": "What the guard decides.", "band": "Open the playground."},
    "shiphub": {"why": "Ideas are cheap. Shipping is the point.", "ideas": "Save, claim, ship.",
                "features": "On the dock.", "band": "Claim an idea."},
    "signals": {"why": "Two indicators agreeing, not one guessing.", "ideas": "Confluence, paper, caps.",
                "features": "On the chart.", "band": "Read the README."},
    "skillmouse": {"why": "Your agent skills, one click away.", "ideas": "Select, click, done.",
                   "features": "Under the cursor.", "band": "Try SkillMouse."},
    "sortie": {"why": "Tidying files should feel like play.", "ideas": "Sort, sweep, ask.",
               "features": "Watch it sort.", "band": "Sort a folder."},
    "steward": {"why": "Keep the assistant on the job.", "ideas": "Detect, deflect, block.",
                "features": "The governance layer.", "band": "Read the README."},
    "sweep": {"why": "One command to tidy up a day's work.", "ideas": "Sync, mirror, update.",
              "features": "What the sweep covers.", "band": "Run a sweep."},
    "sync": {"why": "Same song, same second, anywhere.", "ideas": "Any source, in sync.",
             "features": "In the listening room.", "band": "Start a session."},
    "teman-sehat": {"why": "A gentle friend for daily habits.", "ideas": "Small habits, kept.",
                    "features": "What your friend reminds you.", "band": "Meet Teman Sehat."},
    "tools": {"why": "Small problems deserve good tools.", "ideas": "Local, broad, tested.",
              "features": "In the toolbox.", "quick": "Open the toolbox.", "band": "Open the toolbox."},
    "townsquare-3d": {"why": "A town built by the people who play it.", "ideas": "Land, crops, market.",
                      "features": "Around the square.", "band": "Visit the square."},
    "twin": {"why": "Practise the trade before you make it.", "ideas": "Replay, research, copy.",
             "features": "What your twin can do.", "band": "Meet your twin."},
    "undanu": {"why": "An invitation every guest gets personally.", "ideas": "Design, send, welcome.",
               "features": "From envelope to entrance.", "band": "Design an invitation."},
    "upwind": {"why": "A first-order scheme, studied properly.", "ideas": "Upwind, plot, compare.",
               "features": "The numerical method.", "band": "Read the study."},
    "vale": {"why": "A fading realm waiting for its light.", "ideas": "Explore, gather, restore.",
             "features": "Across the vale.", "band": "Enter the vale."},
    "vitals": {"why": "Know what your device is really doing.", "ideas": "Clean, forecast, find.",
               "features": "The check-up.", "band": "Run a check-up."},
}


# --------------------------------------------------------------------------- emblems
def _pts(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _star(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return _pts(pts)


def _gear(cx, cy, r_out, r_in, teeth=10):
    pts = []
    step = 360 / teeth
    for i in range(teeth):
        a0 = i * step
        for da, r in ((0, r_in), (step * 0.18, r_out), (step * 0.5, r_out), (step * 0.68, r_in)):
            a = math.radians(a0 + da)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return _pts(pts)


def _rays(cx, cy, r1, r2, n):
    out = []
    for i in range(n):
        a = math.radians(i * 360 / n)
        out.append(f'<line class="ao" x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" '
                   f'x2="{cx + r2 * math.cos(a):.1f}" y2="{cy + r2 * math.sin(a):.1f}"/>')
    return "".join(out)


def _petals(cx, cy, n, rx, ry, dist, cls="s o"):
    out = []
    for i in range(n):
        ang = -90 + (i - (n - 1) / 2) * (150 / max(n - 1, 1))
        out.append(f'<ellipse class="{cls}" cx="{cx}" cy="{cy - dist}" rx="{rx}" ry="{ry}" '
                   f'transform="rotate({ang + 90:.1f} {cx} {cy})"/>')
    return "".join(out)


def _paw(x, y, s=1.0, rot=0):
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({s})">'
            '<ellipse class="a" cx="0" cy="8" rx="11" ry="9"/>'
            '<circle class="a" cx="-11" cy="-6" r="4.5"/><circle class="a" cx="-4" cy="-12" r="4.5"/>'
            '<circle class="a" cx="5" cy="-12" r="4.5"/><circle class="a" cx="12" cy="-6" r="4.5"/></g>')


ART = {
    "cairn": '<line class="o" x1="22" y1="178" x2="178" y2="178"/>'
             '<ellipse class="s o" cx="100" cy="158" rx="62" ry="20"/><ellipse class="a o" cx="96" cy="122" rx="46" ry="17"/>'
             '<ellipse class="s o" cx="103" cy="90" rx="33" ry="14"/><ellipse class="a o" cx="99" cy="64" rx="21" ry="11"/>'
             '<path class="ao" d="M142 40 q10 -14 22 -6"/>',
    "steward": '<path class="s o" d="M100 22 L160 46 V98 C160 140 132 166 100 180 C68 166 40 140 40 98 V46 Z"/>'
               '<path class="ao" d="M72 102 L93 123 L132 80" style="stroke-width:10"/>',
    "scopeguard": '<path class="s o" d="M100 22 L160 46 V98 C160 140 132 166 100 180 C68 166 40 140 40 98 V46 Z"/>'
                  '<circle class="o" cx="100" cy="100" r="34"/><circle class="a" cx="100" cy="100" r="9"/>'
                  '<line class="o" x1="100" y1="54" x2="100" y2="74"/><line class="o" x1="100" y1="126" x2="100" y2="146"/>'
                  '<line class="o" x1="54" y1="100" x2="74" y2="100"/><line class="o" x1="126" y1="100" x2="146" y2="100"/>',
    "maccormack": '<line class="o" x1="18" y1="170" x2="186" y2="170"/><line class="o" x1="22" y1="30" x2="22" y2="174"/>'
                  '<path class="ao" d="M28 120 C52 120 58 40 80 40 S106 150 128 150 S158 96 182 96"/>'
                  '<path class="o" d="M28 132 C56 132 66 64 88 64 S114 140 136 140 S166 110 182 110" style="stroke-dasharray:6 10;stroke-width:4"/>'
                  '<circle class="a" cx="80" cy="40" r="7"/><circle class="a" cx="128" cy="150" r="7"/>',
    "upwind": '<line class="o" x1="18" y1="170" x2="186" y2="170"/>'
              '<path class="ao" d="M24 64 H140 q24 0 24 -20 q0 -16 -16 -16 q-14 0 -14 14"/>'
              '<path class="o" d="M24 104 H160 q22 0 22 18 q0 14 -14 14 q-12 0 -12 -12"/>'
              '<path class="ao" d="M24 142 H112"/><path class="o" d="M120 132 l14 10 l-14 10" />',
    "airiz-motor": f'<polygon class="s o" points="{_gear(100, 100, 74, 60, 12)}"/>'
                   '<circle class="p o" cx="100" cy="100" r="34"/><circle class="a" cx="100" cy="100" r="12"/>'
                   '<path class="ao" d="M100 66 A34 34 0 0 1 134 100"/>',
    "atomize": '<ellipse class="ao" cx="100" cy="100" rx="80" ry="30"/>'
               '<ellipse class="o" cx="100" cy="100" rx="80" ry="30" transform="rotate(60 100 100)"/>'
               '<ellipse class="o" cx="100" cy="100" rx="80" ry="30" transform="rotate(-60 100 100)"/>'
               '<circle class="a o" cx="100" cy="100" r="16"/><circle class="a" cx="178" cy="96" r="7"/>',
    "cozy-island": '<circle class="a" cx="152" cy="46" r="20"/>'
                   '<path class="s o" d="M22 150 Q100 96 178 150 Z"/>'
                   '<path class="o" d="M98 132 C96 106 100 82 112 62"/>'
                   '<path class="ao" d="M112 62 q-26 -8 -42 6 M112 62 q24 -12 40 0 M112 62 q-6 -22 -24 -28 M112 62 q14 -18 32 -16"/>'
                   '<path class="o" d="M14 172 q14 -10 28 0 t28 0 t28 0 t28 0 t28 0 t28 0"/>',
    "crewcup": '<path class="o" d="M78 44 q-10 -12 0 -24 M100 44 q-10 -12 0 -24 M122 44 q-10 -12 0 -24"/>'
               '<path class="s o" d="M48 62 H152 L142 148 Q140 162 126 162 H74 Q60 162 58 148 Z"/>'
               '<path class="o" d="M150 80 q30 0 30 24 q0 24 -34 26"/>'
               '<ellipse class="a" cx="100" cy="176" rx="74" ry="9"/><rect class="a" x="56" y="92" width="88" height="22" rx="6"/>',
    "datum-bench": '<rect class="s o" x="22" y="78" width="160" height="34" rx="6"/>'
                   + "".join(f'<line class="o" x1="{x}" y1="78" x2="{x}" y2="{92 if i % 2 else 100}" style="stroke-width:3"/>'
                             for i, x in enumerate(range(36, 180, 12)))
                   + '<path class="a o" d="M40 112 V170 H62 V112"/><path class="a o" d="M120 112 V150 H142 V112"/>'
                     '<path class="o" d="M40 78 V44 H62 V78"/>',
    "datum-cad": '<polygon class="s o" points="100,34 162,68 100,102 38,68"/>'
                 '<polygon class="a o" points="38,68 100,102 100,170 38,136"/>'
                 '<polygon class="p o" points="162,68 100,102 100,170 162,136"/>'
                 '<path class="ao" d="M170 76 V144 M164 82 l6 -6 l6 6 M164 138 l6 6 l6 -6" style="stroke-width:4"/>',
    "e-coder": '<rect class="s o" x="20" y="34" width="160" height="132" rx="14"/><line class="o" x1="20" y1="62" x2="180" y2="62"/>'
               '<circle class="a" cx="38" cy="48" r="5"/><circle class="o" cx="54" cy="48" r="4" style="stroke-width:3"/>'
               '<path class="ao" d="M48 92 l22 18 l-22 18"/><line class="o" x1="82" y1="132" x2="122" y2="132"/>'
               '<rect class="a" x="128" y="122" width="12" height="20" rx="2"/>',
    "earlystar": f'<polygon class="s o" points="{_star(92, 104, 70, 30)}"/>'
                 '<path class="ao" d="M120 168 L150 136 L164 148 L188 118"/><path class="ao" d="M172 116 H190 V134"/>',
    "etsy-prompts": '<path class="s o" d="M34 70 L92 24 H170 V102 L112 160 Q100 172 88 160 L34 106 Q22 94 34 70 Z" transform="rotate(8 100 100)"/>'
                    '<circle class="p o" cx="146" cy="50" r="10"/>'
                    '<line class="ao" x1="68" y1="94" x2="120" y2="66"/><line class="o" x1="78" y1="114" x2="126" y2="88"/>'
                    '<line class="o" x1="90" y1="132" x2="122" y2="114"/>',
    "fade": '<rect class="p o" x="70" y="26" width="60" height="150" rx="30"/>'
            + "".join(f'<path class="a" d="M72 {y} L128 {y - 26} V{y - 8} L72 {y + 18} Z"/>' for y in range(64, 170, 36))
            + '<rect class="o" x="70" y="26" width="60" height="150" rx="30"/>'
              '<rect class="s o" x="60" y="14" width="80" height="16" rx="8"/><rect class="s o" x="60" y="172" width="80" height="16" rx="8"/>',
    "game-library": '<path class="s o" d="M50 70 H150 Q182 70 186 110 L190 140 Q192 162 172 162 Q160 162 150 146 L140 132 H60 L50 146 Q40 162 28 162 Q8 162 10 140 L14 110 Q18 70 50 70 Z"/>'
                    '<path class="o" d="M58 92 V124 M42 108 H74"/><circle class="a" cx="138" cy="98" r="9"/>'
                    '<circle class="a" cx="158" cy="118" r="9"/><circle class="o" cx="118" cy="118" r="7" style="stroke-width:4"/>',
    "glow": f'{_rays(100, 100, 52, 84, 12)}<circle class="a o" cx="100" cy="100" r="40"/>'
            '<path class="o" d="M84 98 q4 -6 8 0 M108 98 q4 -6 8 0 M86 114 q14 12 28 0"/>',
    "guang-yao-together": '<path class="s o" d="M100 58 Q70 40 24 46 V160 Q70 154 100 172 Q130 154 176 160 V46 Q130 40 100 58 Z"/>'
                          '<line class="o" x1="100" y1="58" x2="100" y2="172"/>'
                          '<path class="o" d="M42 78 Q66 74 86 84 M42 102 Q66 98 86 108 M114 84 Q134 74 158 78 M114 108 Q134 98 158 102" style="stroke-width:4"/>'
                          f'<polygon class="a" points="{_star(160, 30, 16, 6, 4, -90)}"/>',
    "handoff": '<rect class="s o" x="60" y="70" width="80" height="70" rx="8"/><path class="o" d="M60 92 H140 M100 70 V92"/>'
               '<path class="ao" d="M20 168 Q40 124 60 120"/><path class="ao" d="M180 50 Q160 90 140 92"/>'
               '<path class="o" d="M170 40 l12 8 l-8 12"/><path class="o" d="M30 178 l-12 -8 l8 -12"/>',
    "haru": '<g transform="rotate(-6 100 100)"><rect class="p o" x="38" y="30" width="124" height="144" rx="6"/>'
            '<rect class="s o" x="52" y="44" width="96" height="88" rx="2"/>'
            '<path class="a o" d="M70 132 V104 L94 86 L118 104 V132 Z"/><circle class="a" cx="130" cy="66" r="9"/>'
            '<line class="o" x1="60" y1="152" x2="112" y2="152" style="stroke-width:4"/></g>'
            f'{_petals(164, 156, 5, 8, 14, 16, "a")}',
    "hazel": '<rect class="s o" x="22" y="48" width="156" height="104" rx="10"/>'
             + "".join(f'<rect class="p o" x="{x}" y="56" width="12" height="10" rx="2" style="stroke-width:3"/>'
                       f'<rect class="p o" x="{x}" y="134" width="12" height="10" rx="2" style="stroke-width:3"/>'
                       for x in range(34, 170, 24))
             + '<path class="a o" d="M86 78 L126 100 L86 122 Z"/>',
    "hearthwood": '<path class="o" d="M150 40 q-12 -12 0 -24 M162 46 q-10 -10 0 -20" style="stroke-width:4"/>'
                  '<rect class="o" x="142" y="52" width="16" height="30"/>'
                  '<path class="s o" d="M40 100 L100 50 L160 100 V168 H40 Z"/><rect class="a o" x="86" y="124" width="28" height="44" rx="14"/>'
                  '<rect class="p o" x="56" y="112" width="20" height="20"/><path class="ao" d="M28 100 L100 40 L172 100"/>',
    "house-of-articles": '<path class="s o" d="M22 140 Q28 98 62 92 L96 84 Q110 60 132 66 L150 76 Q178 92 182 128 V146 H22 Z"/>'
                         '<path class="a o" d="M22 146 H182 V160 Q182 168 172 168 H32 Q22 168 22 158 Z"/>'
                         '<path class="o" d="M96 84 l10 18 M112 76 l10 18 M128 72 l8 18" style="stroke-width:4"/>',
    "jeda": f'{_petals(100, 140, 5, 16, 34, 44)}<ellipse class="a o" cx="100" cy="138" rx="22" ry="12"/>'
            '<path class="o" d="M30 160 Q100 178 170 160"/>'
            '<path class="a" d="M100 30 q12 16 0 30 q-12 -14 0 -30 Z"/>',
    "kinibuka": '<path class="s o" d="M28 70 H172 L160 40 H40 Z"/>'
                + "".join(f'<path class="a o" d="M{x} 70 q12 18 24 0" style="stroke-width:4"/>' for x in range(28, 172, 24))
                + '<rect class="p o" x="40" y="88" width="120" height="80" rx="4"/>'
                  '<rect class="a o" x="70" y="104" width="60" height="24" rx="12"/><line class="o" x1="40" y1="148" x2="160" y2="148"/>',
    "launchkit": '<path class="s o" d="M100 20 C130 44 138 84 130 126 H70 C62 84 70 44 100 20 Z"/>'
                 '<circle class="p o" cx="100" cy="74" r="14"/><path class="a o" d="M70 102 L46 132 L72 128 Z M130 102 L154 132 L128 128 Z"/>'
                 '<path class="ao" d="M86 140 q14 40 14 44 q0 -4 14 -44"/>',
    "lingua": '<path class="s o" d="M22 40 H112 Q124 40 124 52 V100 Q124 112 112 112 H60 L38 130 V112 H34 Q22 112 22 100 V52 Q22 40 34 40 Z"/>'
              '<path class="a o" d="M76 88 H166 Q178 88 178 100 V146 Q178 158 166 158 H162 V176 L140 158 H88 Q76 158 76 146 V100 Q76 88 88 88 Z"/>'
              '<path class="o" d="M48 92 L62 58 L76 92 M53 80 H71" style="stroke-width:4"/>'
              '<path class="o" d="M110 110 H146 M128 104 V146 M112 128 H144" style="stroke-width:4;stroke:var(--paper)"/>',
    "mint": '<path class="s o" d="M40 160 C40 90 90 40 168 34 C164 112 118 160 40 160 Z"/>'
            '<path class="o" d="M40 160 C78 122 112 90 150 54"/>'
            '<circle class="a o" cx="58" cy="58" r="30"/><path class="o" d="M58 42 V74 M50 50 H64 Q70 50 70 56 Q70 62 58 62 Q46 62 46 68 Q46 74 54 74 H66" style="stroke-width:4;stroke:var(--paper)"/>',
    "morning-paper": f'{_rays(150, 150, 34, 50, 7)}<circle class="a" cx="150" cy="150" r="26"/>'
                     '<path class="s o" d="M24 36 H140 V150 Q140 168 122 168 H40 Q24 168 24 152 Z"/>'
                     '<rect class="a" x="38" y="50" width="88" height="16" rx="3"/>'
                     '<path class="o" d="M38 82 H126 M38 100 H80 M38 118 H80 M38 136 H80 M92 100 H126 M92 118 H126" style="stroke-width:4"/>',
    "nudge": '<path class="s o" d="M28 40 H172 Q184 40 184 52 V122 Q184 134 172 134 H86 L52 164 V134 H28 Q16 134 16 122 V52 Q16 40 28 40 Z"/>'
             '<path class="a o" d="M100 116 C70 96 62 80 74 68 C84 58 96 62 100 72 C104 62 116 58 126 68 C138 80 130 96 100 116 Z"/>',
    "orbis": '<ellipse class="o" cx="100" cy="100" rx="88" ry="34" transform="rotate(-18 100 100)"/>'
             '<circle class="s o" cx="100" cy="100" r="46"/><path class="o" d="M58 86 Q100 104 142 86 M62 118 Q100 132 138 118" style="stroke-width:4"/>'
             '<path class="ao" d="M14 128 A88 34 -18 0 0 186 72" transform="rotate(0)"/><circle class="a o" cx="178" cy="66" r="11"/>',
    "outlook-archiver": '<path class="s o" d="M30 96 H170 V164 Q170 174 160 174 H40 Q30 174 30 164 Z"/>'
                        '<rect class="a o" x="22" y="78" width="156" height="22" rx="4"/><rect class="p o" x="82" y="116" width="36" height="12" rx="6"/>'
                        '<rect class="p o" x="64" y="18" width="72" height="48" rx="4"/><path class="o" d="M64 22 L100 46 L136 22"/>'
                        '<path class="ao" d="M100 66 V80"/>',
    "peers": '<circle class="a o" cx="46" cy="100" r="28"/><path class="o" d="M34 100 l9 9 l16 -18" style="stroke:var(--paper)"/>'
             '<circle class="s o" cx="100" cy="100" r="28"/><path class="o" d="M92 88 V112 M108 88 V112"/>'
             '<circle class="p o" cx="154" cy="100" r="28"/><path class="o" d="M144 90 L164 110 M164 90 L144 110"/>',
    "pips": _paw(46, 160, 1.1, -20) + _paw(84, 118, 1.0, -10) + _paw(126, 92, 0.95, 10) + _paw(164, 52, 0.9, 20),
    "plm-aml-approval": '<rect class="s o" x="40" y="34" width="120" height="146" rx="10"/><rect class="p o" x="74" y="22" width="52" height="24" rx="6"/>'
                        '<path class="ao" d="M58 76 l8 8 l14 -16 M58 112 l8 8 l14 -16"/><path class="o" d="M92 78 H142 M92 114 H142 M92 148 H142" style="stroke-width:4"/>'
                        '<rect class="o" x="58" y="140" width="18" height="18" rx="3" style="stroke-width:4"/>',
    "pushlab": '<path class="s o" d="M100 28 C70 28 58 54 58 82 V116 L44 140 H156 L142 116 V82 C142 54 130 28 100 28 Z"/>'
               '<path class="a o" d="M84 140 Q86 160 100 160 Q114 160 116 140"/>'
               '<path class="ao" d="M160 40 q16 16 0 36 M174 28 q26 28 0 60 M40 40 q-16 16 0 36 M26 28 q-26 28 0 60"/>',
    "respark": '<circle class="s o" cx="100" cy="100" r="70"/>'
               '<path class="a o" d="M108 38 L66 110 H96 L88 162 L134 86 H104 Z"/>'
               '<path class="ao" d="M164 70 A70 70 0 0 1 150 148"/><path class="o" d="M156 136 l-6 14 l14 -2" style="stroke-width:4"/>',
    "rewind": '<rect class="s o" x="24" y="54" width="152" height="112" rx="18"/><rect class="p o" x="40" y="68" width="98" height="84" rx="12"/>'
              '<path class="a" d="M110 92 L86 110 L110 128 Z M86 92 L62 110 L86 128 Z"/>'
              '<circle class="a o" cx="158" cy="86" r="7"/><circle class="o" cx="158" cy="112" r="6" style="stroke-width:4"/>'
              '<path class="o" d="M76 54 L56 26 M124 54 L144 26"/>',
    "shiphub": '<path class="s o" d="M30 132 H170 L152 164 H50 Z"/><line class="o" x1="100" y1="132" x2="100" y2="30"/>'
               '<path class="a o" d="M104 36 L156 112 H104 Z"/><path class="p o" d="M96 52 L56 112 H96 Z"/>'
               '<path class="o" d="M14 178 q14 -10 28 0 t28 0 t28 0 t28 0 t28 0 t28 0"/>',
    "signals": '<line class="o" x1="20" y1="176" x2="184" y2="176"/>'
               + "".join(f'<line class="o" x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" style="stroke-width:4"/>'
                         f'<rect class="{c} o" x="{x - 10}" y="{b1}" width="20" height="{b2 - b1}" rx="3" style="stroke-width:4"/>'
                         for x, y1, y2, b1, b2, c in ((42, 110, 168, 122, 156, "p"), (78, 88, 150, 98, 136, "a"),
                                                      (114, 96, 156, 108, 144, "p"), (150, 40, 120, 52, 104, "a")))
               + '<path class="ao" d="M30 136 L78 112 L114 120 L170 52"/>',
    "skillmouse": '<rect class="s o" x="62" y="44" width="76" height="124" rx="38"/><line class="o" x1="100" y1="44" x2="100" y2="92"/>'
                  '<path class="o" d="M62 92 H138"/><rect class="a" x="94" y="60" width="12" height="20" rx="6"/>'
                  f'<polygon class="a" points="{_star(158, 42, 20, 7, 4)}"/>',
    "sortie": '<path class="s o" d="M24 92 H84 L96 104 H176 V168 H24 Z"/>'
              '<rect class="p o" x="66" y="30" width="38" height="46" rx="4" transform="rotate(-18 85 53)"/>'
              '<rect class="a o" x="112" y="22" width="38" height="46" rx="4" transform="rotate(14 131 45)"/>'
              '<path class="ao" d="M40 70 q10 -30 34 -40 M170 70 q-6 -30 -26 -44" style="stroke-dasharray:4 9"/>',
    "sweep": '<line class="o" x1="150" y1="22" x2="96" y2="112"/>'
             '<path class="s o" d="M84 104 L120 124 L104 170 Q78 176 52 160 Z"/>'
             '<path class="o" d="M70 132 L60 162 M84 140 L78 168 M98 146 L96 170" style="stroke-width:4"/>'
             f'<polygon class="a" points="{_star(160, 150, 14, 5, 4)}"/><polygon class="a" points="{_star(36, 116, 10, 4, 4)}"/>',
    "sync": '<path class="o" d="M40 116 V100 Q40 40 100 40 Q160 40 160 100 V116"/>'
            '<rect class="a o" x="28" y="108" width="34" height="58" rx="12"/><rect class="a o" x="138" y="108" width="34" height="58" rx="12"/>'
            '<path class="s o" d="M84 82 V128 M84 82 L120 74 V120" /><circle class="a o" cx="78" cy="130" r="9"/><circle class="a o" cx="114" cy="122" r="9"/>',
    "teman-sehat": '<path class="s o" d="M100 172 C40 132 20 100 30 70 C40 40 80 36 100 64 C120 36 160 40 170 70 C180 100 160 132 100 172 Z"/>'
                   '<path class="ao" d="M36 108 H70 L82 84 L98 132 L112 98 L120 108 H164"/>'
                   '<path class="a o" d="M146 22 C176 22 182 44 178 60 C156 62 140 50 146 22 Z" style="stroke-width:4"/>',
    "tools": '<path class="s o" d="M46 154 L120 80 Q110 50 136 34 Q150 28 164 32 L142 54 L148 70 L164 76 L186 54 Q190 70 182 84 Q166 108 134 98 L60 168 Q50 176 42 168 Q34 160 46 154 Z"/>'
             '<path class="a o" d="M58 46 L126 114 L136 140 L110 130 L42 62 Q34 54 42 46 Q50 38 58 46 Z"/>',
    "townsquare-3d": '<path class="s o" d="M20 112 L50 84 L80 112 V164 H20 Z"/><path class="a o" d="M76 98 L112 62 L148 98 V164 H76 Z"/>'
                     '<path class="s o" d="M144 116 L164 96 L184 116 V164 H144 Z"/><rect class="p o" x="100" y="124" width="24" height="40" rx="4"/>'
                     '<rect class="p o" x="38" y="128" width="20" height="18"/><line class="o" x1="12" y1="166" x2="190" y2="166"/>',
    "twin": '<circle class="s o" cx="78" cy="100" r="54"/><circle class="o" cx="122" cy="100" r="54" style="fill:var(--accent);fill-opacity:.35"/>'
            '<path class="ao" d="M40 128 L70 108 L92 118 L124 82 L160 74"/><circle class="a" cx="160" cy="74" r="7"/>',
    "undanu": '<rect class="s o" x="20" y="54" width="160" height="110" rx="8"/><path class="o" d="M20 60 L100 118 L180 60"/>'
              f'<circle class="a o" cx="100" cy="116" r="22"/><polygon class="p" points="{_star(100, 116, 11, 5)}"/>'
              '<path class="o" d="M30 156 L82 112 M170 156 L118 112" style="stroke-width:4"/>',
    "vale": '<polygon class="s o" points="100,18 132,64 118,176 82,176 68,64"/><polygon class="a o" points="100,18 118,64 100,176 82,64"/>'
            '<polygon class="p o" points="48,96 64,118 58,168 40,168 34,118"/><polygon class="p o" points="152,86 168,110 162,168 144,168 138,110"/>'
            f'<polygon class="a" points="{_star(164, 40, 12, 4, 4)}"/><polygon class="a" points="{_star(36, 60, 9, 3, 4)}"/>',
    "vitals": '<rect class="s o" x="26" y="58" width="140" height="84" rx="14"/><rect class="a o" x="166" y="84" width="14" height="32" rx="4"/>'
              '<path class="ao" d="M42 100 H72 L84 76 L100 124 L114 92 L122 100 H150"/>',
}

ART_CSS = r"""
.art { display: block; width: var(--art-size, 120px); height: var(--art-size, 120px); margin: 0 auto 18px; }
.art svg { width: 100%; height: 100%; overflow: visible; }
.art .o { fill: none; stroke: var(--ink); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
.art .ao { fill: none; stroke: var(--accent); stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
.art .a { fill: var(--accent); }
.art .s { fill: var(--accent-soft); }
.art .p { fill: var(--card); }
@media (prefers-reduced-motion: no-preference) {
  .art svg { animation: art-in .9s cubic-bezier(.2,.8,.2,1) both; }
  @keyframes art-in { from { opacity: 0; transform: translateY(10px) rotate(-4deg) scale(.94); } to { opacity: 1; transform: none; } }
}
"""


def art_svg(slug, label):
    body = ART.get(slug)
    if not body:
        return ""
    return (f'<span class="art" aria-hidden="true"><svg viewBox="0 0 200 200" role="presentation" focusable="false">'
            f'{body}</svg></span>')


def fonts_link(slug):
    spec = FONTS.get(slug)
    if not spec:
        return ""
    return f'<link href="https://fonts.googleapis.com/css2?family={spec[0]}&display=swap" rel="stylesheet">'


def root_vars(slug):
    spec = FONTS.get(slug)
    if not spec:
        return ""
    return f'--fd: "{spec[1]}", var(--fd-fallback); --fdw: {spec[2]};'


def html_classes(slug):
    hero, bg, card, hd = STYLE.get(slug, ("center", "dots", "soft", "center"))
    return f"h-{hero} bg-{bg} c-{card} hd-{hd}"


def hero_layout(slug):
    return STYLE.get(slug, ("center",))[0]


DNA_CSS = r"""
/* ---- per-project design DNA (fonts, backgrounds, cards, headings, hero layouts) ---- */
h1, h2, h3, .brand, .stat b, .lead { font-weight: var(--fdw, 800); }

/* backgrounds */
html.bg-dots body { background-image: radial-gradient(color-mix(in srgb, var(--ink) 13%, transparent) 1.2px, transparent 1.3px); background-size: 20px 20px; }
html.bg-grid body { background-image: linear-gradient(color-mix(in srgb, var(--ink) 7%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--ink) 7%, transparent) 1px, transparent 1px); background-size: 40px 40px; }
html.bg-fine body { background-image: linear-gradient(color-mix(in srgb, var(--accent) 14%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--accent) 14%, transparent) 1px, transparent 1px), linear-gradient(color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px); background-size: 96px 96px, 96px 96px, 16px 16px, 16px 16px; }
html.bg-lines body { background-image: linear-gradient(color-mix(in srgb, var(--ink) 8%, transparent) 1px, transparent 1px); background-size: 100% 34px; }
html.bg-diag body { background-image: repeating-linear-gradient(-45deg, color-mix(in srgb, var(--accent) 9%, transparent) 0 2px, transparent 2px 22px); background-size: auto; }
html.bg-plus body { background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='34' height='34'%3E%3Cpath d='M17 11v12M11 17h12' stroke='%23888' stroke-opacity='.28' stroke-width='1.5'/%3E%3C/svg%3E"); background-size: 34px 34px; }
html.bg-waves body { background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='40'%3E%3Cpath d='M0 20 Q15 8 30 20 T60 20 T90 20 T120 20' fill='none' stroke='%23888' stroke-opacity='.22' stroke-width='1.5'/%3E%3C/svg%3E"); background-size: 120px 40px; }
html.bg-topo body { background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cg fill='none' stroke='%23888' stroke-opacity='.2' stroke-width='1.3'%3E%3Cpath d='M-20 60 C60 20 120 110 200 60 S300 40 330 80'/%3E%3Cpath d='M-20 100 C70 60 120 150 210 100 S300 80 330 120'/%3E%3Cpath d='M-20 170 C50 130 130 220 200 170 S290 150 330 190'/%3E%3Cpath d='M-20 230 C80 190 120 280 210 230 S300 210 330 250'/%3E%3Cellipse cx='240' cy='150' rx='26' ry='14'/%3E%3Cellipse cx='240' cy='150' rx='12' ry='6'/%3E%3C/g%3E%3C/svg%3E"); background-size: 300px 300px; }
html.bg-rings body { background-image: radial-gradient(circle at 85% 0%, transparent 0 120px, color-mix(in srgb, var(--accent) 12%, transparent) 121px 122px, transparent 123px 200px, color-mix(in srgb, var(--accent) 10%, transparent) 201px 202px, transparent 203px 290px, color-mix(in srgb, var(--accent) 8%, transparent) 291px 292px, transparent 293px), radial-gradient(color-mix(in srgb, var(--ink) 9%, transparent) 1px, transparent 1.2px); background-size: auto, 26px 26px; background-repeat: no-repeat, repeat; background-attachment: fixed, scroll; }
html.bg-stars body { background-image: radial-gradient(1.4px 1.4px at 20px 30px, color-mix(in srgb, var(--ink) 40%, transparent), transparent), radial-gradient(1px 1px at 90px 120px, color-mix(in srgb, var(--ink) 30%, transparent), transparent), radial-gradient(1.8px 1.8px at 160px 60px, color-mix(in srgb, var(--accent) 60%, transparent), transparent), radial-gradient(1px 1px at 130px 170px, color-mix(in srgb, var(--ink) 30%, transparent), transparent); background-size: 200px 200px; }
html.bg-checker body { background-image: conic-gradient(color-mix(in srgb, var(--ink) 5%, transparent) 25%, transparent 0 50%, color-mix(in srgb, var(--ink) 5%, transparent) 0 75%, transparent 0); background-size: 48px 48px; }
html.bg-paper body { background-image: radial-gradient(70rem 30rem at 50% -8%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 70%); background-repeat: no-repeat; }

/* cards */
html.c-soft :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border: 1px solid color-mix(in srgb, var(--line) 70%, transparent); border-radius: 24px; box-shadow: 0 18px 40px -26px rgba(15, 20, 40, .35); }
html.c-outline :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border: 1.5px solid color-mix(in srgb, var(--ink) 55%, transparent); border-radius: 10px; box-shadow: none; }
html.c-brutal :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border: 2.5px solid var(--ink); border-radius: 6px; box-shadow: 5px 5px 0 var(--accent); }
html.c-flat :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border-color: transparent; border-radius: 16px; box-shadow: none; background: color-mix(in srgb, var(--accent-soft) 55%, var(--card)); }
html.c-ticket :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border: 2px dashed color-mix(in srgb, var(--ink) 30%, transparent); border-radius: 6px; box-shadow: none; }
html.c-pill :is(.idea, .cell, .stat, .hood-card, .faq details, .rel, .checks li) { border: 1.5px solid var(--line); border-radius: 30px; box-shadow: 0 3px 0 var(--line); }
html.c-brutal .frame { border-radius: 6px; box-shadow: 10px 10px 0 var(--accent); }
html.c-soft .frame { border-width: 1px; border-color: color-mix(in srgb, var(--line) 80%, transparent); border-radius: 22px; box-shadow: 0 40px 80px -40px rgba(15, 20, 40, .45); }
html.c-outline .frame { box-shadow: none; border-radius: 10px; }
html.c-flat .frame { border-color: transparent; box-shadow: 0 0 0 10px color-mix(in srgb, var(--accent-soft) 70%, transparent); }
html.c-ticket .frame { box-shadow: 0 0 0 8px var(--paper), 0 0 0 10px color-mix(in srgb, var(--ink) 25%, transparent); }
html.c-pill .frame { border-radius: 28px; }

/* section headings */
html.hd-marker section.block > h2::after { content: ""; display: block; width: 64px; height: 7px; margin: 16px auto 0; border-radius: 7px; background: var(--accent); }
html.hd-left section.block > :is(h2, .kicker) { text-align: left; margin-left: 0; }
html.hd-left section.block > h2 { max-width: 760px; }
html.hd-upper section.block > h2 { text-transform: uppercase; letter-spacing: .01em; font-size: clamp(28px, 4vw, 46px); }
html.hd-upper .kicker { letter-spacing: .22em; }
html.hd-italic section.block > h2 { font-style: italic; }
html.hd-outline .hero h1 .hl { color: transparent; -webkit-text-stroke: 2px var(--accent); }
html.hd-outline section.block > h2 { position: relative; }

/* hero layouts */
.hero.split.rev .hero-copy { order: 2; }
.hero.split.rev .frame { order: 1; }
.hero.split.rev .stats { order: 3; }
.hero.split .art { margin: 0 0 14px; --art-size: 96px; }
.hero.poster { text-align: left; max-width: 1240px; padding-top: 64px; }
.hero.poster .hero-top { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 40px; align-items: center; }
.hero.poster .art { --art-size: clamp(150px, 20vw, 250px); margin: 0; order: 2; }
.hero.poster h1 { font-size: clamp(46px, 8.6vw, 116px); margin: 20px 0 40px; max-width: none; line-height: .96; }
.hero.poster p.sub { margin-left: 0; }
.hero.poster .cta { justify-content: flex-start; }
.hero.poster .frame { transform: rotate(-1.2deg); margin-top: 60px; max-width: none; }
.hero.poster .stats { justify-content: flex-start; max-width: none; }
.hero.editorial { text-align: left; max-width: 1180px; padding-top: 64px; }
.hero.editorial .hero-top { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, .75fr); gap: 48px; align-items: center; border-bottom: 2px solid var(--ink); padding-bottom: 36px; }
.hero.editorial .art { --art-size: clamp(170px, 22vw, 280px); margin: 0 auto; }
.hero.editorial h1 { font-size: clamp(42px, 6.4vw, 84px); margin: 18px 0 20px; max-width: none; }
.hero.editorial p.sub { margin-left: 0; }
.hero.editorial .cta { justify-content: flex-start; }
.hero.editorial .stats { justify-content: flex-start; max-width: none; }
.hero:is(.poster, .editorial) .sticker { display: none; }
@media (max-width: 860px) {
  .hero.poster .hero-top, .hero.editorial .hero-top { grid-template-columns: 1fr; gap: 10px; }
  .hero.poster .art, .hero.editorial .art { --art-size: 120px; order: -1; margin: 0; }
  .hero.split.rev .hero-copy { order: 0; }
  .hero.poster .frame { transform: none; }
}
"""
