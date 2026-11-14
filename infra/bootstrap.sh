#!/usr/bin/env bash
# One-time setup so the CD workflow can deploy. Run from the repo root by someone
# with Owner on the Azure subscription and admin on the GitHub repo:
#
#   az login && gh auth login
#   ./infra/bootstrap.sh
#
# It creates the resource group and the deploy identity (infra/bootstrap.bicep),
# the GitHub environment "production" (main branch only), and that environment's
# variables and secrets. Safe to re-run: existing secrets are kept unless you pass
# --rotate-secrets. Secret values are generated here and never printed.
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-sdd-splitwise}"
LOCATION="${LOCATION:-spaincentral}"
REPO="${REPO:-Ruben-Penning/SDD-Group-Project}"
ENVIRONMENT=production

rotate=false
[[ "${1:-}" == "--rotate-secrets" ]] && rotate=true

echo "Registering resource providers (first time only, can take a few minutes)"
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace "$ns" --wait --output none
done

echo "Creating $RESOURCE_GROUP and the deploy identity"
outputs=$(az deployment sub create \
  --name bootstrap \
  --location "$LOCATION" \
  --template-file infra/bootstrap.bicep \
  --parameters resourceGroupName="$RESOURCE_GROUP" location="$LOCATION" githubRepo="$REPO" \
  --query properties.outputs --output json)
output() { jq -r ".$1.value" <<<"$outputs"; }

echo "Creating the GitHub environment $ENVIRONMENT (deploys from main only)"
gh api --method PUT "repos/$REPO/environments/$ENVIRONMENT" --input - >/dev/null <<'JSON'
{"deployment_branch_policy": {"protected_branches": true, "custom_branch_policies": false}}
JSON

echo "Setting environment variables"
gh variable set AZURE_CLIENT_ID --repo "$REPO" --env "$ENVIRONMENT" --body "$(output clientId)"
gh variable set AZURE_TENANT_ID --repo "$REPO" --env "$ENVIRONMENT" --body "$(output tenantId)"
gh variable set AZURE_SUBSCRIPTION_ID --repo "$REPO" --env "$ENVIRONMENT" --body "$(output subscriptionId)"
gh variable set AZURE_RESOURCE_GROUP --repo "$REPO" --env "$ENVIRONMENT" --body "$RESOURCE_GROUP"

# 32 random letters and digits, plus one of each kind so Azure SQL's
# complexity rule always passes.
random_secret() { printf '%sAa1' "$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 32)"; }

existing=$(gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name')
for name in SQL_ADMIN_PASSWORD API_KEY; do
  if $rotate || ! grep -qx "$name" <<<"$existing"; then
    random_secret | gh secret set "$name" --repo "$REPO" --env "$ENVIRONMENT"
  else
    echo "$name already set, keeping it"
  fi
done

echo "Done. The next merge to main (or Actions > CD > Run workflow) deploys the app."
