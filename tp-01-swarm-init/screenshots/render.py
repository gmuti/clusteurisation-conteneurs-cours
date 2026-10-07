import sys, os, re
from PIL import Image, ImageDraw, ImageFont
os.chdir(sys.argv[1]); os.makedirs("screenshots", exist_ok=True)
F = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)
FB = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 15)
BG, BAR, FG, GREEN, GREY, YEL, RED = "#1e1e2e", "#313244", "#cdd6f4", "#a6e3a1", "#7f849c", "#f9e2af", "#f38ba8"

def blocks(path):
    out, cur = [], None
    for l in open(path, encoding="utf-8").read().replace("\r", "").split("\n"):
        if l.startswith("$ ") or (l.startswith("# ") and not (cur and cur[-1].startswith("#"))):
            cur = [l]; out.append(cur)
        elif cur is not None:
            cur.append(l.rstrip())
    for b in out:
        while b and b[-1] == "": b.pop()
    return out

def render(name, title, parts, highlight=(), drop=None):
    lines = []
    for path, idx in parts:
        bl = blocks(path)
        for i in (idx if idx is not None else range(len(bl))):
            lines += bl[i] + [""]
    lines = lines[:-1]
    if drop:
        kept = []
        for l in lines:
            if re.search(drop, l):
                if not kept or kept[-1] != " […]": kept.append(" […]")
            else: kept.append(l)
        lines = kept
    cw, lh, pad, bar = F.getlength("M"), 20, 18, 34
    w = int(max(F.getlength(l) for l in lines) + 2 * pad); w = max(w, 700)
    h = bar + pad * 2 + lh * len(lines)
    img = Image.new("RGB", (w, h), BG); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w, bar], 0, fill=BAR)
    for i, c in enumerate(["#f38ba8", "#f9e2af", "#a6e3a1"]):
        d.ellipse([14 + i * 20, 11, 26 + i * 20, 23], fill=c)
    d.text((w / 2, bar / 2), title, font=F, fill=GREY, anchor="mm")
    y = bar + pad
    for l in lines:
        if l.startswith("$ "):
            d.text((pad, y), "$", font=FB, fill=GREEN); d.text((pad + 2 * cw, y), l[2:], font=FB, fill=FG)
        elif l.startswith("#"):
            d.text((pad, y), l, font=F, fill=GREY)
        else:
            col = FG
            for pat, c in highlight:
                if re.search(pat, l): col = c
            d.text((pad, y), l, font=F, fill=col)
        y += lh
    img.save(f"screenshots/{name}.png"); print(name, img.size)

T = "Git Bash — tp-01-swarm-init"
C = "captures/"
HL = [(r"\bDown\b|Shutdown|6/4", RED), (r"=>|4/4|Healthy|joined|initialized|converged", GREEN), (r"^t\+", YEL)]
render("01-noeuds", T, [(C+"01-preparation-noeuds.txt", [0, 1])], HL, drop=r"Creating|Starting|Started|Waiting|^ Container .*Created|Network .*Created")
render("01b-versions", T, [(C+"01-preparation-noeuds.txt", [2, 3, 4, 5])], HL)
render("02-swarm-init", T, [(C+"02-swarm-init-join.txt", [0])], HL)
render("03-swarm-join", T, [(C+"02-swarm-init-join.txt", [2, 3, 4])], HL)
render("04-service-create", T, [(C+"03-service-create.txt", None)], HL)
render("05-repartition-avant", T, [("cluster-status-before.txt", [1, 3, 4, 5, 6])], HL)
render("06-panne", T, [(C+"04-panne-worker1.txt", [0, 6])], HL)
render("07-etat-apres", T, [("cluster-status-after.txt", [1, 2, 3, 6]), ("service-ps.txt", [2])], HL)
render("08-bonus-retour-worker1", T, [(C+"05-bonus-retour-worker1.txt", None)], HL)
