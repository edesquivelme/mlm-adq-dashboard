# Diccionario de Métricas y Reglas de Negocio - MLM ADQ Dash v2

Este documento contiene la lógica estricta para el cálculo de KPIs en la pestaña "Performance". NUNCA inferir cálculos fuera de estas reglas ni leer datos de Excels crudos.

## 1. Métricas de Volumen (N+R)
**KPI**: N+R Total
* **Fuente BQ**: `PANEL_MONTHLY_DAILY_HISTORICO`
* **Cálculo**: Suma absoluta de usuarios adquiridos y reactivados por canal y mes.

**KPI**: N+R Paid
* **Fuente BQ**: `PANEL_MONTHLY_COSTOS_CANALES`
* **Lógica**: Volumen de usuarios N+R en las filas donde `INVERSION_TOTAL_USD > 0`.

**KPI**: N+R Free
* **Cálculo Matemático**: `N+R Total - N+R Paid`

## 2. Métricas de Inversión (Costos)
**Regla de Oro**: Todos los cálculos en backend/SQL (incluyendo CPA) DEBEN usar valores absolutos. La conversión a M (Millones) o K (Miles) es exclusivamente una máscara visual de Frontend al momento de renderizar.

**KPI**: Inversión Canal
* **Fuente BQ**: `PANEL_MONTHLY_COSTOS_CANALES`
* **Cálculo Base**: `SUM(COSTO_CANAL)` (Valor absoluto).
* **Formato Visual**: `M USD` (Dividir entre 1,000,000).

**KPI**: Inversión Incentivos
* **Fuente BQ**: `PANEL_MONTHLY_COSTOS_CANALES`
* **Cálculo Base**: `SUM(COSTO_INCENTIVOS)` (Valor absoluto).
* **Formato Visual**: `M USD` (Dividir entre 1,000,000).

**KPI**: Inversión Mantika
* **Fuente BQ**: `PANEL_MONTHLY_COSTOS_CANALES`
* **Cálculo Base**: `SUM(COSTO_MANTIKA)` (Valor absoluto).
* **Formato Visual**: `K USD` (Dividir entre 1,000).

**KPI**: Inversión Total
* **Fuente BQ**: `PANEL_MONTHLY_COSTOS_CANALES`
* **Cálculo Base**: `SUM(INVERSION_TOTAL_USD)` (Valor absoluto).
* **Formato Visual**: `M USD` (Dividir entre 1,000,000).
* **Casos Borde**: Los canales `L&P ADQ` y `L&P ACT` tienen `no_cost=true`.

## 3. Métricas de Eficiencia (CPA)
**KPI**: CPA Blend
* **Cálculo Matemático**: `Inversión Total / N+R Total` (Usar valores absolutos).
* **Manejo de Errores**: Si `N+R Total` es 0 o nulo, devolver 0.

**KPI**: CPA Paid
* **Cálculo Matemático**: `Inversión Total / N+R Paid` (Usar valores absolutos).
* **Manejo de Errores**: Si `N+R Paid` es 0 o nulo, devolver 0.

## 4. Métricas de Valor Predicho y VPU
**KPI**: Valor Pred 90D
* **Fuente BQ**: `PANEL_MONTHLY_DAILY_HISTORICO`
* **Columna Base**: `VALUE_MKT_PREDICTION_90D_NR_USERS` (Este valor en BQ ya es absoluto y viene pre-multiplicado por NR).
* **Cálculo**: `SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)`

**KPI**: VPU (Value Per User Promedio)
* **Cálculo Matemático**: `Valor Pred 90D / N+R Total`
* **Casos Borde Críticos**: Canales como POM y MGM tienen `VALUE_PRED=0` en la tabla de costos. Por lo tanto, el cruce de datos debe garantizar que el `Valor Pred 90D` de estos canales se extraiga siempre de la tabla histórica `PANEL_MONTHLY_DAILY_HISTORICO` y nunca de la tabla de costos.



## 5. Métricas de Retorno (ROA / ROAS)
**Regla de Oro**: El cálculo del numerador (Valor Predicho) cambia dependiendo del canal debido a asimetrías en las fuentes de datos. El denominador SIEMPRE es la Inversión Total (en valores absolutos) calculada previamente.

**KPI**: ROA (Return on Assets / Ad Spend)
* **Cálculo Base**: `Numerador VALUE_PRED / Inversión Total`
* **Lógica del Numerador por Canal**:
  * [cite_start]**UCR+OC**: `SUM(VALUE_PRED)` de la tabla `PANEL_MONTHLY_COSTOS_CANALES`, aplicando el filtro estricto de `INVERSION_TOTAL_USD > 0` y `STRATEGY IN ('ACTIVATION','UCRANIA')`.
  * [cite_start]**POM**: `SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)` de la tabla `PANEL_MONTHLY_DAILY_HISTORICO`, donde `CHANNEL IN ('POM ACQ','POM')` y `STRATEGY IN ('ACQUISITION','ACTIVATION')`.
  * [cite_start]**Others (ej. MGM)**: `SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)` de la tabla `PANEL_MONTHLY_DAILY_HISTORICO`, donde `CHANNEL='MGM'` y `STRATEGY='ACQUISITION'`.
  * [cite_start]**Orgánico**: No tiene inversión asociada, por lo que el ROA es nulo (`null` o `—`).




  ## 6. Mapeo del Resumen Plan 2026 y Equivalencias de Negocio
**Regla de Oro Arquitectónica**: EL LLM (Claude) debe procurar NO debe leer el archivo CSV/Excel crudo ni generar código que busque filas por texto. Esto consume tokens innecesarios, rompe el principio de eficiencia y es propenso a fallos. La extracción de datos del Plan 2026 DEBE hacerse EXCLUSIVAMENTE por índice de fila (`iloc`).

### A. Piedra Rosetta: Equivalencias Negocio vs. Plan
La asignación estricta de las líneas del Excel (`Resumen Plan Acq 2026.xlsx`) hacia los Canales/Subcanales del Dashboard es la siguiente. **Esta lógica rige para TODOS los bloques de KPIs (N+R, VPU, Valor, CPA e Inversión):**

* **Nodos POM**:
  * `POM Total` = Línea "POM gest".
  * `POM no gestionado` = Línea "POM no gestionado".
* **Nodos OC + UCR**:
  * `UCR Gest + OC ACT Recurring` (Agrupado) = Línea "OC Recurring".
  * `UCR Gest + OC ACT Ad-Hoc` (Agrupado) = Línea "OC Adhoc".
  * `UCR PRD` = Líneas "Others" + "Producto" (Sumadas).
  * `OC + UCR` (Nodo Padre) = Líneas "OC Recurring" + "OC Adhoc" + "Others" + "Producto" (Sumadas).
* **Otros Nodos Base**:
  * `Organico` = Línea "No Atribuido / Organico".
  * `MGM Total` = Línea "MGM".
  * `L&P Total` = Línea "L&P".

### B. Mapa de Coordenadas Absolutas (Desplazamiento de Bloques)
El orden de los canales en el Excel se repite idénticamente en cada bloque de KPIs. El código Python debe mapear la fila base (N+R) definida en el JSON y aplicar los siguientes índices absolutos de inicio:

* **Bloque N+R (Base)**: Fila Excel 1-30 
* **Bloque VPU**: Inicia en la fila Excel 35 (`iloc[34]`).
* **Bloque Valor**: Inicia en la fila Excel 51 (`iloc[50]`).
* **Bloque CPA**: Inicia en la fila Excel 67 (`iloc[66]`).
* **Bloque Inversión Total USD**: Inicia en la fila Excel 83 (`iloc[81]`).e