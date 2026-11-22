# Cómo recrear la base de datos del ERP de ESLEVA

Esta guía explica, paso a paso, cómo obtener una copia idéntica de la base de datos PostgreSQL que simula el ERP de Estampaciones Levante S.A. (ESLEVA). Sirve para el caso en que la base de datos alojada en Supabase no esté disponible, por ejemplo porque el servicio gratuito la haya pausado por inactividad.

La base de datos se reconstruye íntegramente con dos scripts SQL incluidos en este repositorio:

| Orden | Script | Qué hace |
|---|---|---|
| 1 | `datos/sql/01_crear_tablas.sql` | Crea las tablas, sus claves primarias y sus relaciones (claves foráneas). |
| 2 | `datos/sql/02_cargar_datos.sql` | Inserta todos los datos del periodo enero de 2024 a octubre de 2026. |

Los scripts deben ejecutarse **en este orden**: si se ejecuta primero el de carga, fallará porque las tablas aún no existen.

Elige **una** de las tres opciones siguientes. La opción A es la más sencilla si nunca has usado PostgreSQL.

---

## Paso 0. Descargar el repositorio

1. Entra en https://github.com/sortaria24-max/ESLEVA-BI
2. Pulsa el botón verde **Code** y después **Download ZIP**.
3. Descomprime el fichero. Los scripts estarán en la carpeta `datos/sql/`.

Si utilizas Git, también puedes clonarlo:

```bash
git clone https://github.com/sortaria24-max/ESLEVA-BI.git
```

---

## Opción A. PostgreSQL instalado en tu ordenador

### A.1. Instalar PostgreSQL

- **Windows:** descarga el instalador de https://www.postgresql.org/download/windows/ y ejecútalo con las opciones por defecto. Durante la instalación te pedirá una contraseña para el usuario `postgres`: anótala. El instalador incluye **pgAdmin**, una aplicación gráfica para gestionar la base de datos.
- **macOS:** la forma más sencilla es instalar **Postgres.app** desde https://postgresapp.com/ y, si quieres una herramienta gráfica, **pgAdmin** desde https://www.pgadmin.org/download/.

### A.2. Crear la base de datos

1. Abre **pgAdmin** y conéctate al servidor local (`localhost`) con el usuario `postgres` y la contraseña que anotaste.
2. En el panel izquierdo, clic derecho sobre **Databases > Create > Database…**
3. Nombre: `esleva`. Pulsa **Save**.

### A.3. Ejecutar los scripts

1. Selecciona la base de datos `esleva` en el panel izquierdo.
2. Abre la herramienta de consultas: menú **Tools > Query Tool**.
3. Pulsa el icono de **abrir fichero** y selecciona `datos/sql/01_crear_tablas.sql`.
4. Ejecuta el script con el botón **▶ Execute** (o la tecla F5). Debe terminar sin errores.
5. Repite los pasos 3 y 4 con `datos/sql/02_cargar_datos.sql`. Este script es más grande y puede tardar algo más.

**Alternativa por terminal (psql):** desde la carpeta del repositorio,

```bash
createdb -U postgres esleva
psql -U postgres -d esleva -f datos/sql/01_crear_tablas.sql
psql -U postgres -d esleva -f datos/sql/02_cargar_datos.sql
```

Datos de conexión resultantes:

| Parámetro | Valor |
|---|---|
| Servidor | `localhost` |
| Puerto | `5432` |
| Base de datos | `esleva` |
| Usuario | `postgres` |
| Contraseña | la que definiste en la instalación |

---

## Opción B. Un nuevo proyecto en Supabase (en la nube)

1. Crea una cuenta gratuita en https://supabase.com/ y pulsa **New project**.
2. Elige un nombre (por ejemplo, `esleva`), una contraseña para la base de datos (anótala) y la región más cercana (por ejemplo, *West EU*). Espera a que el proyecto termine de crearse.
3. En el menú lateral, abre el **SQL Editor**.
4. Pulsa **New query**, pega el contenido de `datos/sql/01_crear_tablas.sql` y pulsa **Run**.
5. Para la carga de datos, el script `02_cargar_datos.sql` puede ser demasiado grande para el editor web. Es más fiable ejecutarlo con `psql` desde tu ordenador (necesitas tener PostgreSQL instalado, opción A.1) usando la cadena de conexión del proyecto:
   - En Supabase, pulsa **Connect** (parte superior) y copia la cadena de la sección **Session pooler**.
   - Ejecuta, sustituyendo la cadena por la tuya:

   ```bash
   psql "postgresql://postgres.<ref>:<contraseña>@aws-0-<region>.pooler.supabase.com:5432/postgres" -f datos/sql/02_cargar_datos.sql
   ```

Usa siempre los datos del **Session pooler**: la conexión directa de Supabase solo funciona con IPv6 y muchas redes domésticas no la admiten.

Datos de conexión resultantes (los encontrarás en **Connect > Session pooler**):

| Parámetro | Valor |
|---|---|
| Servidor | `aws-0-<region>.pooler.supabase.com` |
| Puerto | `5432` |
| Base de datos | `postgres` |
| Usuario | `postgres.<ref>` |
| Contraseña | la que definiste al crear el proyecto |

---

## Opción C. Docker

Si tienes Docker instalado, desde la carpeta del repositorio:

```bash
docker run --name esleva-db -e POSTGRES_PASSWORD=esleva -e POSTGRES_DB=esleva -p 5432:5432 -d postgres:16
docker cp datos/sql/. esleva-db:/sql
docker exec -it esleva-db psql -U postgres -d esleva -f /sql/01_crear_tablas.sql
docker exec -it esleva-db psql -U postgres -d esleva -f /sql/02_cargar_datos.sql
```

Datos de conexión: servidor `localhost`, puerto `5432`, base de datos `esleva`, usuario `postgres`, contraseña `esleva`.

---

## Paso final. Comprobar que la base de datos es correcta

Ejecuta esta consulta (en pgAdmin, en el SQL Editor de Supabase o con `psql`). Muestra el número de filas de cada tabla:

```sql
SELECT relname AS tabla, n_live_tup AS filas
FROM pg_stat_user_tables
ORDER BY relname;
```

Si alguna tabla aparece con 0 filas justo después de la carga, ejecuta antes `ANALYZE;` para actualizar las estadísticas, o cuenta las filas de una tabla concreta con `SELECT COUNT(*) FROM clientes;`.

Compara el resultado con los recuentos de referencia:

| Tabla | Filas esperadas |
|---|---|
| *Pendiente: se completará al generar los datos.* | |

---

## Conectar Power BI a la base de datos recreada

1. En Power BI Desktop: **Inicio > Obtener datos > Más… > Base de datos > Base de datos PostgreSQL**.
2. **Servidor:** el de la tabla de tu opción, con el puerto si no es el 5432 (por ejemplo, `localhost` o `aws-0-<region>.pooler.supabase.com:5432`).
3. **Base de datos:** `esleva` (opciones A y C) o `postgres` (opción B).
4. Modo de conectividad: **Importar**.
5. En la ventana de credenciales, elige **Base de datos** e introduce el usuario y la contraseña.
6. En el navegador, selecciona las tablas y pulsa **Transformar datos** para continuar con el proceso ETL.

Si utilizas la opción A o C y Power BI muestra un error de cifrado SSL, desmarca **Cifrar conexiones** en la ventana de credenciales: una base de datos local no lo necesita. Con Supabase (opción B), mantenla marcada.

---

## Problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| `relation "..." does not exist` al cargar los datos | Se ejecutó `02_cargar_datos.sql` antes que `01_crear_tablas.sql` | Ejecuta primero el script de creación. |
| `relation "..." already exists` | Los scripts ya se habían ejecutado antes | Borra la base de datos, créala de nuevo vacía y repite los pasos. |
| `password authentication failed` | Usuario o contraseña incorrectos | En Supabase, el usuario es `postgres.<ref>`, no solo `postgres`. |
| No conecta con Supabase | Conexión directa (IPv6) o proyecto pausado | Usa los datos del **Session pooler** y, si el proyecto está pausado, reactívalo con **Restore project**. |
