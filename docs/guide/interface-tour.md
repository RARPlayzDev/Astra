# Interface Tour

ASTRA follows a classic desktop-application layout.

```
┌──────────────────────────────────────────────────────────────────┐
│ ASTRA   File  View  Run  Tools  Help                ASTRA 1.0.0 │  ← menu bar
├──────────────────────────────────────────────────────────────────┤
│ [▶ Start Mission] [⏹ Stop] │ Rate [v] │ Diagnostics │ User Guide │  ← toolbar
│                               Home  Ops  Analysis  Intel  Geo   │  ← perspectives
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                     workspace (perspective)                       │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ ● RUNNING - slot 1247/2400    ASTRA    port 54321                │  ← status bar
└──────────────────────────────────────────────────────────────────┘
```

## Menu bar

| Menu | Entries | Purpose |
|---|---|---|
| **File** | New mission · Open scenario · Export results · Exit | Mission control, file I/O, shutdown |
| **View** | Home · Operations · Analysis · Intelligence · Geolocation · Data & Sources · Full screen | Perspective switching |
| **Run** | Start / Stop paired mission · Rate presets | Mission control and simulation speed |
| **Tools** | Diagnostics | Self-test of the installation |
| **Help** | User guide · About | This documentation; version information |

## Perspectives

| Perspective | Purpose |
|---|---|
| **Home** | Dashboard: headline stats, quick actions, system status |
| **Operations** | Live paired A/B mission with waterfall displays |
| **Analysis** | KPP gate table, Monte Carlo results, figure gallery |
| **Intelligence** | Emitter identification board with threat classification |
| **Geolocation** | Multi-receiver AOA triangulation with CEP analysis |
| **Data & Sources** | Sensor feeds, scenarios, model training |

## Toolbar

Run controls (start/stop), simulation-rate selector, quick access to
Diagnostics and User Guide.

## Status bar

Live state: `READY` or `RUNNING - slot n/T`, the product name, and the local port.
