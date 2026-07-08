Lee el skill `MLM_ADQ_Dash/skills/analizar-OC_Comms_skill.md` y aplica sus instrucciones completas.

Contexto de datos: `MLM_ADQ_Dash/skills/analizar-OC_Comms_context.md`
Contexto de negocio adicional: `MLM_ADQ_Dash/docs/OC_POM_master_context.md`

El argumento del usuario (si existe) determina el modo:
- Sin argumento → modo `juicio_rapido`
- `historicos` → modo historicos (mejores/peores períodos, qué se hizo)
- `canal push` / `canal pandora` / `canal re` / `canal wpp` → modo canal
- `timing` → modo timing (cuándo enviar qué)
- `wording` → modo wording (qué VPs y formatos funcionan)
- `patrones` → modo patrones (qué tienen en común las mejores/peores comms)
- `waterfall [mes]` → modo waterfall para ese mes específico
- `top_campaigns` → modo top_campaigns (requiere datos del usuario)
- Cualquier pregunta libre → responder con el framework del skill

Modo invocado: $ARGUMENTS
