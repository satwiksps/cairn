# Indexing API

The CLI adds effect-approval gates around these functions. Direct callers must implement equivalent authorization for network access, deletion, empty-corpus publication, and configuration migration.

```{autoclass} steadlith.index.service.PreparedIndex
:members:
```

```{autoclass} steadlith.index.service.ApplyResult
:members:
```

```{autofunction} steadlith.index.service.prepare_index
```

```{autofunction} steadlith.index.service.apply_prepared
```

```{autofunction} steadlith.index.service.index_status
```

```{autofunction} steadlith.index.service.query_index
```

```{autofunction} steadlith.index.service.compact_index
```

```{autofunction} steadlith.index.service.verify_index
```

## Plan models

```{autoclass} steadlith.index.plan.IndexPlan
:members:
```

```{autoclass} steadlith.index.plan.PlanOperation
:members:
```

```{autoclass} steadlith.index.plan.CostEstimate
:members:
```
