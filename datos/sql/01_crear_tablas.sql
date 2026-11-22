-- ============================================================================
-- ERP de Estampaciones Levante S.A. (ESLEVA) - Creación de tablas
-- Generado automáticamente por generador/generar_datos_ESLEVA.py
-- Puede ejecutarse varias veces: elimina antes las tablas si ya existen.
-- Se ejecuta en una única transacción: si falla, no se borra ni se crea nada.
-- ============================================================================

BEGIN;

DROP TABLE IF EXISTS compras, lineas_pedido, pedidos_venta, ordenes_fabricacion,
    productos, materias_primas, proveedores, maquinas, familias, clientes CASCADE;

CREATE TABLE clientes (
    id_cliente            INTEGER PRIMARY KEY,
    nombre                VARCHAR(120) NOT NULL,
    tipo                  VARCHAR(10)  NOT NULL,
    pais                  VARCHAR(40)  NOT NULL,
    ciudad                VARCHAR(60),
    condiciones_pago_dias INTEGER
);

CREATE TABLE familias (
    id_familia INTEGER PRIMARY KEY,
    nombre     VARCHAR(80) NOT NULL
);

CREATE TABLE maquinas (
    id_maquina       INTEGER PRIMARY KEY,
    codigo           VARCHAR(10) NOT NULL UNIQUE,
    descripcion      VARCHAR(80),
    tipo             VARCHAR(20) NOT NULL,
    tonelaje         INTEGER,
    cadencia_teorica INTEGER NOT NULL
);

CREATE TABLE proveedores (
    id_proveedor       INTEGER PRIMARY KEY,
    nombre             VARCHAR(120) NOT NULL,
    pais               VARCHAR(40),
    plazo_entrega_dias INTEGER
);

CREATE TABLE materias_primas (
    id_materia_prima         INTEGER PRIMARY KEY,
    nombre                   VARCHAR(80) NOT NULL,
    tipo                     VARCHAR(20) NOT NULL,
    id_proveedor_principal   INTEGER REFERENCES proveedores(id_proveedor),
    id_proveedor_alternativo INTEGER REFERENCES proveedores(id_proveedor)
);

CREATE TABLE productos (
    id_producto      INTEGER PRIMARY KEY,
    referencia       VARCHAR(20) NOT NULL UNIQUE,
    descripcion      VARCHAR(120),
    id_familia       INTEGER NOT NULL REFERENCES familias(id_familia),
    id_cliente       INTEGER NOT NULL REFERENCES clientes(id_cliente),
    id_maquina       INTEGER NOT NULL REFERENCES maquinas(id_maquina),
    id_materia_prima INTEGER NOT NULL REFERENCES materias_primas(id_materia_prima),
    material         VARCHAR(20) NOT NULL,
    peso_kg          NUMERIC(8,3),
    coste_estandar   NUMERIC(12,4),
    precio_venta     NUMERIC(12,4),
    fecha_alta       DATE,
    fecha_baja       DATE,
    activo           BOOLEAN NOT NULL
);

CREATE TABLE pedidos_venta (
    id_pedido    INTEGER PRIMARY KEY,
    id_cliente   INTEGER NOT NULL REFERENCES clientes(id_cliente),
    fecha_pedido DATE NOT NULL,
    estado       VARCHAR(15) NOT NULL
);

CREATE TABLE lineas_pedido (
    id_linea           INTEGER PRIMARY KEY,
    id_pedido          INTEGER NOT NULL REFERENCES pedidos_venta(id_pedido),
    id_producto        INTEGER NOT NULL REFERENCES productos(id_producto),
    cantidad           INTEGER NOT NULL,
    precio_unitario    NUMERIC(12,4) NOT NULL,
    fecha_solicitada   DATE NOT NULL,
    fecha_entrega_real DATE
);

CREATE TABLE ordenes_fabricacion (
    id_of                INTEGER PRIMARY KEY,
    id_producto          INTEGER NOT NULL REFERENCES productos(id_producto),
    id_maquina           INTEGER NOT NULL REFERENCES maquinas(id_maquina),
    fecha_inicio         DATE NOT NULL,
    fecha_fin            DATE NOT NULL,
    cantidad_planificada INTEGER NOT NULL,
    cantidad_fabricada   INTEGER NOT NULL,
    estado               VARCHAR(15) NOT NULL
);

CREATE TABLE compras (
    id_compra        INTEGER PRIMARY KEY,
    fecha_pedido     DATE NOT NULL,
    fecha_recepcion  DATE,
    id_proveedor     INTEGER NOT NULL REFERENCES proveedores(id_proveedor),
    id_materia_prima INTEGER NOT NULL REFERENCES materias_primas(id_materia_prima),
    kilos            NUMERIC(12,1) NOT NULL,
    precio_kg        NUMERIC(8,4) NOT NULL,
    importe          NUMERIC(14,2) NOT NULL
);

COMMIT;
