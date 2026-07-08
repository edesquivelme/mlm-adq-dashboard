# Guía de Nomenclatura de Campañas — MLM Mercado Pago México
## Diccionario oficial de abreviaturas y códigos en nombres de campaña (Comms_OC)

> **Propósito**: Fuente de verdad para decodificar `CAMPAIGN_NAME_CLEAN` en la tabla Comms_OC.
> Leer SIEMPRE que se analice el nombre de una campaña antes de inferir su contexto.
>
> **Mantenimiento**: Actualizar cuando el equipo confirme el significado de un código nuevo.
> Nunca asumir el significado de un código sin confirmar — ver §4 Códigos no determinados.
>
> **Skills que usan este archivo**:
> - `skills/analizar-OC_Comms_skill.md` — Regla 6 (nombres de campaña)
> - `skills/OPTIMIZADOR-OC_skill.md` — FILTRO 2 (anti-alucinación)

---

## §1 — Estructura General del Nombre de Campaña

Los nombres siguen el patrón (no todos los campos son obligatorios):

```
[SITE]_[APP]_[APP2]-[CANAL]_[PRODUCTO]_[AUDIENCIA]_[TIPO]_[BL]_[SUFIJO]_[EQUIPO]-[VARIANTE]
```

**Ejemplo real decodificado**:
```
MLM_MP_ML-PUSHML_CC_MARA_AO-UCR_ALL_INST_X_X_DEFAULT_I-EG-UCR-MTK-NIA-MARA-V2
 │    │   │       │   │    │    │   │    │        │     │
 │    │   │       │   │    │    │   │    │        │     └─ Equipo/variante interna
 │    │   │       │   │    │    │   │    │        └─ Sufijo (DEFAULT = versión base)
 │    │   │       │   │    │    │   │    └─ Business Line (INST = INSTALLS)
 │    │   │       │   │    │    │   └─ Audiencia (ALL = todos)
 │    │   │       │   │    │    └─ Segmento de audiencia (UCR = Own Channels)
 │    │   │       │   │    └─ Tipo de campaña (AO = Always On)
 │    │   │       │   └─ Código interno [ver §4 — no confirmado]
 │    │   │       └─ PRODUCTO: CC = Consumer Credits / Meses sin Tarjeta ⚠️ NO = Credit Card
 │    │   └─ Canal: ML-PUSHML = Push via app MercadoLibre
 │    └─ App: MP = Mercado Pago
 └─ Sitio: MLM = México
```

---

## §1.5 — CAMPAÑAS CON TIMING CODIFICADO EN EL NOMBRE ⭐

Algunas campañas tienen el TIMING ÓPTIMO codificado directamente en su nombre.
Estas son de **máxima prioridad analítica** — fueron diseñadas para condiciones específicas.

| Código en nombre | Significado | Implicación analítica |
|---|---|---|
| `QUIN` | Enviada en quincena (días 14-16 o 29-31) | IS_semanal 1.20-1.30 — condición óptima documentada |
| `S2` | Semana 2 del mes (D8-16) | Segunda mejor ventana intra-mensual |
| `BF` | Buen Fin (+ verificar fecha Nov) | Amplificador estacional — ver Nivel 1 §5 |
| `HS` | Hot Sale (+ verificar fecha May) | Amplificador estacional |
| `0815` / `MMDD` | Fecha específica de envío codificada | Permite verificar exactamente cuándo fue |

**Caso documentado — campaña GOLD STANDARD**:
```
I-M-NR-CB-QUIN-A-0815
  I = Internal · M = México · NR = adquisición N+R
  CB = Cashback · QUIN = quincena (timing by design) · A = variante
  0815 = Agosto 15 = quincena 1 del mejor mes del año (IS Ago = 1.15)
  
TRIPLE AMPLIFICADOR: Cashback VP + Quincena (IS_semanal 1.25) + Agosto (IS 1.15)
Resultado: "muy buenos resultados" — confirma la combinación IS mensual × IS semanal × VP
```

**Protocolo de detección**: cuando se vea `QUIN`, `S2`, o una fecha `MMDD` en el nombre:
1. Verificar que la fecha de envío coincida con el período codificado
2. Comparar resultado vs comms del mismo VP sin timing codificado
3. La diferencia es el "premium de timing" — cuánto vale enviar en quincena vs fuera de quincena

---

## §1.7 — INFERENCIA DE VP DESDE EL NOMBRE DE CAMPAÑA

Cuando `CHANNELS_METRICS` (BL) es genérico (ej. `INSTALLS`) o hay STRING_AGG de múltiples valores,
el nombre de campaña puede revelar el VP real con mayor precisión.

### Protocolo de enriquecimiento automático VP_INFERIDO_NOMBRE

Para cada `CAMPAIGN_NAME_CLEAN`, tokenizar por `_` y `-` y asignar:

**1. VP_TIPO** — ¿Qué producto/incentivo se está ofreciendo?

| Token en nombre | VP_TIPO inferido | Descripción |
|---|---|---|
| `CB` / `CBK` | VP_CASHBACK | Cashback en % o $ |
| `CC` | VP_CONSUMER_CREDIT | Consumer Credits / Meses sin Tarjeta ⚠️ NO = Credit Card |
| `WLL` / `WALL` / `WLLT` | VP_WALLET | Saldo en billetera MP |
| `REC` / `RECA` / `RECAR` | VP_RECARGA | Recarga de saldo telefónico |
| `SVS` / `SVC` / `SERV` | VP_SERVICIOS | Pago de servicios (luz, agua, teléfono) |
| `PREST` / `PRST` | VP_PRESTAMO | Préstamo personal |
| `CRED` | VP_CREDITO | Crédito (general) |
| `TDD` | VP_TDD | Tarjeta de Débito MP |
| `TC` | VP_TC | Tarjeta de Crédito MP (producto físico) |
| `MYI` / `MYO` / `MONIN` / `DACCNT` | VP_MONEY_IN | Money In — depósito/fondeo de cuenta ("Ingresa $X y te damos $Y"). MYI y MYO son alias del mismo producto. |
| `INV` | VP_INVERSION | Fondo de inversión MP |
| `SEG` | VP_SEGUROS | Seguros |
| `PAG` | VP_PAGOS | Pagos QR / servicios |
| `CPN` | VP_CUPON | Cupón de descuento |
| `QUIN` / `QUINCENA` | — | No es VP, es TIMING (ver §1.5) |
| `NIA` | VP_UNKNOWN | Código interno no determinado |

**2. TRIGGER_TIPO** — ¿Qué acción del usuario disparó la comm?

| Token en nombre | TRIGGER_TIPO | Descripción |
|---|---|---|
| `POSTCOMPRA` | TRIGGER_POSTCOMPRA | Usuario acaba de comprar en ML — alta propensión |
| `DROPF` | TRIGGER_DROP_FUNNEL | Usuario abandonó el flujo de registro/activación |
| `RIND` | TRIGGER_REENGAGEMENT | Re-engagement individual |
| `ABANDONO` | TRIGGER_ABANDONO | Carrito o flujo abandonado |
| `CARRITO` | TRIGGER_CARRITO | Abandono de carrito en ML |
| `BIENVENID` / `BIENVENIDA` | TRIGGER_BIENVENIDA | Primera comunicación post-registro |
| `JNY` / `JOURNEY` | TRIGGER_JOURNEY | Journey automatizado por comportamiento |

**3. AUDIENCIA_NOMBRE** — ¿A quién va dirigida (según el nombre)?

| Token en nombre | AUDIENCIA_INFERIDA | Descripción |
|---|---|---|
| `UCR` / `UCR_ALL` | AUD_UCR_ALL | Todos los usuarios Own Channels |
| `UCR_EG` | AUD_UCR_EG | Sub-segmento E&G |
| `GRE` | AUD_GREEN | Perfil verde (bajo riesgo, buen historial) |
| `NAV` | AUD_NAVEGANTES | Navegantes ML sin compra |
| `RECOVERED` | AUD_RECOVERED | Churned que volvieron |
| `NEW` | AUD_NEW | Nuevos usuarios |
| `ACT` | AUD_ACTIVATION | Usuarios en proceso de activación |
| `ALL` | AUD_ALL | Audiencia total |

**4. ESTRATEGIA_NOMBRE** — Canal/Strategy del nombre (complementa datos BQ)

| Token en nombre | ESTRATEGIA_NOMBRE |
|---|---|
| `UCRANIA` / `UCR` | UCRANIA (Own Channels E&G) |
| `ACTIVATION` / `ACT` | ACTIVATION |
| `ADHOC` / `AH` | ADHOC |

### Ejemplo de enriquecimiento completo

```
CAMPAIGN_NAME_CLEAN: MLM-ML-I-EG-UCR-PUSH-NIA-POSTCOMPRA
BL (dato): INSTALLS
→ Enriquecimiento desde nombre:
  VP_TIPO:          VP_UNKNOWN (NIA = código desconocido)
  TRIGGER_TIPO:     TRIGGER_POSTCOMPRA ← esto SÍ es información valiosa
  AUDIENCIA_NOMBRE: AUD_UCR (UCR en nombre)
  CANAL_NOMBRE:     PUSH
  ESTRATEGIA_NOMBRE: UCRANIA (UCR en nombre)
→ Interpretación: "PUSH a audiencia UCR, disparado por post-compra en ML,
  VP desconocido (NIA). Esperar LIFT alto por ser trigger comportamental."

CAMPAIGN_NAME_CLEAN: I-M-NR-CB-QUIN-A-0815
→ Enriquecimiento desde nombre:
  VP_TIPO:          VP_CASHBACK (CB)
  TRIGGER_TIPO:     — (no es trigger, es AO)
  TIMING_NOMBRE:    QUIN (quincena) + fecha 0815 (Agosto 15)
  ESTRATEGIA_NOMBRE: [no explícita en nombre]
→ Interpretación: "Cashback de quincena, enviado Agosto 15 (IS 1.15 + S2)."
```

### Regla de prioridad (cuando nombre y dato BL difieren)

```
1. TRIGGER_TIPO del nombre → SIEMPRE priorizar sobre BL
   (POSTCOMPRA en nombre > BL=INSTALLS: la comm ES de post-compra)
2. VP_TIPO del nombre → usar como campo adicional (no reemplaza BL)
   (el BL del dato puede ser el segmento de negocio, el nombre el producto ofrecido)
3. AUDIENCIA_NOMBRE → complementar con Strategy del dato BQ
   (UCR en nombre + UCRANIA en Strategy = confirmado)
4. Si nombre dice algo diferente al dato → documentar como [inconsistencia nombre-dato]
   y reportar ambos al equipo para calibración
```

---

## §2 — Diccionario de Códigos CONFIRMADOS

### §2.1 — Sitio y App

| Código | Significado | Confirmado |
|---|---|---|
| `MLM` | México (site ID) | ✅ |
| `MLB` | Brasil | ✅ |
| `MP` | Mercado Pago (app) | ✅ |
| `ML` | MercadoLibre (app) | ✅ |

### §2.2 — Canal de envío

| Código | Significado | Notas |
|---|---|---|
| `PUSHML` | Push notification via app MercadoLibre | Mayor reach diario |
| `PUSHMP` | Push notification via app Mercado Pago | |
| `EMAIL` | Correo electrónico | |
| `WPP` | WhatsApp | |
| `PANDORA` | Pandora (placements in-app) | |
| `RE-DRW` | Real Estate — Drawer | |
| `RE-QA` | Real Estate — Quick Access | |
| `JOURNEY` | Push Journey (automation flow) | Ver BT_OC_MP_FLOWS_DAILY |

### §2.3 — Producto / VP (Value Proposition)

| Código | Significado real | ⚠️ ERROR COMÚN |
|---|---|---|
| `CC` | **Consumer Credits / Meses sin Tarjeta** | ❌ NO es "Credit Card" |
| `CBK` | Cashback | |
| `SVS` | Servicios (pagos de servicios) | |
| `CPN` | Cupón | |
| `CPN-SVS` | Cupón de Servicios | |
| `MYI` / `MYO` | **Money In** (depósito / fondeo de cuenta). MYI y MYO son el mismo producto. | |
| `MYI-CBK` | Money In + Cashback | |
| `MONIN` | Money In incentive — patrón "Ingresa $X y te damos $Y" | VP propenso a fatiga — ver OPTIMIZADOR Dimensión 7 |
| `DACCNT` | Depósito en Cuenta (Deposit Account) | Usualmente combinado con MONIN |
| `TDD` | Tarjeta de Débito | |
| `TC` | Tarjeta de Crédito (la tarjeta MP como producto, no como VP) | Diferente de CC |
| `INV` | Inversión / Fondo de inversión | |
| `SEG` | Seguros | |
| `REC` | Recargas (telefonía) | |
| `PAG` | Pagos | |
| `PREST` | Préstamo personal | |
| `CRED` | Crédito (general) | |

### §2.4 — Audiencia / Segmento

| Código | Significado | Notas |
|---|---|---|
| `UCR_ALL` | Todos los usuarios UCR (Own Channels) | Mayor reach posible |
| `UCR_EG` | UCR E&G (Engagement) | Sub-segmento UCR |
| `UCR` | Own Channels genérico | |
| `ALL` | Audiencia total sin segmentación adicional | |
| `INST` | Usuarios de installs / onboarding | Relacionado con BL=INSTALLS |
| `RECOVERED` | Usuarios recuperados (churned que volvieron) | CVR alto históricamente |
| `CHURNED` | Usuarios perdidos / inactivos | |
| `NAV` | Navegantes (usuarios que navegan ML sin comprar) | |
| `ACQ` | Acquisition audience | |
| `ACT` | Activation audience | |
| `GRE` | Green (usuarios de bajo riesgo / buen perfil) | |
| `OA` | Other audience | |

### §2.5 — Tipo de campaña

| Código | Significado | Notas |
|---|---|---|
| `AO` | Always On (campaña permanente, no temporal) | Infraestructura recurrente |
| `ADHOC` | Ad-Hoc (campaña puntual, no recurrente) | |
| `RECURRING` | Recurrente (envío periódico automatizado) | |
| `PROMOTIONAL` | Promocional (tiene VP/oferta específica) | |
| `TRIGGER` | Disparado por acción del usuario | POSTCOMPRA, DROPF, RIND |
| `POSTCOMPRA` | Trigger post-compra en ML | LIFT alto garantizado |
| `DROPF` | Drop funnel (usuario abandonó el flujo) | |
| `RIND` | Re-engagement individual | |

### §2.6 — Business Line (BL)

| Código | Significado | Notas |
|---|---|---|
| `INST` | Installs (onboarding de nuevos usuarios) | BL de mayor volumen en UCRANIA |
| `ACCOUNT_FUND` | Fondeo de cuenta / saldo | |
| `CREDIT_APP` | Solicitud de crédito personal | VPU alto |
| `CREDIT_BORR` | Crédito — tomadores activos | |
| `WALLET_UTIL` | Utilidades de la wallet (pagos, servicios) | |
| `NEW_INV` | Nuevos inversores | |

### §2.7 — Eventos internos MP (validar SIEMPRE con fecha)

> **Regla**: el código de evento en el nombre es evidencia SOLO si la fecha cae en el período.

| Código | Evento | Período típico México | ¿Fecha coincide? |
|---|---|---|---|
| `BF` | Buen Fin | 3ra semana de Noviembre | Verificar Nov semana 3 |
| `HS` | Hot Sale | Última semana de Mayo | Verificar May semana 4-5 |
| `LCDLF` | El Buen Fin de Agosto (La Caza del Ahorro / buen fin de verano) | Agosto–Octubre | Verificar Ago-Oct |
| `FIFA` | Copa Mundial FIFA / torneo FIFA activo | Depende del año | Verificar fechas del torneo |
| `JDV` | Juego de Verano | Julio-Agosto | Verificar Jul-Ago |
| `DBL` | Double Days / Días dobles de puntos | Variable | Verificar con calendario |
| `DD` | Double Days | Variable | Verificar con calendario |
| `INDEP` | Día de la Independencia | 15-16 Septiembre | Verificar Sep 15-16 |
| `NAVIDAD` | Navidad / Temporada navideña | Diciembre | Verificar Dic |
| `QUINCENA` / `QUIN` | **Campaña diseñada específicamente para envío en quincena** | Mensual | Verificar días 14-16 o 29-31 en FIRST_SENT_DATE ✅ Si coincide → inferencia VÁLIDA de timing |

---

## §3 — Códigos de Equipo / Sufijo interno

| Código | Significado probable | Confirmación |
|---|---|---|
| `I-EG-UCR` | Equipo E&G (Engagement & Growth) — canal UCR | ✅ Confirmado por contexto |
| `MTK` | Marketing | ⚠️ Inferido |
| `NIA` | Not Identified Acronym — código interno desconocido | ❌ No confirmado |
| `DEFAULT` | Versión base / control del experimento | ✅ Confirmado |
| `V1`, `V2`, `V3` | Versión del creativo | ✅ Confirmado |
| `INDIVIDUALS` | Team responsable: equipo de individuos/masivos | ✅ Confirmado (campo TEAM) |

---

## §4 — Códigos NO DETERMINADOS (no asumir su significado)

> Estos códigos aparecen en nombres de campaña pero su significado exacto **no ha sido confirmado**.
> Reportar siempre como `[Código interno — significado no determinado]`.

| Código | Aparece en | Hipótesis NO confirmada | Estado |
|---|---|---|---|
| `MARA` | CC_MARA (Jun-25, Sep-25) | ~~Maratón CDMX~~ — DESCARTADO: aparece en Jun cuando el Maratón fue en Ago | ❌ Desconocido |
| `W_W` | W_W-ALL (Jun-25) | Weekend? World Wide? | ❌ Desconocido |
| `CARABO` | UCR_JNY_CARABO (Abr-26) | Código de journey | ❌ Desconocido |
| `MST2MP` | UCR_JNY_MST2MP (Abr-26) | **Meses Sin Tarjeta → Mercado Pago** (conversión de usuario a Consumer Credits MP). MST = Meses sin Tarjeta (mismo producto que CC). 2MP = to Mercado Pago. | ⚠️ Alta confianza — pendiente confirmación equipo |
| `FAVOR` | UCR_JNY_FAVOR | Favoritos? | ❌ Desconocido |
| `CARO` | UCR_JNY_CARO | Carob? Código interno? | ❌ Desconocido |
| `FAVORITOS` | UCR_JNY_FAVORITOS | Sección favoritos de ML | ⚠️ Inferido, no confirmado |
| `RH` | flows_RH (Jun-25) | Recursos Humanos? Código creativo? | ❌ Desconocido |
| `FJ` | flows_FJ | Código creativo interno | ❌ Desconocido |
| `b1m` | flows_b1m | Bottom 1 month? | ❌ Desconocido |
| `u0q` | flows_u0q | Código de segmento | ❌ Desconocido |
| `a4h` | flows_a4h | Audience 4 hours? | ❌ Desconocido |
| `SOL_ENC` | MLM_I_EG_NEW_TC_SOL_ENC | Solicitud + Encuesta? | ⚠️ Inferido |
| `mer` | flows_..._mer_... | Miércoles (día de envío) | ✅ Alta confianza — patrón consistente en datos |

---

## §5 — Regla de Interpretación (para Skills)

```
PASO 1: Tokenizar el nombre por separadores (_, -, .)
PASO 2: Buscar cada token en §2 (CONFIRMADOS) → asignar significado con [dato]
PASO 3: Para tokens en §4 (NO DETERMINADOS) → reportar [Código interno — no confirmado]
PASO 4: Para códigos de EVENTO (§2.7):
  · Si la fecha de la campaña cae en el período del evento → [dato inferido — nombre+fecha coinciden]
  · Si la fecha NO coincide → [Código interno — fecha no coincide con el evento]
  · Si no hay datos de fecha → [inf — requiere verificar fecha]
PASO 5: Antes de proponer amplificador externo → agotar explicación por IS + WoM + DoW

EJEMPLO CORRECTO:
  CC_MARA en Jun-25:
    CC   → Consumer Credits / Meses sin Tarjeta [dato — §2.3]
    MARA → [Código interno — significado no determinado §4]
    Jun  → IS 1.01, S1/Dom — condiciones basales
  Análisis: "El motor CC (Consumer Credits) + PUSH + UCR_ALL genera 19K en condiciones
  basales (IS 1.01, S1, Dom). MARA es código interno sin significado confirmado."
```

---

## §6 — Cómo actualizar este archivo

Cuando el equipo confirme el significado de un código:
1. Mover de §4 (No determinados) a §2 (Confirmados) o §3 (Equipo)
2. Anotar la fecha de confirmación y quién confirmó
3. Actualizar `skills/CHANGELOG.md` con la entrada

**Última actualización**: 2026-04-20
**Confirmaciones pendientes de equipo**: MARA, W_W, CARABO, MST2MP, FAVOR, CARO
