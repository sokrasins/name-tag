#!/usr/bin/env bash
# Render 3D images of both nametag PCBs, export the back board's schematic as a
# PDF, and generate the back board's interactive BOM
# (docs/assembly/assembly_ibom.html) and printable assembly guides in color and
# grayscale (docs/assembly/assembly_guide.pdf and assembly_guide_grayscale.pdf,
# via scripts/assembly_doc.py) into docs/ using kicad-cli (KiCad 9+), the
# InteractiveHtmlBom plugin and rsvg-convert.
#
# Usage: scripts/render_pcbs.sh [top|bottom|both]   (default: top)
#
# Environment overrides:
#   KICAD_CLI  path to kicad-cli (default: found on PATH, or the macOS app bundle)
#   QUALITY    basic | high | user (default: basic; see lighting note below)
#   WIDTH      image width in px (default: 1920)
#   HEIGHT     image height in px (default: 1440)
#   BACKGROUND transparent | opaque | default (default: transparent)
#   PADDING    margin in px left around each board after cropping (default: 24)
#   IBOM       path to InteractiveHtmlBom's generate_interactive_bom.py
#              (default: found in KiCad's 3rd-party plugin directory)
#   PCBNEW_PYTHON python that can import KiCad's pcbnew module, used to hide
#              User layers in the back board renders and to run the
#              interactive BOM and assembly guide (default: the first of
#              KiCad's bundled python, python3, /usr/bin/python3 that can)
#
# The interactive BOM is skipped with a warning if the plugin or a python with
# pcbnew can't be found; the assembly guide is skipped if a python with pcbnew
# or rsvg-convert can't be found.
#
# Renders are cropped to the board with ImageMagick (magick or convert) when it
# is installed; without it they keep kicad-cli's full-size margins. Cropping
# only works on the transparent background: the opaque one is a gradient.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$repo_root/docs"
assembly_dir="$out_dir/assembly"
render_dir="$out_dir/renders"

# board name -> .kicad_pcb path (relative to the repo root)
boards=(
  "nametag_back:pcbs/nametag_back/nametag_back.kicad_pcb"
  "nametag_front:pcbs/nametag_front/nametag_front.kicad_pcb"
)

# Root schematic; the PDF includes every hierarchical sheet. Only the back
# board has a schematic.
schematic="pcbs/nametag_back/nametag_back.kicad_sch"

sides="${1:-top}"
case "$sides" in
  top) sides=(top) ;;
  bottom) sides=(bottom) ;;
  both) sides=(top bottom) ;;
  *) echo "usage: $0 [top|bottom|both]" >&2; exit 2 ;;
esac

kicad_cli="${KICAD_CLI:-}"
if [[ -z "$kicad_cli" ]]; then
  if command -v kicad-cli >/dev/null 2>&1; then
    kicad_cli="kicad-cli"
  elif [[ -x /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli ]]; then
    kicad_cli="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
  else
    echo "error: kicad-cli not found; install KiCad 9+ or set KICAD_CLI" >&2
    exit 1
  fi
fi

# Look for "render" in the pcb subcommand list rather than trusting an exit
# code: kicad-cli 9 exits nonzero from --help even when the command exists.
pcb_help="$("$kicad_cli" pcb --help 2>&1 || true)"
if ! grep -qE '^[[:space:]]+render[[:space:]]' <<<"$pcb_help"; then
  echo "error: '$kicad_cli' has no 'pcb render' command (requires KiCad 9+)" >&2
  exit 1
fi

mkdir -p "$out_dir" "$render_dir"

magick_cmd=()
if command -v magick >/dev/null 2>&1; then
  magick_cmd=(magick)
elif command -v convert >/dev/null 2>&1; then
  magick_cmd=(convert)
else
  echo "warning: ImageMagick not found; renders will not be cropped" >&2
fi

# pcbnew only loads in the python KiCad was built against. -E ignores
# PYTHONHOME/PYTHONPATH, which other toolchains (e.g. nRF Connect) set to their
# own python and which would otherwise break it.
pcbnew_python="${PCBNEW_PYTHON:-${IBOM_PYTHON:-}}"
if [[ -z "$pcbnew_python" ]]; then
  for py in \
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
    python3 \
    /usr/bin/python3; do
    if "$py" -E -c 'import pcbnew' >/dev/null 2>&1; then
      pcbnew_python="$py"
      break
    fi
  done
fi

# Boards whose renders hide every User layer (User.Drawings, User.Comments,
# User.Eco1/2, User.1-45). The "follow_plot_settings" preset doesn't hide the
# User.N layers, so these boards are rendered from a temporary copy with the
# user-layer graphics deleted.
hide_user_layers=(nametag_back)

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

# strip_user_layers SRC_PCB DST_PCB: copy SRC_PCB to DST_PCB without the
# graphics on User layers. The project file comes along so text variables and
# other project settings still resolve.
strip_user_layers() {
  local src="$1" dst="$2"
  cp "${src%.kicad_pcb}.kicad_pro" "${dst%.kicad_pcb}.kicad_pro" 2>/dev/null || true
  "$pcbnew_python" -E - "$src" "$dst" <<'PY'
import sys
import pcbnew

src, dst = sys.argv[1:3]
board = pcbnew.LoadBoard(src)
user = {l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsUserLayer(l)}

for item in list(board.GetDrawings()):
    if item.GetLayer() in user:
        board.Delete(item)
zones = [board.GetArea(i) for i in range(board.GetAreaCount())]
for zone in zones:
    if all(l in user for l in zone.GetLayerSet().Seq()):
        board.Delete(zone)
for fp in board.GetFootprints():
    for item in list(fp.GraphicalItems()):
        if item.GetLayer() in user:
            fp.Delete(item)
    for field in fp.GetFields():
        if field.GetLayer() in user:
            field.SetVisible(False)

pcbnew.SaveBoard(dst, board)
PY
}

for entry in "${boards[@]}"; do
  name="${entry%%:*}"
  pcb="$repo_root/${entry#*:}"
  if [[ " ${hide_user_layers[*]} " == *" $name "* ]]; then
    if [[ -z "$pcbnew_python" ]]; then
      echo "warning: no python can import pcbnew; $name renders will show User layers (set PCBNEW_PYTHON)" >&2
    else
      mkdir -p "$tmp_dir/$name"
      stripped="$tmp_dir/$name/$(basename "$pcb")"
      strip_user_layers "$pcb" "$stripped"
      pcb="$stripped"
    fi
  fi
  for side in "${sides[@]}"; do
    # The top render keeps the filename the README already links to.
    if [[ "$side" == top ]]; then
      out="$render_dir/${name}_render.png"
    else
      out="$render_dir/${name}_render_${side}.png"
    fi
    echo "Rendering $name ($side) -> ${out#"$repo_root"/}"
    # Lighting: "high" quality ray-traces shadows from the side lights, which
    # leave a blotchy halo around the battery holder, so render without them.
    # Brightness comes from low side lights rather than the top/camera lights:
    # on the glossy mask those reflect straight into the camera, washing the
    # color out to gray and leaving a hotspot in the middle of the board.
    "$kicad_cli" pcb render \
      --side "$side" \
      --quality "${QUALITY:-basic}" \
      --background "${BACKGROUND:-transparent}" \
      --width "${WIDTH:-1920}" \
      --height "${HEIGHT:-1440}" \
      --light-side 0.8 \
      --light-side-elevation 40 \
      --light-top 0.05 \
      --light-camera 0.1 \
      --output "$out" \
      "$pcb"

    # Crop to the board, then pad it back out with the background color, read
    # from the corner pixel.
    if (( ${#magick_cmd[@]} )); then
      bg="$("${magick_cmd[@]}" "$out" -format '%[pixel:p{0,0}]' info:)"
      "${magick_cmd[@]}" "$out" -trim +repage \
        -bordercolor "$bg" -border "${PADDING:-24}" "$out"
    fi
  done
done

# Take the revision from the root sheet's title block, e.g. (rev "1") -> _rev1.
# Characters that don't belong in a filename become '-'.
rev="$(awk '
  /\(title_block/ { in_tb = 1 }
  in_tb && match($0, /\(rev "[^"]*"\)/) {
    print substr($0, RSTART + 6, RLENGTH - 8)
    exit
  }
  in_tb && /^\t\)/ { exit }
' "$repo_root/$schematic" | tr -c 'A-Za-z0-9._\n-' '-')"
if [[ -n "$rev" ]]; then
  schematic_pdf="nametag_back_schematic_rev${rev}.pdf"
else
  echo "warning: no revision in $schematic title block; omitting it from the filename" >&2
  schematic_pdf="nametag_back_schematic.pdf"
fi

echo "Exporting schematic -> docs/$schematic_pdf"
"$kicad_cli" sch export pdf \
  --output "$out_dir/$schematic_pdf" \
  "$repo_root/$schematic"

# Interactive BOM for the back board (the front board has no components).
ibom="${IBOM:-}"
if [[ -z "$ibom" ]]; then
  for dir in \
    "$HOME/.local/share/kicad"/*/3rdparty/plugins \
    "$HOME/Documents/KiCad"/*/3rdparty/plugins; do
    if [[ -f "$dir/org_openscopeproject_InteractiveHtmlBom/generate_interactive_bom.py" ]]; then
      ibom="$dir/org_openscopeproject_InteractiveHtmlBom/generate_interactive_bom.py"
    fi
  done
fi

if [[ -z "$ibom" ]]; then
  echo "warning: InteractiveHtmlBom plugin not found; skipping docs/assembly/assembly_ibom.html (set IBOM)" >&2
elif [[ -z "$pcbnew_python" ]]; then
  echo "warning: no python can import pcbnew; skipping docs/assembly/assembly_ibom.html (set PCBNEW_PYTHON)" >&2
else
  echo "Generating interactive BOM -> docs/assembly/assembly_ibom.html"
  mkdir -p "$assembly_dir"
  "$pcbnew_python" -E "$ibom" \
    --no-browser \
    --dest-dir "$assembly_dir" \
    --name-format assembly_ibom \
    --dark-mode \
    --show-pads \
    --show-fabrication \
    --hide-silkscreen \
    --highlight-pin1 none \
    --checkboxes "Sourced,Placed" \
    --bom-view left-right \
    --layer-view F \
    --show-fields "Value,Footprint" \
    "$repo_root/pcbs/nametag_back/nametag_back.kicad_pcb"
fi

# Printable assembly guide: one page per component, for the back board.
if [[ -z "$pcbnew_python" ]]; then
  echo "warning: no python can import pcbnew; skipping the assembly guides (set PCBNEW_PYTHON)" >&2
elif ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "warning: rsvg-convert not found; skipping the assembly guides (brew install librsvg)" >&2
else
  for variant in color grayscale; do
    if [[ "$variant" == color ]]; then
      guide=assembly_guide.pdf; flags=()
    else
      guide=assembly_guide_grayscale.pdf; flags=(--grayscale)
    fi
    echo "Generating assembly guide ($variant) -> docs/assembly/$guide"
    "$pcbnew_python" -E "$repo_root/scripts/assembly_doc.py" \
      ${flags[@]+"${flags[@]}"} \
      --output "$assembly_dir/$guide" \
      "$repo_root/pcbs/nametag_back/nametag_back.kicad_pcb"
  done
fi
