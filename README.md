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
└── docs/           Guía para recrear la base de datos y figuras del diseño
```

## Fuentes de datos

| Fuente | Tipo | Ubicación | Contenido |
|---|---|---|---|
| ERP | Base de datos PostgreSQL (Supabase) | `datos/sql/` | Clientes, productos, pedidos, órdenes de fabricación, compras |
| Calidad | Excel | `datos/excel/calidad_ESLEVA.xlsx` | Inspecciones y reclamaciones de cliente |
| Presupuesto | Excel | `datos/excel/presupuesto_ESLEVA.xlsx` | Presupuesto mensual por familia de producto |
| MES | CSV | `datos/mes/mes_AAAA_MM.csv` | Producción y paradas por máquina y turno |
| Portal de clientes | API REST (Supabase) | `datos/sql/03_api_previsiones.sql` | Previsiones semanales de demanda de cada cliente por familia |

Periodo de los datos: enero de 2024 a octubre de 2026.

## Acceso a la base de datos

La base de datos del ERP está alojada en Supabase (PostgreSQL) y puede consultarse con un usuario de **solo lectura**:

| Parámetro | Valor |
|---|---|
| Servidor | `aws-1-eu-west-1.pooler.supabase.com` |
| Puerto | `5432` |
| Base de datos | `postgres` |
| Usuario | `lector_esleva.fcpxbuhuzvqyjrlwejgv` |
| Contraseña | `09MBID_lector` |

En Power BI Desktop: **Obtener datos > Base de datos PostgreSQL**, servidor `aws-1-eu-west-1.pooler.supabase.com:5432`, base de datos `postgres`, modo **Importar**; en la ventana de credenciales, elige **Base de datos** e introduce el usuario y la contraseña anteriores. Las tablas están en el esquema `public`.

Este usuario solo puede leer las tablas, no modificarlas. El plan gratuito de Supabase pausa los proyectos tras un periodo de inactividad; si la conexión falla por ese motivo, puede solicitarse su reactivación o recrear la base de datos en local.

Si no fuera posible acceder a la base de datos en la nube, puede recrearse en cualquier instancia de PostgreSQL siguiendo la guía paso a paso [Cómo recrear la base de datos](docs/recrear_base_de_datos.md).

## Regenerar los datos

Todos los ficheros de `datos/` se generan con el script `generador/generar_datos_ESLEVA.py`. Usa una semilla fija, de modo que cada ejecución produce exactamente los mismos datos. Desde la carpeta raíz del repositorio:

```bash
pip install -r generador/requirements.txt
python generador/generar_datos_ESLEVA.py
```

El script sobrescribe los ficheros de `datos/sql/`, `datos/excel/` y `datos/mes/` y muestra al final un resumen con el número de filas generadas.

### Particularidades de las fuentes

- Los CSV del MES usan el punto y coma (`;`) como separador y contienen algunos registros duplicados.
- El Excel de presupuesto tiene un título en la primera fila y filas de `TOTAL` que deben eliminarse en la transformación.
- El Excel de calidad contiene fechas en formatos mixtos, variantes en los nombres, celdas vacías y duplicados, como ocurre con los registros manuales reales.

## Estado del proyecto

- [x] Diseño del escenario, de las fuentes y del modelo de datos
- [x] Generación de los datos
- [x] Carga de la base de datos en Supabase
- [ ] Proyecto de Power BI: ETL, modelo, DAX e informes
