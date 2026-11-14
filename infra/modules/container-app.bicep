// One FastAPI service as a Container App: public HTTPS ingress on port 8000,
// scale to zero, config only through environment variables.

param name string
param location string
param environmentId string

@description('Value of SERVICE_NAME, also used as the container name.')
param serviceName string

param image string

@secure()
param databaseUrl string

@secure()
param apiKey string

@description('The UI origin allowed by CORS.')
param corsOrigin string

@description('Extra plain environment variables, as {name, value} objects.')
param extraEnv array = []

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'api-key'
          value: apiKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: serviceName
          image: image
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: concat(
            [
              {
                name: 'SERVICE_NAME'
                value: serviceName
              }
              {
                name: 'DATABASE_URL'
                secretRef: 'database-url'
              }
              {
                name: 'API_KEY'
                secretRef: 'api-key'
              }
              {
                name: 'CORS_ORIGIN'
                value: corsOrigin
              }
            ],
            extraEnv
          )
        }
      ]
      // Scale to zero when idle. The first request after that waits for a cold start,
      // and the database may need up to a minute to resume from auto-pause.
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output url string = 'https://${app.properties.configuration.ingress.fqdn}'
