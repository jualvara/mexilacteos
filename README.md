# Proyecto Odoo: Buenas Prácticas y Control de Versiones

Este repositorio es una demostración técnica de la construcción de un módulo en Odoo 18, siguiendo un flujo de trabajo profesional dividido en etapas.

## Estructura de Ramas (Roadmap de Aprendizaje)

Para seguir el proceso de construcción paso a paso, cambia entre las siguientes ramas:

1.  **`step/01-scaffold-manifest`**: Estructura base del módulo, manifiesto, inicialización de paquetes y secuencias.
2.  **`step/02-orm-models-logic`**: Definición de modelos ORM, lógica de negocio, validaciones (`@api.constrains`) y soporte para Chatter.
3.  **`step/03-security-rules`**: Implementación de seguridad (Grupos de usuario, `ir.model.access.csv` y Record Rules).
4.  **`step/04-ui-ux-odoo18`**: Definición de la interfaz de usuario, menús, acciones de ventana y componentes dinámicos de Odoo 18.
5.  **`step/05-qa-final-review`**: Ajustes finales, pruebas de instalabilidad y optimizaciones de rendimiento.

## Cómo usar este repositorio

Cada rama es acumulativa. Si deseas ver el código específico de una etapa:
```bash
git checkout step/XX-nombre-de-la-rama
```

---
Desarrollado con ❤️ para la comunidad Odoo.
