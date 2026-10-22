#!/usr/bin/env bash
# Render 3D images of both nametag PCBs and export the back board's schematic
# as a PDF into docs/ using kicad-cli (KiCad 9+).
#
# Usage: scripts/render_pcbs.sh [top|bottom|both]   (default: top)
#
# Environment overrides:
#   KICAD_CLI  path to kicad-cli (default: found on PATH, or the macOS app bundle)
#   QUALITY    basic | high | user (default: basic; see lighting note below)
#   WIDTH      image width in px (default: 1920)
#   HEIGHT     image height in px (default: 1440)
#   BACKGROUND transparent | opaque | default (default: transparent)

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$repo_root/docs"

# board name -> .kicad_pcb path (relative to the repo root)
boards=(
  "nametag_back:nametag_back/nametag_back.kicad_pcb"
  "nametag_front:nametag_front/nametag_front.kicad_pcb"
)

# Root schematic; the PDF includes every hierarchical sheet. Only the back
# board has a schematic.
schematic="nametag_back/nametag_back.kicad_sch"

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

if ! "$kicad_cli" pcb render --help >/dev/null 2>&1; then
  echo "error: '$kicad_cli' has no 'pcb render' command (requires KiCad 9+)" >&2
  exit 1
fi

mkdir -p "$out_dir"

for entry in "${boards[@]}"; do
  name="${entry%%:*}"
  pcb="$repo_root/${entry#*:}"
  for side in "${sides[@]}"; do
    # The top render keeps the filename the README already links to.
    if [[ "$side" == top ]]; then
      out="$out_dir/${name}_render.png"
    else
      out="$out_dir/${name}_render_${side}.png"
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
