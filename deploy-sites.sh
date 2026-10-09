#!/usr/bin/env bash
# Clones tharkacoding/om (branch with the polished sites) and deploys the five
# sites in sites/ to Vercel as projects t1..t5, then turns login protection off.
# Needs: git, gh (already logged in), node/npm. Run:  bash deploy-sites.sh
set -euo pipefail

REPO="tharkacoding/om"
BRANCH="claude/friendly-lamport-y8hz5r"
DIR="${OM_DIR:-$HOME/om-sites}"
SCOPE_ARGS=()
[ -n "${VERCEL_SCOPE:-}" ] && SCOPE_ARGS=(--scope "$VERCEL_SCOPE")

# t-name : folder
SITES=("t1:ln-dental" "t2:spine-reset" "t3:nimrah-cafe" "t4:z-square-banquets" "t5:lime-boutique-suites")

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1 - please install it and re-run."; exit 1; }; }
need git; need gh; need node; need npm
gh auth status >/dev/null 2>&1 || { echo "gh is not logged in. Run: gh auth login"; exit 1; }

if [ -d "$DIR/.git" ]; then
  echo ">> Updating $DIR"
  git -C "$DIR" fetch origin "$BRANCH"
  git -C "$DIR" checkout "$BRANCH"
  git -C "$DIR" pull --ff-only origin "$BRANCH"
else
  echo ">> Cloning $REPO ($BRANCH) into $DIR"
  gh repo clone "$REPO" "$DIR" -- --branch "$BRANCH"
fi

command -v vercel >/dev/null 2>&1 || { echo ">> Installing Vercel CLI"; npm install -g vercel; }

if ! vercel whoami "${SCOPE_ARGS[@]}" >/dev/null 2>&1; then
  echo ">> Log in to Vercel (a browser window will open)"
  vercel login
fi
echo ">> Deploying as: $(vercel whoami "${SCOPE_ARGS[@]}" 2>/dev/null | tail -1)"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
printf '{"ssoProtection":null}' > "$TMP/open.json"
RESULTS=()

for entry in "${SITES[@]}"; do
  name="${entry%%:*}"; folder="${entry##*:}"
  echo; echo "=== $name  ($folder) ==="
  cd "$DIR/sites/$folder"
  vercel link --yes --project "$name" "${SCOPE_ARGS[@]}"
  url="$(vercel deploy --prod --yes "${SCOPE_ARGS[@]}" | tail -1)"
  # make the site public (no Vercel login wall); best effort
  vercel api "/v9/projects/$name" --method PATCH --input "$TMP/open.json" "${SCOPE_ARGS[@]}" >/dev/null 2>&1 \
    || echo "   (could not auto-disable protection: Vercel dashboard > $name > Settings > Deployment Protection > Vercel Authentication: Off)"
  RESULTS+=("$name  $folder  $url")
done

echo; echo "================ DONE ================"
printf '%s\n' "${RESULTS[@]}"
echo "Open each link in a private window to confirm it loads without a login."
