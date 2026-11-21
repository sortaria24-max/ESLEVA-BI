# ESLEVA-BI

Repositorio del proyecto de implantación de un Sistema de Inteligencia de Negocio en **Estampaciones Levante S.A. (ESLEVA)**, desarrollado para la asignatura *09MBID Soluciones de Inteligencia de Negocio*.

> **Nota:** ESLEVA es una empresa ficticia. Todos los datos de este repositorio son sintéticos y se han generado específicamente para este proyecto.

## Escenario

ESLEVA es un proveedor de segundo nivel (Tier 2) del sector de la automoción, dedicado a la fabricación de componentes metálicos estampados y subconjuntos soldados. Cuenta con 240 personas, tres líneas de prensas y dos células de soldadura robotizada, y trabaja en tres turnos. Su información está dispersa entre el ERP y diversas herramientas departamentales, y el objetivo del proyecto es integrarla en un único modelo analítico en Power BI.

## Estructura del repositorio

```
ESLEVA-BI/
├── generador/      Script de Python que genera los datos sintéticos
├── datos/
│   ├── sql/        Scripts de creación y carga de la base de datos PostgreSQL (ERP)
│   ├── excel/      Ficheros departamentales: calidad y presupuesto
│   └── mes/        Ficheros CSV mensuales del sistema de captura de planta (MES)
├── powerbi/        Proyecto de Power BI y script de Python para el cálculo del OEE
└── docs/figuras/   Diagramas de arquitectura y del modelo de datos
```

## Fuentes de datos

| Fuente | Tipo | Ubicación | Contenido |
|---|---|---|---|
| ERP | Base de datos PostgreSQL (Supabase) | `datos/sql/` | Clientes, productos, pedidos, órdenes de fabricación, compras |
| Calidad | Excel | `datos/excel/calidad_ESLEVA.xlsx` | Inspecciones y reclamaciones de cliente |
| Presupuesto | Excel | `datos/excel/presupuesto_ESLEVA.xlsx` | Presupuesto mensual por familia de producto |
| MES | CSV | `datos/mes/mes_AAAA_MM.csv` | Producción y paradas por máquina y turno |

Periodo de los datos: enero de 2024 a octubre de 2026.

## Acceso a la base de datos

*Pendiente.* Aquí se indicarán el servidor, la base de datos y las credenciales de solo lectura. Si no fuera posible acceder a la base de datos en la nube, puede recrearse en cualquier instancia de PostgreSQL ejecutando en orden los scripts de `datos/sql/`.

## Regenerar los datos

*Pendiente.* Instrucciones para ejecutar `generador/generar_datos_ESLEVA.py`.

## Estado del proyecto

- [x] Diseño del escenario, de las fuentes y del modelo de datos
- [ ] Generación de los datos
- [ ] Carga de la base de datos en Supabase
- [ ] Proyecto de Power BI: ETL, modelo, DAX e informes
