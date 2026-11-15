// One-time setup, run by infra/bootstrap.sh with an Owner account: the resource
// group and the identity GitHub Actions deploys with. No secret is created here:
// GitHub signs in through OIDC (a federated credential), so there is no password
// or client secret to leak.

targetScope = 'subscription'

param resourceGroupName string

@allowed([
  'spaincentral'
  'norwayeast'
  'germanywestcentral'
  'italynorth'
  'polandcentral'
])
param location string = 'spaincentral'

@description('GitHub repository as owner/name.')
param githubRepo string

@description('The same repository with GitHub IDs, as owner@ownerId/name@repoId. GitHub puts this form in the OIDC subject for this repo.')
param githubRepoWithIds string

@description('GitHub environment the CD job runs in. Only that environment can sign in.')
param githubEnvironment string = 'production'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

module deployIdentity 'modules/deploy-identity.bicep' = {
  name: 'deploy-identity'
  scope: rg
  params: {
    location: location
    // GitHub may send either form of the subject, so trust both.
    subjects: [
      'repo:${githubRepo}:environment:${githubEnvironment}'
      'repo:${githubRepoWithIds}:environment:${githubEnvironment}'
    ]
  }
}

output clientId string = deployIdentity.outputs.clientId
output tenantId string = tenant().tenantId
output subscriptionId string = subscription().subscriptionId
