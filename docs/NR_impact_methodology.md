# NR Impact Methodology — Pestaña 🦅 Análisis OC+UCR
# ==============================================================================
# PROPÓSITO:
#   Explica cómo se calcula el NR Impact de cada palanca del Plan 1.5M OC.
#   Fuente de verdad para auditar o actualizar los números del dashboard.
#
# PRINCIPIO DE CONSERVADURISMO:
#   Todos los valores en el dashboard usan el PISO del rango (mínimo comprobable).
#   No el techo, no el promedio. Si no podemos defender el mínimo, no ponemos el número.
#
# FUENTE PRINCIPAL: skills/analizar-Optimizar_Performance_KPIs_context.md
# ÚLTIMA VALIDACIÓN: 13-Abr-2026 (datos hasta Mar-26)
# ==============================================================================

---

## PALANCA 1 — WPP Ucrania Always On

**NR Impact en dashboard**: `+25K/mes`

### Cómo se calculó
```
Audiencia objetivo : 6M usuarios UCR sin opt-in Push (§A9)
Lift conservador   : 0.4% (vs 0.5% reportado en §C4 O9 — usamos −20% de margen)
Cálculo            : 6,000,000 × 0.004 = 24,000 → redondeado a 25K
Referencia fuente  : Monthly Mar-26 §10.1 cita "+25–30K NR/mes"
Valor en dashboard : piso del rango = 25K
```

### Por qué es conservador
- El lift de 0.5% viene de estimación del equipo, no de test A/B validado
- Se aplica un descuento del 20% al lift para absorber incertidumbre de opt-in rates y reach real
- Cualquier resultado ≥ 25K confirma la tesis; resultados menores requieren revisar el lift

---

## PALANCA 2 — Gamification (checkpoint + multi-target)

**NR Impact en dashboard**: `+15K/mes`

### Cómo se calculó
```
Fuente             : Monthly Mar-26 §10.1 y §C4 O10 estiman "+15–20K NR/mes"
Valor en dashboard : piso del rango = 15K
Contexto           : MYI single-target tiene techo documentado (~80% NR concentrado)
                     Nuevas mecánicas activan el segmento que no responde a MYI
```

### Supuestos clave
- Requiere features Gami E&G (≠ Gami Negocio) — blocker activo
- El +15K asume adopción gradual en los primeros 2-3 meses tras lanzamiento
- No incluye efecto compuesto del Bandit optimizando la mecánica

---

## PALANCA 3 — Nuevos Espacios ML (Favoritos, Carrito, Home)

**NR Impact en dashboard**: `+8K/mes al escalar`

### Cómo se calculó
```
Audiencia          : ~10M navegadores en alta intención de compra (§C4 O3)
Fuentes separadas  :
  - Espacio Favoritos/Carrito  → +20K NR/mes (§C4 O3, Monthly Mar-26 p.112)
  - MP en Search ML            → +11K NR/mes (§C4 O4, Monthly Mar-26 p.112)
Período de madurez : Q3 (estos espacios tardan 3-4 meses en escalar post-lanzamiento)
Valor "al escalar" : 8K = estimado de los primeros meses antes de madurar (40% del pico)
Pico maduro        : ~20K+ (no se promete en el dashboard — demasiado incierto en timeline)
```

### Por qué "+8K al escalar" y no el pico
- Las negociaciones con MeLi no están cerradas (§C4 O2/O3/O4 en estado "En negociación")
- El +8K es el impacto realista en los primeros 60 días post-lanzamiento
- Se actualizará cuando se tenga el acuerdo firmado y datos de prueba piloto

---

## PALANCA 4 — Pandora Ramp Up + CC Attribution + Incentivos

**NR Impact en dashboard**: `+4K/mes por track`

### Cómo se calculó
```
Fuentes            :
  - Pandora Always On UCR 85%  → +4.5K NR/mes (§C4 O6)
  - Pandora Always On ACT 85%  → +6.0K NR/mes (§C4 O7)
  Total ambos tracks : +10.5K NR/mes

Estado actual      : BLOQUEADO — calibrador en 0.2 (§B5b, §C4 O6/O7 marcados 🔴)
  Calibrador 0.2 = −47% UCR, −56% ACT vs calibrador 0.6

Valor por track    : 4K = piso del menor track (UCR: 4.5K → redondeado a 4K)
                     Cuando el calibrador suba: el impacto real será 4.5K–6K por track
```

### Nota crítica
- **Este número SOLO aplica cuando el calibrador sube de 0.2 a ≥ 0.6**
- Con calibrador en 0.2 el impacto neto es NEGATIVO (−7.2K NR/mes vs baseline)
- El dashboard muestra el potencial a liberar, no el estado hoy

---

## PALANCA 5 — Segmentación por Valor (KYC, FS not-in-app, Meli+)

**NR Impact en dashboard**: `+10K/mes al madurar`

### Cómo se calculó
```
Audiencias identificadas       :
  - KYC: ~10M usuarios (6x conversión en tests vs sin KYC — §C4 O8, Weekly Mar-26 §11)
  - FS not-in-app: ~4.1M usuarios
  - Meli+: ~720K usuarios

Lift KYC estimado  : 6x vs baseline de ~0.02% CVR = 0.12% CVR
Cálculo KYC        : 10M × 0.0012 = 12,000 → piso 10K (descuento 20% por incertidumbre)
Valor en dashboard : 10K = conservador, solo KYC. FS y Meli+ son upside adicional no prometido.
```

### Por qué solo KYC en el piso
- FS not-in-app y Meli+ no tienen test A/B validado de lift en OC
- KYC tiene la evidencia más sólida (test directo con 6x conversión)
- Los 3 segmentos combinados son el upside del escenario optimista, no el base

---

## TRACK 0 — Atribución CC Incrementales

**NR Impact en dashboard**: `+7K «found» N+R`

### Cómo se calculó
```
Base de referencia : 149K NR/mes (Mar-26 real — §B1)
Rango documentado  : 5–8% de N+R "found" (§C3 R7)
Cálculo piso       : 149,000 × 0.05 = 7,450 → redondeado a 7K

Por qué "found"    : Este N+R YA SE GENERA pero no se atribuye al canal correcto.
                     No es N+R incremental nuevo — es N+R que ya existe y no se cuenta.
                     Por eso el badge es diferente (no verde sino ámbar).
```

### Diferencia vs otras palancas
- Las palancas 1-5 generan **N+R nuevo** que hoy no existe
- Track 0 "encuentra" N+R que **ya se genera** pero se atribuye mal
- Impacto en decisiones: con atribución correcta, el presupuesto se reasigna hacia los canales que realmente convierten → efecto multiplicador sobre las demás palancas

---

## QUICK WINS — Metodología de los totales

**Total en dashboard**: `+15K N+R/mes adicionales en Abril`

| Quick Win | Piso NR | Fuente del cálculo |
|---|---|---|
| Protocolo Pandora circuit-breaker | Condicionado a calibrador | Impacto solo si cal sube en Abr |
| Reasignación 5-10pp POM ACQ → OC | **+6K** | 10pp × inversión mensual OC × elasticidad X-Channel (§A11) |
| Push VP Servicios/Pagos + Recargas | **+2K** | CPA $0.6-0.8, escalar audiencia 30% con VPs probados (§A5) |
| WPP Ucrania lanzamiento Q2 | Habilitador — impacto desde May | No se suma al total de Abr |
| Bandit RL Push POC → escalar | **+3K** | Resultado piloto 3.5K/mes × descuento 15% por incertidumbre de escala |
| **Total sin Pandora** | **+11–15K** | Solo palancas ejecutables sin depender de calibrador externo |

> **Por qué 15K y no 22K**: el rango anterior incluía palancas cuyo impacto depende de la
> subida del calibrador de Pandora — una variable que el equipo no controla directamente.
> El piso conservador son las palancas que el equipo puede ejecutar hoy mismo.

---

## REGLA DE ORO PARA FUTURAS ACTUALIZACIONES

```
1. Siempre usa el PISO del rango, no el techo ni el promedio
2. Si el número viene de una estimación sin test A/B validado → aplica −20% de descuento
3. Si el número depende de una variable externa (calibrador, acuerdo MeLi) →
   marca como "condicional" y no lo sumes al total base
4. Cuando llegue el dato real: actualizar esta tabla + builders_analysis.py + CHANGELOG.md
5. Todo número en el dashboard necesita tener una fila en este archivo
```
