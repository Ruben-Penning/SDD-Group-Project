// Everything the app runs on. The CD pipeline deploys this file on every merge to
// main, with the images built for that commit.
//
// Azure for Students only allows five regions (spaincentral, norwayeast,
// germanywestcentral, italynorth, polandcentral). Static Web Apps is not offered in
// any of them, so the UI is served as a Storage static website instead. The Azure SQL
// free offer is not available in spaincentral, so everything runs in germanywestcentral.

@description('Short lowercase name at the start of every resource name.')
@maxLength(16)
param prefix string = 'sdd-splitwise'

@description('Must be one of the allowed regions and support the Azure SQL free offer.')
@allowed([
  'germanywestcentral'
  'italynorth'
  'polandcentral'
])
param location string = 'germanywestcentral'

@description('expenses-service image, for example ghcr.io/owner/repo/expenses:<sha>.')
param expensesImage string

@description('settlements-service image, for example ghcr.io/owner/repo/settlements:<sha>.')
param settlementsImage string

param sqlAdminLogin string = 'sqladmin'

@secure()
param sqlAdminPassword string

@description('Shared demo key. The UI sends it as X-API-Key, so it is visible in the browser by design.')
@secure()
param apiKey string

@description('When the monthly free Azure SQL allowance runs out: BillOverUsage keeps the databases online and bills the credit, AutoPause takes them offline until next month.')
@allowed([
  'BillOverUsage'
  'AutoPause'
])
param freeLimitExhaustionBehavior string = 'BillOverUsage'

var suffix = uniqueString(resourceGroup().id)

// ---------- Logs: request lines from both services end up here ----------

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ---------- UI: static website in a storage account ----------

resource uiStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stui${suffix}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    // The static website endpoint is public on its own; no anonymous blob access needed.
    allowBlobPublicAccess: false
  }
}

// primaryEndpoints.web ends with a slash; CORS needs the bare origin.
var uiWebEndpoint = uiStorage.properties.primaryEndpoints.web
var uiOrigin = take(uiWebEndpoint, length(uiWebEndpoint) - 1)

// ---------- Databases: one serverless database per service ----------

resource sql 'Microsoft.Sql/servers@2023-08-01' = {
  name: '${prefix}-sql-${suffix}'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

// 0.0.0.0 is Azure's marker for "allow Azure services", which covers Container Apps.
resource allowAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01' = {
  parent: sql
  name: 'AllowAllWindowsAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource databases 'Microsoft.Sql/servers/databases@2023-08-01' = [
  for db in ['expenses', 'settlements']: {
    parent: sql
    name: db
    location: location
    sku: {
      name: 'GP_S_Gen5'
      tier: 'GeneralPurpose'
      family: 'Gen5'
      capacity: 1
    }
    properties: {
      // Azure SQL free offer: 100,000 vCore seconds and 32 GB per database per month.
      useFreeLimit: true
      freeLimitExhaustionBehavior: freeLimitExhaustionBehavior
      autoPauseDelay: 60
      minCapacity: json('0.5')
      maxSizeBytes: 34359738368
      zoneRedundant: false
      requestedBackupStorageRedundancy: 'Local'
    }
  }
]

func databaseUrl(server string, login string, password string, database string) string =>
  'mssql+pyodbc://${login}:${uriComponent(password)}@${server}:1433/${database}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30'

// ---------- Container Apps: both services, scale to zero ----------

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

module expenses 'modules/container-app.bicep' = {
  name: 'expenses-app'
  params: {
    name: '${prefix}-expenses'
    location: location
    environmentId: environment.id
    serviceName: 'expenses'
    image: expensesImage
    databaseUrl: databaseUrl(sql.properties.fullyQualifiedDomainName, sqlAdminLogin, sqlAdminPassword, 'expenses')
    apiKey: apiKey
    corsOrigin: uiOrigin
  }
  dependsOn: [
    databases
    allowAzureServices
  ]
}

module settlements 'modules/container-app.bicep' = {
  name: 'settlements-app'
  params: {
    name: '${prefix}-settlements'
    location: location
    environmentId: environment.id
    serviceName: 'settlements'
    image: settlementsImage
    databaseUrl: databaseUrl(sql.properties.fullyQualifiedDomainName, sqlAdminLogin, sqlAdminPassword, 'settlements')
    apiKey: apiKey
    corsOrigin: uiOrigin
    extraEnv: [
      {
        name: 'EXPENSES_URL'
        value: expenses.outputs.url
      }
    ]
  }
  dependsOn: [
    databases
    allowAzureServices
  ]
}

output expensesUrl string = expenses.outputs.url
output settlementsUrl string = settlements.outputs.url
output uiUrl string = uiOrigin
output uiStorageAccount string = uiStorage.name
