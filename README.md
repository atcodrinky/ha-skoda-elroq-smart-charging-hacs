# Skoda Elroq Smart Charging – HACS Integration

> Custom component Python per Home Assistant, basato sulla logica del repository [ha-skoda-elroq-smart-charging](https://github.com/atcodrinky/ha-skoda-elroq-smart-charging).

Questa integrazione trasforma la raccolta di automazioni YAML in un **custom component installabile via HACS**, con configurazione grafica, sensori, switch e number entity nativi.

---

## Funzionalità

| Funzione | Descrizione |
|---|---|
| ☀️ Surplus FV | Regolazione dinamica della corrente in base all'eccedenza fotovoltaica |
| 🌙 Notturna F3 | Ricarica durante la fascia off-peak italiana |
| ⚡ Load Balancing | Prevenzione dello sforamento della potenza contrattuale |
| 🔋 Dual SOC Target | Target SOC separato per utente e veicolo |
| 🚀 Forza Ricarica | Override immediato indipendente da fascia/solare |
| 🛑 Master Stop | Blocco globale di tutte le ricariche |
| 📡 MQTT | Comunicazione diretta con Silla Prism |

---

## Installazione via HACS

1. In HACS → **Integrazioni** → menu ⋮ → **Repository personalizzati**
2. Aggiungere l'URL del repository, categoria `Integrazione`
3. Installare **Skoda Elroq Smart Charging**
4. Riavviare Home Assistant
5. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** → cercare *Skoda Elroq*

---

## Configurazione

### Step 1 – Parametri principali
- **Topic base MQTT** del wallbox Silla Prism (default: `prism/1`)
- **Potenza contratto** in Watt (default: 5700 W)
- **Capacità batteria** del veicolo in kWh (default: 59 kWh per Elroq 60)

### Step 2 – Selezione entità
Seleziona le entità già presenti in HA fornite da:
- **Skoda Connect** (SOC, cavo collegato, limite di carica)
- **Silla Prism MQTT** (stato wallbox)
- **Meter/Inverter** (potenza rete, FV, wallbox, tensione)
- **PUN Sensor** (fascia tariffaria F1/F2/F3)

---

## Entità create dall'integrazione

### Sensori
| Entità | Descrizione |
|---|---|
| `sensor.charging_mode` | Modalità ricarica corrente |
| `sensor.pv_surplus` | Surplus fotovoltaico disponibile (W) |
| `sensor.target_soc` | SOC target attivo |
| `sensor.charging_time_remaining` | Tempo rimanente stimato |
| `sensor.charge_end_time` | Orario fine ricarica stimato |
| `sensor.wallbox_current_target` | Corrente target teorica da FV (A) |

### Switch
| Entità | Descrizione |
|---|---|
| `switch.master_stop` | Blocco globale ricarica |
| `switch.force_charge` | Forza ricarica immediata |
| `switch.solar_controller_active` | Controllo solare attivo |

### Number (regolabili dalla UI)
| Entità | Descrizione |
|---|---|
| `number.user_soc_target` | Target SOC utente (%) |
| `number.vehicle_soc_target` | Target SOC veicolo (%) |
| `number.contract_power_limit` | Potenza contrattuale (W) |
| `number.allowed_grid_import` | Import rete permesso in modalità FV (W) |
| `number.night_charging_power_limit` | Limite potenza notturna (W) |

### Select
| Entità | Descrizione |
|---|---|
| `select.charging_mode_select` | Selezione manuale modalità ricarica |

---

## Logica di controllo

```
Veicolo collegato
        │
        ▼
Master Stop? → SÌ → STOP (revoca autorizzazione)
        │ NO
        ▼
Forza Ricarica? → SÌ → Ricarica fino a Vehicle Target
        │ NO
        ▼
Fascia F3? → SÌ → Ricarica fino a User Target (con load balancing)
        │ NO
        ▼
Surplus FV ≥ 6A? → SÌ → Ricarica solare fino a Vehicle Target
        │ NO
        ▼
In attesa
```

---

## Servizi HA disponibili

```yaml
skoda_elroq_smart_charging.authorize_charging
skoda_elroq_smart_charging.revoke_charging
skoda_elroq_smart_charging.set_charge_limit   # current_a: 6-16
```

---

## Integrazioni esterne richieste
- [Skoda Connect](https://www.home-assistant.io/integrations/) – dati veicolo
- [PUN Sensor](https://github.com/virtualdj/pun_sensor) – fasce tariffarie italiane
- MQTT Broker – comunicazione con Silla Prism

---

## Struttura file

```
custom_components/skoda_elroq_smart_charging/
├── __init__.py          # Setup integrazione e servizi
├── coordinator.py       # Logica smart charging + MQTT
├── config_flow.py       # UI configurazione guidata
├── const.py             # Costanti
├── sensor.py            # Sensori derivati
├── switch.py            # Switch (Master Stop, Forza, Solare)
├── number.py            # Parametri regolabili
├── select.py            # Selezione modalità
├── manifest.json        # Metadati integrazione
├── strings.json         # Testi UI
└── translations/
    └── it.json          # Traduzione italiana
```
