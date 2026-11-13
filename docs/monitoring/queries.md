# Monitoring queries

Both services log one JSON line per request to stdout, for example:

```json
{"service":"settlements","method":"GET","path":"/groups/{group_id}/settle-up","status":200,"duration_ms":84}
```

Container Apps sends stdout to the environment's Log Analytics workspace, in the
`ContainerAppConsoleLogs_CL` table. Every query below parses the JSON, keeps only our
request lines, and leaves out `/health` so the pipeline's health checks don't skew the
numbers.

Run them in Azure Portal → Log Analytics workspace → **Logs**, then **Save → Save as query**.

## 1. Request count (per 5 minutes, per service)

```kusto
ContainerAppConsoleLogs_CL
| extend e = parse_json(Log_s)
| where isnotempty(e.service) and tostring(e.path) != "/health"
| summarize requests = count() by service = tostring(e.service), bin(TimeGenerated, 5m)
| render timechart
```

## 2. Error rate (status ≥ 500, per service)

```kusto
ContainerAppConsoleLogs_CL
| extend e = parse_json(Log_s)
| where isnotempty(e.service) and tostring(e.path) != "/health"
| summarize total = count(), errors = countif(toint(e.status) >= 500)
    by service = tostring(e.service), bin(TimeGenerated, 5m)
| extend error_rate_pct = round(100.0 * errors / total, 2)
| project TimeGenerated, service, error_rate_pct
| render timechart
```

## 3. Response time (p50 and p95, per service)

```kusto
ContainerAppConsoleLogs_CL
| extend e = parse_json(Log_s)
| where isnotempty(e.service) and tostring(e.path) != "/health"
| summarize p50_ms = percentile(todouble(e.duration_ms), 50),
            p95_ms = percentile(todouble(e.duration_ms), 95)
    by service = tostring(e.service), bin(TimeGenerated, 5m)
| render timechart
```

## 4. SLO: settle-up

**Objective:** 99% of `GET /groups/{group_id}/settle-up` requests return a non-5xx
status in under 1000 ms, measured over 7 days.

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(7d)
| extend e = parse_json(Log_s)
| where tostring(e.service) == "settlements"
    and tostring(e.method) == "GET"
    and tostring(e.path) endswith "/settle-up"
| summarize total = count(),
            good = countif(toint(e.status) < 500 and todouble(e.duration_ms) < 1000)
| extend slo_pct = round(100.0 * good / total, 2), target_pct = 99.0
| extend met = slo_pct >= target_pct
```

**Cold starts:** both Container Apps scale to zero and the databases auto-pause, so the
first request after idle can take tens of seconds. The SLO measures the service while
it is running; cold starts are a deliberate cost trade-off, recorded in `decisions.md`.
